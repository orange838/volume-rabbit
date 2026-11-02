"""早读萝卜 —— 用麦克风音量驱动兔子拔萝卜。

- 早读模式：声音越大拔得越快（要够大声才开拔）
- 安静模式：越安静才拔，达标后匀速；一吵就停
- 兔子排队轮流，每只拔完一根，全部轮完停 2 秒后整排重置
"""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQuick import QQuickView

from ClassWidgets.SDK import CW2Plugin, ConfigBaseModel, PluginAPI

from _vr.audio import AudioMeter
from _vr.engine import MODE_MORNING, MODE_QUIET, Engine, Params

PLUGIN_ID = "org.cslblog.volumerabbit"


class VolRabbitConfig(ConfigBaseModel):
    mode: str = MODE_MORNING
    rabbit_count: int = 4
    sensitivity_db: float = 0.0
    pull_seconds: float = 8.0
    morning_db: float = 18.0
    quiet_db: float = 3.0
    window_width: int = 1280
    window_height: int = 720


class GameBridge(QObject):
    """暴露给大窗口 QML 的接口。"""

    stateChanged = Signal()

    def __init__(self, plugin: "Plugin") -> None:
        super().__init__()
        self._plugin = plugin

    def _snapshot(self) -> dict:
        return self._plugin.snapshot()

    state = Property("QVariantMap", _snapshot, notify=stateChanged)

    @Slot()
    def toggle(self) -> None:
        self._plugin.toggle_game()

    @Slot()
    def start(self) -> None:
        self._plugin.start_game()

    @Slot()
    def pause(self) -> None:
        self._plugin.pause_game()

    @Slot()
    def reset(self) -> None:
        self._plugin.reset_game()

    @Slot(str)
    def setMode(self, mode: str) -> None:
        self._plugin.set_mode(mode)

    @Slot(int)
    def setRabbitCount(self, count: int) -> None:
        self._plugin.set_rabbit_count(count)

    @Slot(float)
    def setSensitivity(self, value: float) -> None:
        self._plugin.set_sensitivity(value)

    @Slot(float)
    def setPullSeconds(self, value: float) -> None:
        self._plugin.set_pull_seconds(value)

    @Slot()
    def toggleFullscreen(self) -> None:
        self._plugin.toggle_fullscreen()

    @Slot()
    def closeWindow(self) -> None:
        self._plugin.close_window()

    @Slot(result=str)
    def deviceName(self) -> str:
        return self._plugin.meter.device_name or "未连接"


