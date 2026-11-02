"""早读萝卜的核心判定与进度逻辑。

这里不依赖 Qt，方便单独跑测试。
输入是每帧的麦克风电平（dBFS），输出是一份可以丢给 QML 的状态快照。
"""

from __future__ import annotations

from dataclasses import dataclass, field

MODE_MORNING = "morning"   # 早读：声音够大才拔，越响越快
MODE_QUIET = "quiet"       # 安静：声音够小才拔，达标后匀速

PHASE_IDLE = "idle"
PHASE_RUNNING = "running"
PHASE_CELEBRATE = "celebrate"

# 电平条显示范围
METER_FLOOR_DB = -70.0
METER_TOP_DB = 0.0


@dataclass
class Params:
    mode: str = MODE_MORNING
    rabbit_count: int = 4
    sensitivity_db: float = 0.0     # 滑块微调，负值更容易，正值更难（±18 dB）
    morning_db: float = 10.0        # 早读：需高出底噪多少 dB（笔记本内置麦 10 dB 就够）
    quiet_db: float = 3.0           # 安静：允许高出底噪多少 dB
    pull_seconds: float = 8.0       # 满速拔完一根萝卜需要的时间
    on_ms: int = 400                # 达标持续多久才开拔
    off_ms: int = 1000              # 掉线持续多久才停
    panic_db: float = 6.0           # 安静模式下，超出阈值这么多直接判定为吵
    rollback_speed: float = 0.3     # 回落速度，0 表示拔出来的不往回掉
    rollback_delay: float = 1.0     # 停下后多久才开始回落
    rollback_seconds: float = 2.0   # 回落最多持续多久，到点就停
    celebrate_seconds: float = 2.0
    env_release_db: float = 12.0    # 声音包络每秒回落多少 dB（让短促的音节也能算数）

    def clamped(self) -> "Params":
        self.rabbit_count = max(1, min(12, int(self.rabbit_count)))
        self.pull_seconds = max(2.0, min(60.0, float(self.pull_seconds)))
        self.sensitivity_db = max(-18.0, min(18.0, float(self.sensitivity_db)))
        self.rollback_speed = max(0.0, min(1.0, float(self.rollback_speed)))
        self.morning_db = max(3.0, min(40.0, float(self.morning_db)))
        self.quiet_db = max(-3.0, min(20.0, float(self.quiet_db)))
        if self.mode not in (MODE_MORNING, MODE_QUIET):
            self.mode = MODE_MORNING
        return self


def _pct(db: float) -> float:
    span = METER_TOP_DB - METER_FLOOR_DB
    return max(0.0, min(1.0, (db - METER_FLOOR_DB) / span))


