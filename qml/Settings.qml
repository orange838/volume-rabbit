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
    property string micInfo: ""

    Component.onCompleted: refresh()

    Connections {
        target: backend
        function onConfigChanged() { root.refresh() }
    }

    function refresh() {
        if (!backend) return
        var s = backend.getSettings()
        mode = s.mode
        rabbitCount = s.rabbit_count
        sensitivity = s.sensitivity_db
        pullSeconds = s.pull_seconds
        micInfo = backend.micStatus()
    }

    SettingCard {
        Layout.fillWidth: true
        icon.name: "ic_fluent_play_20_regular"
        title: qsTr("打开大屏")
        description: qsTr("在独立窗口里显示萝卜地，可以全屏投影。建议先在教室里点开，看一眼右下角电平条。")

        RowLayout {
            spacing: 8
            Button {
                text: qsTr("打开大窗口")
                highlighted: true
                onClicked: backend.openWindow()
            }
            Button {
                text: qsTr("测一下麦克风")
                onClicked: {
                    backend.startPreview()
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
        description: qsTr("负数更容易达标，正数更严格。底噪是自动跟的，这里只是微调。")

        Slider {
            Layout.fillWidth: true
            from: -9
            to: 9
            stepSize: 1
            value: root.sensitivity
            onMoved: backend.setSensitivity(value)
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