class Plugin(CW2Plugin):
    configChanged = Signal()

    def __init__(self, api: PluginAPI) -> None:
        super().__init__(api)
        self._config = VolRabbitConfig()
        self._engine = Engine(Params())
        self.meter = AudioMeter(self)
        self._bridge = GameBridge(self)
        self._view: QQuickView | None = None
        self._restore_quit_on_close = False
        self._last_tick = time.monotonic()
        self._last_state_emit = 0.0

        self.meter.levelChanged.connect(self._on_level)
        self.meter.failed.connect(self._on_mic_failed)

    # ------------------------------------------------------------ 生命周期
    def on_load(self) -> None:
        super().on_load()
        self.api.config.register_plugin_model(self.pid, self._config)
        model = self.api.config.get_plugin_model(self.pid)
        if model is not None:
            self._config = model
        self._apply_params()

        self.api.ui.register_settings_page(
            qml_path="qml/Settings.qml",
            title="早读萝卜",
            icon="ic_fluent_mic_20_regular",
        )
        # 快捷面板里的「早读萝卜」入口，一键打开大窗口
        try:
            self.api.ui.register_shortcut(
                shortcut_id="open",
                name="早读萝卜",
                icon="icon.png",
                action=self.open_window,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[早读萝卜] 注册快捷方式失败：{exc}")
        logger.info("[早读萝卜] 插件已加载")

    def on_unload(self) -> None:
        self.meter.stop()
        try:
            self.api.ui.unregister_plugin_shortcuts(self.pid)
        except Exception:  # noqa: BLE001
            pass
        self._restore_app_quit_flag()
        view = self._view
        if view is not None:
            try:
                view.hide()
                view.close()
            except Exception:  # noqa: BLE001
                pass
        self._view = None
        if view is not None:
            view.deleteLater()
        logger.info("[早读萝卜] 插件已卸载")

    # ------------------------------------------------------------ 参数
    def _apply_params(self) -> None:
        self._engine.apply_params(Params(
            mode=self._config.mode,
            rabbit_count=self._config.rabbit_count,
            sensitivity_db=self._config.sensitivity_db,
            morning_db=self._config.morning_db,
            quiet_db=self._config.quiet_db,
            pull_seconds=self._config.pull_seconds,
        ))

    def _save(self) -> None:
        try:
            self.api.config.save()
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[早读萝卜] 保存配置失败：{exc}")
        self.configChanged.emit()
        # 设置页改的值要立刻反映到大屏（反之亦然）
        self._bridge.stateChanged.emit()

    def snapshot(self) -> dict:
        data = self._engine.snapshot()
        data["device"] = self.meter.device_name or "未连接"
        data["mic_running"] = self.meter.running
        return data

    # ------------------------------------------------------------ 音频
    def _on_level(self, rms: float, dbfs: float) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now
        self._engine.tick(dt, dbfs)
        # 16Hz 左右刷新界面就够了
        if now - self._last_state_emit >= 0.05:
            self._last_state_emit = now
            self._bridge.stateChanged.emit()

    def _on_mic_failed(self, message: str) -> None:
        logger.warning(f"[早读萝卜] 麦克风不可用：{message}")
        self._bridge.stateChanged.emit()

    # ------------------------------------------------------------ 控制
    def toggle_game(self) -> None:
        if self._engine.phase == "idle":
            self.start_game()
        else:
            self.pause_game()

    def start_game(self) -> None:
        if not self.meter.running:
            self.meter.start()
        self._last_tick = time.monotonic()
        self._engine.start()
        self._bridge.stateChanged.emit()

    def pause_game(self) -> None:
        self._engine.pause()
        self._bridge.stateChanged.emit()

    def reset_game(self) -> None:
        self._engine.reset()
        self._bridge.stateChanged.emit()

    def set_mode(self, mode: str) -> None:
        self._config.mode = mode if mode in (MODE_MORNING, MODE_QUIET) else MODE_MORNING
        self._apply_params()
        self._save()

    def set_rabbit_count(self, count: int) -> None:
        self._config.rabbit_count = max(1, min(12, int(count)))
        self._apply_params()
        self._save()

    @Slot(float)
    def set_sensitivity(self, value: float) -> None:
        self._config.sensitivity_db = max(-9.0, min(9.0, float(value)))
        self._apply_params()
        self._save()

    @Slot(float)
    def set_pull_seconds(self, value: float) -> None:
        self._config.pull_seconds = max(2.0, min(60.0, float(value)))
        self._apply_params()
        self._save()

    # ------------------------------------------------------------ 窗口
    def open_window(self) -> None:
        self._guard_app_quit()
        if self._view is not None:
            self._view.show()
            self._view.raise_()
            self._view.requestActivate()
            if not self.meter.running:
                self.meter.start()
            return

        qml_path = Path(__file__).resolve().parent / "qml" / "GameWindow.qml"
        view = QQuickView()
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setColor(QColor("#FFF6E5"))
        view.setTitle("早读萝卜")
        view.rootContext().setContextProperty("backend", self._bridge)
        view.setSource(QUrl.fromLocalFile(str(qml_path)))
        if view.status() == QQuickView.Status.Error:
            for err in view.errors():
                logger.error(f"[早读萝卜] QML 错误：{err.toString()}")
        view.closing.connect(self._on_window_closing)
        view.resize(max(640, self._config.window_width), max(360, self._config.window_height))
        view.show()
        view.requestActivate()

        self._view = view
        self._last_tick = time.monotonic()
        if not self.meter.running:
            self.meter.start()
        logger.info("[早读萝卜] 大窗口已打开")

    @Slot()
    def _on_window_closing(self) -> None:
        # 注意：这里绝不能销毁 view。窗口的 closing 信号是在它自己的关闭流程里发出的，
        # 此时把 Python 引用置 None 会立即析构 QQuickView，导致进程直接崩溃。
        self.meter.stop()
        self._engine.pause()
        logger.info("[早读萝卜] 大窗口被关闭（标题栏）")

    def _guard_app_quit(self) -> None:
        """大窗口关闭时不要把整个 CW2 带走。

        Qt 默认「最后一个可见窗口关闭就退出应用」。CW2 主窗口收进托盘后，
        我们的窗口就是唯一可见窗口，此时关闭它会让 CW2 直接退出。
        """
        app = QGuiApplication.instance()
        if app is not None and app.quitOnLastWindowClosed():
            app.setQuitOnLastWindowClosed(False)
            self._restore_quit_on_close = True
            logger.info("[早读萝卜] 暂时禁用「关闭最后窗口即退出」，避免连带关闭 CW2")

    def _restore_app_quit_flag(self) -> None:
        if not self._restore_quit_on_close:
            return
        self._restore_quit_on_close = False
        app = QGuiApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(True)

    def close_window(self) -> None:
        # 用 hide() 而不是 close()：close 会触发「关闭最后一个可见窗口就退出应用」，
        # 在 CW2 主窗口收进托盘时会把整个 CW2 带走。
        if self._view is not None:
            self._view.hide()
        self.meter.stop()
        self._engine.pause()
        logger.info("[早读萝卜] 大窗口已隐藏（保留实例，可随时重开）")

    def toggle_fullscreen(self) -> None:
        if self._view is None:
            return
        if self._view.visibility() == QQuickView.Visibility.FullScreen:
            self._view.showNormal()
        else:
            self._view.showFullScreen()

    # ------------------------------------------------------------ 设置页接口
    @Slot(str)
    def setMode(self, mode: str) -> None:
        self.set_mode(mode)

    @Slot(int)
    def setRabbitCount(self, count: int) -> None:
        self.set_rabbit_count(count)

    @Slot(float)
    def setSensitivity(self, value: float) -> None:
        self.set_sensitivity(value)

    @Slot(float)
    def setPullSeconds(self, value: float) -> None:
        self.set_pull_seconds(value)

    @Slot(result="QVariantMap")
    def getSettings(self) -> dict:
        return {
            "mode": self._config.mode,
            "rabbit_count": self._config.rabbit_count,
            "sensitivity_db": self._config.sensitivity_db,
            "pull_seconds": self._config.pull_seconds,
            "morning_db": self._config.morning_db,
            "quiet_db": self._config.quiet_db,
        }

    @Slot(str, result="QVariantMap")
    def presetInfo(self, mode: str) -> dict:
        if mode == MODE_QUIET:
            return {
                "title": "安静模式",
                "hint": "声音小于阈值才拔，达标后匀速；一旦大声说话立刻停。适合自习、午休。",
            }
        return {
            "title": "早读模式",
            "hint": "声音大于阈值才拔，越响拔得越快。适合早读、朗读课。",
        }

    @Slot(result=str)
    def micStatus(self) -> str:
        if self.meter.running:
            return f"麦克风：{self.meter.device_name}"
        if self.meter.last_error:
            return f"麦克风不可用：{self.meter.last_error}"
        return "麦克风未启动"

    @Slot()
    def openWindow(self) -> None:
        self.open_window()

    @Slot()
    def startPreview(self) -> None:
        """设置页里点「试听电平」，启动麦克风但不进游戏。"""
        if not self.meter.running:
            self.meter.start()

    @Slot()
    def stopMic(self) -> None:
        self.meter.stop()