class Engine:
    """一局游戏的全部状态。每帧调用 tick()。"""

    def __init__(self, params: Params | None = None) -> None:
        self.p = (params or Params()).clamped()
        self.floor: float | None = None      # 自适应底噪 dBFS
        self.level: float = -90.0            # 当前电平 dBFS
        self.env: float = -90.0              # 声音包络（快起慢落），判定用它
        self.phase: str = PHASE_IDLE
        self.pulling: bool = False
        self.progress: float = 0.0           # 当前这根萝卜的拔出进度 0~1
        self.current: int = 0                # 当前轮到第几只兔子（0 基）
        self.done: list[bool] = [False] * self.p.rabbit_count
        self.on_acc: float = 0.0
        self.off_acc: float = 0.0
        self.rollback_acc: float = 0.0
        self.rollback_left: float = 0.0
        self.celebrate_left: float = 0.0
        self.events: list[str] = []
        self.speed_ratio: float = 0.0        # 当前拔速相对满速的倍率

    # ------------------------------------------------------------ 参数
    def apply_params(self, params: Params) -> None:
        old_count = self.p.rabbit_count
        self.p = params.clamped()
        if self.p.rabbit_count != old_count:
            self.done = [False] * self.p.rabbit_count
            self.current = min(self.current, self.p.rabbit_count - 1)
            self.progress = 0.0
            if self.phase == PHASE_CELEBRATE:
                self.phase = PHASE_IDLE

    def threshold_db(self) -> float:
        base = self.floor if self.floor is not None else -60.0
        # 早读：灵敏度往左（负）→ 阈值降低 → 更容易达标
        if self.p.mode == MODE_MORNING:
            return base + self.p.morning_db + self.p.sensitivity_db
        # 安静：判定是「低于阈值才拔」，所以方向要相反，
        # 灵敏度往左（负）→ 阈值抬高 → 更安静才停下 → 同样更容易达标
        return base + self.p.quiet_db - self.p.sensitivity_db

    # ------------------------------------------------------------ 控制
    def start(self) -> None:
        if self.phase == PHASE_IDLE:
            self.phase = PHASE_RUNNING
            self.events.append("started")

    def pause(self) -> None:
        if self.phase in (PHASE_RUNNING, PHASE_CELEBRATE):
            self.phase = PHASE_IDLE
            self.pulling = False
            self.on_acc = self.off_acc = self.rollback_acc = 0.0
            self.rollback_left = 0.0
            self.events.append("paused")

    def toggle(self) -> None:
        if self.phase == PHASE_IDLE:
            self.start()
        else:
            self.pause()

    def reset(self, auto_start: bool = False) -> None:
        self.progress = 0.0
        self.current = 0
        self.done = [False] * self.p.rabbit_count
        self.pulling = False
        self.on_acc = self.off_acc = self.rollback_acc = 0.0
        self.rollback_left = 0.0
        self.speed_ratio = 0.0
        self.phase = PHASE_RUNNING if auto_start else PHASE_IDLE
        self.events.append("reset")

    # ------------------------------------------------------------ 底噪
    def _update_floor(self, db: float) -> None:
        if self.floor is None:
            self.floor = db
            return
        if db < self.floor:
            # 变安静：快速跟下去，保证阈值不会一直悬在高处
            self.floor += (db - self.floor) * 0.35
        elif not self.pulling and db < self.floor + 2.0:
            # 只有「贴着底噪」的轻微变化才让底噪往上爬。
            # 一旦明显比底噪响（也就是人在说话），底噪就冻住，
            # 否则阈值会跟着朗读声一起爬高，越读越拔不动。
            self.floor += (db - self.floor) * 0.004
        self.floor = max(-90.0, min(-15.0, self.floor))

    # ------------------------------------------------------------ 主循环
    def tick(self, dt: float, db: float) -> dict:
        dt = max(0.0, min(0.5, dt))
        self.level = db
        # 讲课时音量是「有起伏的音节」，只按瞬时值判定会一直卡在阈值线上；
        # 这里做一个快起慢落的包络：一响就抬起来，之后按 env_release_db/秒回落。
        self.env = max(db, self.env - self.p.env_release_db * dt)
        self._update_floor(db)

        if self.phase == PHASE_RUNNING:
            self._tick_running(dt)
        elif self.phase == PHASE_CELEBRATE:
            self.celebrate_left -= dt
            self.speed_ratio = 0.0
            if self.celebrate_left <= 0:
                self.reset(auto_start=True)

        return self.snapshot()

    def _tick_running(self, dt: float) -> None:
        th = self.threshold_db()
        if self.p.mode == MODE_MORNING:
            met = self.env >= th
            excess = self.env - th
            # 刚够线就有半速，越响越快，6 dB 翻一倍速，封顶 2.5 倍
            self.speed_ratio = max(0.5, min(2.5, 0.5 + excess / 6.0)) if met else 0.0
        else:
            # 安静模式要的是「现在就安静」，用瞬时值，不用包络
            met = self.level <= th
            # 安静模式：达标后匀速
            self.speed_ratio = 1.0 if met else 0.0
            # 突然的大声直接判定为吵，不等迟滞
            if self.level > th + self.p.panic_db:
                met = False

        if met:
            self.on_acc += dt
            self.off_acc = 0.0
            if not self.pulling and self.on_acc >= self.p.on_ms / 1000.0:
                self.pulling = True
                self.rollback_acc = 0.0
                self.rollback_left = self.p.rollback_seconds
                self.events.append("pull_start")
        else:
            # 音节之间的空档不要一票否决，让累计值慢慢漏掉即可
            self.on_acc = max(0.0, self.on_acc - dt * 0.8)
            self.off_acc += dt
            if self.pulling and self.off_acc >= self.p.off_ms / 1000.0:
                self.pulling = False
                self.rollback_acc = 0.0
                self.rollback_left = self.p.rollback_seconds
                self.events.append("pull_stop")

        if self.pulling:
            self.progress += self.speed_ratio * dt / self.p.pull_seconds
            self.rollback_acc = 0.0
            if self.progress >= 1.0:
                self._finish_one()
            return

        # 停下之后先等一会儿再回退；回退只持续 rollback_seconds 秒，到点就停
        if self.phase == PHASE_RUNNING:
            self.rollback_acc += dt
            if (self.rollback_acc >= self.p.rollback_delay
                    and self.p.rollback_speed > 0.0
                    and self.rollback_left > 0.0
                    and self.progress > 0.0):
                self.progress -= self.p.rollback_speed * dt / self.p.pull_seconds
                self.rollback_left -= dt
                if self.progress < 0.0:
                    self.progress = 0.0
                if self.rollback_left <= 0.0:
                    self.rollback_left = 0.0
                    self.events.append("rollback_end")

    def _finish_one(self) -> None:
        self.done[self.current] = True
        self.events.append(f"done:{self.current}")
        self.progress = 0.0
        self.current += 1
        self.pulling = False
        self.on_acc = self.off_acc = 0.0
        if self.current >= self.p.rabbit_count:
            self.current = self.p.rabbit_count - 1
            self.phase = PHASE_CELEBRATE
            self.celebrate_left = self.p.celebrate_seconds
            self.events.append("round_complete")

    # ------------------------------------------------------------ 输出
    def message(self) -> str:
        if self.phase == PHASE_IDLE:
            return "点「开始」进入游戏"
        if self.phase == PHASE_CELEBRATE:
            return "全部拔完！"
        if self.p.mode == MODE_MORNING:
            if self.pulling:
                return "很好，保持这个音量！"
            return "声音再大一点"
        if self.pulling:
            return "很安静，就是这样"
        return "太吵了，安静下来才会继续"

    def snapshot(self) -> dict:
        th = self.threshold_db()
        done_count = sum(1 for d in self.done if d)
        return {
            "phase": self.phase,
            "pulling": self.pulling,
            "progress": round(self.progress, 4),
            "current": self.current,
            "done": list(self.done),
            "done_count": done_count,
            "count": self.p.rabbit_count,
            "mode": self.p.mode,
            "sensitivity_db": self.p.sensitivity_db,
            "rabbit_count": self.p.rabbit_count,
            "message": self.message(),
            "level_db": round(self.level, 1),
            "env_db": round(self.env, 1),
            "floor_db": round(self.floor if self.floor is not None else -60.0, 1),
            "threshold_db": round(th, 1),
            "level_pct": round(_pct(self.level), 3),
            "floor_pct": round(_pct(self.floor if self.floor is not None else -60.0), 3),
            "threshold_pct": round(_pct(th), 3),
            "speed_ratio": round(self.speed_ratio, 2),
        }

    def drain_events(self) -> list[str]:
        out = self.events
        self.events = []
        return out
