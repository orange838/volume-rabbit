"""麦克风电平采集。

用 QAudioSource 拉流，每 60ms 读一次 PCM，算 RMS 转 dBFS。
不落盘、不录音，只在内存里算一个数字。
"""

from __future__ import annotations

import array
import math

from loguru import logger
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices


class AudioMeter(QObject):
    """持续输出麦克风电平。"""

    levelChanged = Signal(float, float)   # (rms 0~1, dbfs)
    failed = Signal(str)

    INTERVAL_MS = 60

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source: QAudioSource | None = None
        self._io = None
        self._device_name = ""
        self._running = False
        self._last_error = ""

        self._timer = QTimer(self)
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._poll)

        self._retry = QTimer(self)
        self._retry.setSingleShot(True)
        self._retry.setInterval(3000)
        self._retry.timeout.connect(self.start)

    # ---------------------------------------------------------- 生命周期
    @property
    def running(self) -> bool:
        return self._running

    @property
    def device_name(self) -> str:
        return self._device_name

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self) -> bool:
        self.stop(keep_retry=False)
        try:
            device = QMediaDevices.defaultAudioInput()
        except Exception as exc:  # noqa: BLE001
            self._fail(f"取不到麦克风：{exc}")
            return False

        if device.isNull():
            self._fail("没有找到可用的麦克风")
            return False

        self._device_name = device.description()
        fmt = QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
            logger.info(f"[早读萝卜] 设备不支持 16k 单声道，改用 {fmt.sampleRate()}Hz")

        try:
            self._source = QAudioSource(device, fmt, self)
            self._io = self._source.start()
        except Exception as exc:  # noqa: BLE001
            self._fail(f"打开麦克风失败：{exc}")
            return False

        if self._io is None:
            self._fail(f"打开麦克风失败：{self._source.error()}")
            return False

        self._running = True
        self._last_error = ""
        self._timer.start()
        logger.info(f"[早读萝卜] 开始采集：{self._device_name}")
        return True

    def stop(self, keep_retry: bool = False) -> None:
        self._timer.stop()
        self._running = False
        if not keep_retry:
            self._retry.stop()
        try:
            if self._source is not None:
                self._source.stop()
        except Exception:  # noqa: BLE001
            pass
        self._source = None
        self._io = None

    def _fail(self, message: str) -> None:
        self._last_error = message
        logger.warning(f"[早读萝卜] {message}")
        self.failed.emit(message)
        self.stop(keep_retry=True)
        self._retry.start()

    # ---------------------------------------------------------- 采样
    def _poll(self) -> None:
        if self._io is None:
            return
        try:
            chunk = self._io.readAll()
        except Exception as exc:  # noqa: BLE001
            self._fail(f"读取麦克风失败：{exc}")
            return
        if not chunk or chunk.size() == 0:
            return

        data = bytes(chunk)
        samples = len(data) // 2
        if samples <= 0:
            return

        pcm = array.array("h")
        try:
            pcm.frombytes(data[: samples * 2])
        except Exception:  # noqa: BLE001
            return

        total = 0
        for value in pcm:
            total += value * value
        rms = math.sqrt(total / samples) / 32768.0
        dbfs = 20.0 * math.log10(max(rms, 1e-6))
        self.levelChanged.emit(rms, dbfs)
