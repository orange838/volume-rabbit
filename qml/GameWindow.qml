import QtQuick
import QtQuick.Window

Item {
    id: scene
    width: 1280
    height: 720
    focus: true

    property var st: (typeof backend !== "undefined" && backend) ? backend.state : ({})
    property int rabbitCount: Math.max(1, Math.min(12, st.count || 4))
    property int currentIndex: st.current || 0
    property real progress: st.progress || 0
    property var doneArr: st.done || []
    property bool pulling: !!st.pulling
    property string mode: st.mode || "morning"
    property string phase: st.phase || "idle"

    // 设置页改了灵敏度 → 大屏圆点跟上（拖动中不抢）
    onStChanged: {
        if (!st) return
        var s = Math.round(st.sensitivity_db || 0)
        if (!sensDrag.pressed && s !== Math.round(sensBar.value)) {
            sensBar.value = s
        }
    }

    readonly property real groundTop: height * 0.72
    readonly property real slotWidth: Math.min(320, (width - 60) / rabbitCount)
    readonly property real unitScale: Math.min(1, slotWidth / 280)

    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space) {
            backend.toggle()
            event.accepted = true
        } else if (event.key === Qt.Key_F) {
            backend.toggleFullscreen()
            event.accepted = true
        } else if (event.key === Qt.Key_Escape) {
            // 全屏时 Esc 先退回窗口，再按才关
            if (Window.window && Window.window.visibility === Window.FullScreen) {
                backend.toggleFullscreen()
            } else {
                backend.closeWindow()
            }
            event.accepted = true
        }
    }

    // ---------------------------------------------------------------- 背景
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#FFE3B8" }
            GradientStop { position: 0.45; color: "#FFF4E2" }
            GradientStop { position: 1.0; color: "#EAF3DE" }
        }
    }

    // 太阳
    Rectangle {
        x: scene.width - 200
        y: 56
        width: 126
        height: 126
        radius: 63
        color: "#FFC95C"
        opacity: 0.7
        Rectangle {
            anchors.fill: parent
            anchors.margins: -28
            radius: width / 2
            color: "#2EFFC95C"
        }
    }

    // 远山
    Rectangle {
        x: -60
        y: scene.groundTop - 130
        width: scene.width * 0.5
        height: 200
        radius: width / 2
        color: "#CFE0B8"
        opacity: 0.5
    }
    Rectangle {
        x: scene.width * 0.42
        y: scene.groundTop - 100
        width: scene.width * 0.62
        height: 180
        radius: width / 2
        color: "#DCE9C8"
        opacity: 0.55
    }

    // ---------------------------------------------------------------- 地面
    Rectangle {
        id: ground
        y: scene.groundTop
        width: parent.width
        height: parent.height - scene.groundTop
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#CBA379" }
            GradientStop { position: 0.3; color: "#A8794F" }
            GradientStop { position: 1.0; color: "#7B5437" }
        }
    }

    Repeater {
        model: 30
        Rectangle {
            x: (index * 131) % Math.max(1, scene.width)
            y: scene.groundTop + 22 + ((index * 47) % Math.max(20, scene.height - scene.groundTop - 46))
            width: 24 + (index % 4) * 12
            height: 6
            radius: 3
            color: "#2EFFFFFF"
        }
    }

    // ---------------------------------------------------------------- 萝卜地
    Item {
        id: field
        width: scene.slotWidth * scene.rabbitCount
        height: 300
        x: (scene.width - width) / 2
        y: scene.groundTop - 250

        Repeater {
            model: scene.rabbitCount

            Item {
                id: slot
                width: field.width / scene.rabbitCount
                height: field.height
                x: index * width

                readonly property bool isDone: !!scene.doneArr[index]
                readonly property bool isCurrent: index === scene.currentIndex && !isDone
                readonly property real lift: isDone ? 1.0 : (isCurrent ? scene.progress : 0.0)
                property real bob: 0
                property real wiggle: 0

                // 当前这一只的高亮光圈
                Rectangle {
                    visible: slot.isCurrent
                    x: (slot.width - width) / 2
                    y: 216
                    width: 240
                    height: 46
                    radius: 23
                    color: "#33FFC95C"
                }

                Item {
                    id: unit
                    width: 280
                    height: 300
                    x: (slot.width - 280) / 2
                    scale: scene.unitScale
                    transformOrigin: Item.Bottom

                    // 萝卜
                    Carrot {
                        id: carrot
                        x: 170
                        y: 130 - slot.lift * 100
                        rotation: (slot.isCurrent && scene.pulling) ? slot.wiggle : 0
                        z: 2
                    }

                    // 土坑
                    Rectangle {
                        x: 128
                        y: 196
                        width: 154
                        height: 96
                        radius: 44
                        color: "#9C6F47"
                        z: 3
                        Rectangle {
                            x: 22
                            y: 10
                            width: parent.width - 44
                            height: 14
                            radius: 7
                            color: "#B98A5D"
                        }
                    }

                    // 兔子
                    Rabbit {
                        id: bunny
                        x: 26
                        y: 76
                        z: 4
                        active: slot.isCurrent
                        lean: (slot.isCurrent && scene.pulling) ? slot.bob : 0
                        squash: (slot.isCurrent && scene.pulling) ? 0.6 : 0
                        opacity: slot.isDone ? 0.78 : 1.0
                        Behavior on opacity { NumberAnimation { duration: 300 } }
                    }

                    // 拔完的星星
                    Item {
                        visible: slot.isDone
                        x: carrot.x + 34
                        y: carrot.y - 30
                        width: 44
                        height: 44
                        z: 5

                        Repeater {
                            model: 3
                            Rectangle {
                                width: 9
                                height: 9
                                radius: 2
                                color: "#FFD35C"
                                rotation: 45
                                x: 2 + index * 13
                                y: 4 + (index % 2) * 14
                                SequentialAnimation on opacity {
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.2; duration: 700 + index * 180 }
                                    NumberAnimation { to: 1.0; duration: 700 + index * 180 }
                                }
                            }
                        }
                    }

                    // 序号
                    Rectangle {
                        x: 36
                        y: 272
                        width: 28
                        height: 24
                        radius: 12
                        color: slot.isCurrent ? "#F5A623" : "#FFFFFFAA"
                        z: 5
                        Text {
                            anchors.centerIn: parent
                            text: (index + 1)
                            font.pixelSize: 13
                            font.bold: true
                            color: slot.isCurrent ? "#FFFFFF" : "#8A7057"
                        }
                    }
                }

                SequentialAnimation on bob {
                    running: slot.isCurrent && scene.pulling
                    loops: Animation.Infinite
                    NumberAnimation { to: -9; duration: 420; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 3; duration: 420; easing.type: Easing.InOutSine }
                }

                SequentialAnimation on wiggle {
                    running: slot.isCurrent && scene.pulling
                    loops: Animation.Infinite
                    NumberAnimation { to: 2.6; duration: 170 }
                    NumberAnimation { to: -2.6; duration: 170 }
                }
            }
        }
    }

    // ---------------------------------------------------------------- 顶部栏
    Rectangle {
        id: topBar
        x: 20
        y: 18
        width: parent.width - 40
        height: 60
        radius: 20
        color: "#F2FFFFFF"
        border.width: 1
        border.color: "#22A0846A"

        Row {
            anchors.left: parent.left
            anchors.leftMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            spacing: 14

            Text {
                text: "早读萝卜"
                font.pixelSize: 22
                font.bold: true
                color: "#5E4834"
                anchors.verticalCenter: parent.verticalCenter
            }

            Rectangle {
                width: modeLabel.implicitWidth + 26
                height: 32
                radius: 16
                anchors.verticalCenter: parent.verticalCenter
                color: scene.mode === "quiet" ? "#DFF1FF" : "#FFE6C2"
                border.width: 1
                border.color: scene.mode === "quiet" ? "#A9D2F0" : "#F0C383"
                Text {
                    id: modeLabel
                    anchors.centerIn: parent
                    text: scene.mode === "quiet" ? "安静模式" : "早读模式"
                    font.pixelSize: 14
                    color: scene.mode === "quiet" ? "#2C6E9B" : "#9A6A1E"
                }
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "已拔完 " + (st.done_count || 0) + " / " + scene.rabbitCount
                font.pixelSize: 15
                color: "#8A7057"
            }
        }

        Row {
            anchors.right: parent.right
            anchors.rightMargin: 18
            anchors.verticalCenter: parent.verticalCenter
            spacing: 10

            ChipButton {
                primary: true
                label: scene.phase === "idle" ? "开始" : "暂停"
                onClicked: backend.toggle()
            }
            ChipButton {
                label: scene.mode === "quiet" ? "切到早读" : "切到安静"
                onClicked: backend.setMode(scene.mode === "quiet" ? "morning" : "quiet")
            }
            ChipButton {
                label: "重来"
                onClicked: backend.reset()
            }
            ChipButton {
                label: "全屏"
                onClicked: backend.toggleFullscreen()
            }
            ChipButton {
                label: "关闭"
                onClicked: backend.closeWindow()
            }
        }
    }

    // ---------------------------------------------------------------- 提示语
    Text {
        id: hint
        anchors.horizontalCenter: parent.horizontalCenter
        y: topBar.y + topBar.height + 18
        text: st.message || ""
        font.pixelSize: 30
        font.bold: true
        color: scene.pulling ? "#D98324" : "#8A7057"

        SequentialAnimation on opacity {
            running: scene.pulling
            loops: Animation.Infinite
            NumberAnimation { to: 0.55; duration: 900 }
            NumberAnimation { to: 1.0; duration: 900 }
        }
    }

    // ---------------------------------------------------------------- 电平表
    Rectangle {
        id: meter
        x: 20
        y: parent.height - height - 20
        width: 580
        height: 126
        radius: 18
        color: "#EFFFFFFF"
        border.width: 1
        border.color: "#22A0846A"

        Text {
            x: 18
            y: 12
            text: "麦克风 " + (st.device || "")
            font.pixelSize: 12
            color: "#8A7057"
            elide: Text.ElideRight
            width: parent.width - 36
        }

        Item {
            id: track
            x: 18
            y: 38
            width: parent.width - 36
            height: 18

            Rectangle {
                anchors.fill: parent
                radius: 9
                color: "#EFE6DA"
            }

            Rectangle {
                width: track.width * (st.level_pct || 0)
                height: parent.height
                radius: 9
                gradient: Gradient {
                    GradientStop { position: 0.0; color: "#8CC63F" }
                    GradientStop { position: 0.6; color: "#F5C33B" }
                    GradientStop { position: 1.0; color: "#E8623C" }
                }
                Behavior on width { NumberAnimation { duration: 60 } }
            }

            Rectangle {
                x: Math.max(0, Math.min(track.width - 4, track.width * (st.threshold_pct || 0) - 2))
                width: 4
                height: parent.height + 10
                y: -5
                radius: 2
                color: "#5E4834"
            }
        }

        Text {
            x: 18
            y: 62
            text: "电平 " + (st.level_db || 0).toFixed(0) + " dB   底噪 "
                  + (st.floor_db || 0).toFixed(0) + " dB   阈值 "
                  + (st.threshold_db || 0).toFixed(0) + " dB"
            font.pixelSize: 11
            color: "#9A8168"
        }

        // 灵敏度微调（直接在大屏上调，不用回设置页）
        Item {
            id: sensRow
            x: 18
            y: 88
            width: parent.width - 36
            height: 26

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: "灵敏度"
                font.pixelSize: 12
                color: "#8A7057"
            }

            Item {
                id: sensBar
                x: 58
                width: 240
                height: 22
                anchors.verticalCenter: parent.verticalCenter

                readonly property real from: -18
                readonly property real to: 18
                property real value: st.sensitivity_db || 0

                function apply(x) {
                    var t = Math.max(0, Math.min(1, x / width))
                    var v = Math.round(from + t * (to - from))
                    // 本地立即跟手，再让后端保存并回传，两头始终是同一个值
                    if (v !== Math.round(value)) {
                        value = v
                        backend.setSensitivity(v)
                    }
                }

                Rectangle {
                    anchors.fill: parent
                    radius: 9
                    color: "#EFE6DA"
                }

                Rectangle {
                    x: sensBar.width / 2 - 1
                    width: 2
                    height: parent.height
                    color: "#D8C8B1"
                }

                Rectangle {
                    objectName: "sensKnob"
                    width: 18
                    height: 18
                    radius: 9
                    x: (sensBar.value - sensBar.from) / (sensBar.to - sensBar.from) * (sensBar.width - width)
                    anchors.verticalCenter: parent.verticalCenter
                    color: "#F5A623"
                    border.width: 2
                    border.color: "#FFFFFF"
                }

                MouseArea {
                    id: sensDrag
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onPressed: function(m) { sensBar.apply(m.x) }
                    onPositionChanged: function(m) { if (pressed) sensBar.apply(m.x) }
                }
            }

            Text {
                x: 310
                anchors.verticalCenter: parent.verticalCenter
                text: {
                    var v = Math.round(sensBar.value)
                    return (v > 0 ? "+" : "") + v + " dB"
                }
                font.pixelSize: 12
                font.bold: true
                color: "#6B5540"
            }

            Text {
                x: 372
                anchors.verticalCenter: parent.verticalCenter
                text: "往左更容易达标，往右更严格"
                font.pixelSize: 11
                color: "#A9906F"
            }
        }
    }

    // ---------------------------------------------------------------- 麦克风异常
    Rectangle {
        visible: st.mic_running === false
        anchors.centerIn: parent
        width: 440
        height: 74
        radius: 18
        color: "#F2E8623C"
        Text {
            anchors.centerIn: parent
            text: "麦克风未启动，请检查设备后重新打开本窗口"
            color: "#FFFFFF"
            font.pixelSize: 16
        }
    }
}
