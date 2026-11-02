import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import RinUI
import ClassWidgets.Plugins

PluginPage {
    id: root
    pluginId: "org.cslblog.volumerabbit"
    title: qsTr("早读萝卜")

    property string mode: "morning"
    property int rabbitCount: 4
    property real sensitivity: 0
    property real pullSeconds: 8
    property real rollbackSpeed: 0.3
    property string micInfo: ""
    property bool previewing: false

    Component.onCompleted: refresh()

    Connections {
        target: backend
        function onConfigChanged() { root.refresh() }
        function onPreviewChanged() {
            root.previewing = backend.isPreviewing()
            root.micInfo = backend.micStatus()
        }
    }

    // 试听到点会自动释放，这里轮询一次状态，保证按钮文案也能自己复位
    Timer {
        interval: 500
        repeat: true
        running: root.previewing
        onTriggered: {
            var live = backend.isPreviewing()
            if (live !== root.previewing) {
                root.previewing = live
                root.micInfo = backend.micStatus()
            }
        }
    }

    function refresh() {
        if (!backend) return
        var s = backend.getSettings()
        mode = s.mode
        rabbitCount = s.rabbit_count
        sensitivity = s.sensitivity_db
        pullSeconds = s.pull_seconds
        rollbackSpeed = s.rollback_speed
        micInfo = backend.micStatus()
        previewing = backend.isPreviewing()
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_play_20_regular"
        title: qsTr("打开大屏")
        description: qsTr("在独立窗口里显示萝卜地，可以全屏投影。建议先在教室里点开，看一眼右下角电平条。麦克风只在需要时占用：窗口关掉、游戏暂停就会松手。")

        RowLayout {
            spacing: 8
            Button {
                text: qsTr("打开大窗口")
                highlighted: true
                onClicked: backend.openWindow()
            }
            Button {
                text: root.previewing ? qsTr("停止试听") : qsTr("测一下麦克风")
                onClicked: {
                    if (root.previewing) {
                        backend.stopMic()
                    } else {
                        backend.startPreview()
                    }
                    root.previewing = backend.isPreviewing()
                    root.micInfo = backend.micStatus()
                }
            }
            Text {
                Layout.leftMargin: 8
                text: root.micInfo
                font.pixelSize: 12
                opacity: 0.7
            }
        }
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_mic_20_regular"
        title: qsTr("当前模式")
        description: mode === "quiet"
            ? qsTr("安静模式：声音小于阈值才拔，达标后匀速；一吵就停。")
            : qsTr("早读模式：声音大于阈值才拔，越响拔得越快。")

        RowLayout {
            spacing: 8
            Button {
                text: qsTr("早读模式")
                highlighted: root.mode !== "quiet"
                onClicked: backend.setMode("morning")
            }
            Button {
                text: qsTr("安静模式")
                highlighted: root.mode === "quiet"
                onClicked: backend.setMode("quiet")
            }
        }
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_people_20_regular"
        title: qsTr("兔子数量：%1 只").arg(root.rabbitCount)
        description: qsTr("兔子排队轮流拔，每只拔一根；全部轮完停 2 秒后整排重置。")

        Slider {
            Layout.fillWidth: true
            from: 1
            to: 12
            stepSize: 1
            value: root.rabbitCount
            onMoved: backend.setRabbitCount(Math.round(value))
        }
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_settings_20_regular"
        title: qsTr("灵敏度微调：%1 dB").arg(root.sensitivity > 0 ? "+" + root.sensitivity.toFixed(0) : root.sensitivity.toFixed(0))
        description: qsTr("负数更容易达标，正数更严格。底噪是自动跟的，这里只是微调；还是拔不动就继续往左拉到 -18。")

        Slider {
            Layout.fillWidth: true
            from: -18
            to: 18
            stepSize: 1
            value: root.sensitivity
            onMoved: backend.setSensitivity(value)
        }
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_arrow_undo_20_regular"
        title: qsTr("回落速度：%1%").arg(Math.round(root.rollbackSpeed * 100))
        description: qsTr("声音断了以后，已经拔出来的进度往回掉的快慢；0% 就是不回掉，松口气也不会吃亏。")

        Slider {
            Layout.fillWidth: true
            from: 0
            to: 1
            stepSize: 0.05
            value: root.rollbackSpeed
            onMoved: backend.setRollbackSpeed(value)
        }
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_timer_20_regular"
        title: qsTr("一根萝卜耗时：%1 秒").arg(root.pullSeconds.toFixed(0))
        description: qsTr("满速拔完一根所需时间。早读模式下音量越大越快，这个是基准值。")

        Slider {
            Layout.fillWidth: true
            from: 3
            to: 30
            stepSize: 1
            value: root.pullSeconds
            onMoved: backend.setPullSeconds(value)
        }
    }
}
