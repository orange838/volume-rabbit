import QtQuick

Item {
    id: root
    width: 150
    height: 180

    property color fur: "#FFFBF4"
    property color shade: "#E7D6C6"
    property real lean: 0          // 前倾角度
    property real squash: 0        // 0~1，往上顶的压缩感
    property bool active: false    // 当前这一只

    Item {
        id: g
        anchors.fill: parent
        transformOrigin: Item.Bottom
        rotation: root.lean
        scale: 1 - root.squash * 0.04

        // 地面投影
        Rectangle {
            x: 40
            y: 164
            width: 78
            height: 12
            radius: 6
            color: "#33000000"
        }

        // 尾巴
        Rectangle {
            x: 10; y: 106; width: 26; height: 24; radius: 12
            color: root.fur
            border.color: root.shade
            border.width: 2
        }

        // 身体
        Rectangle {
            x: 26; y: 76; width: 94; height: 80; radius: 40
            color: root.fur
            border.color: root.shade
            border.width: 2
        }

        // 前脚
        Rectangle {
            x: 40; y: 146; width: 36; height: 18; radius: 9
            color: root.fur
            border.color: root.shade
            border.width: 2
        }
        Rectangle {
            x: 82; y: 146; width: 36; height: 18; radius: 9
            color: root.fur
            border.color: root.shade
            border.width: 2
        }

        // 耳朵
        Rectangle {
            x: 76; y: 0; width: 20; height: 66; radius: 10
            color: root.fur
            border.color: root.shade
            border.width: 2
            rotation: -10
            transformOrigin: Item.Bottom
            Rectangle {
                anchors.fill: parent
                anchors.margins: 5
                radius: width / 2
                color: "#F9D6D6"
            }
        }
        Rectangle {
            x: 100; y: 6; width: 20; height: 62; radius: 10
            color: root.fur
            border.color: root.shade
            border.width: 2
            rotation: 14
            transformOrigin: Item.Bottom
            Rectangle {
                anchors.fill: parent
                anchors.margins: 5
                radius: width / 2
                color: "#F9D6D6"
            }
        }

        // 头
        Rectangle {
            x: 62; y: 42; width: 68; height: 64; radius: 32
            color: root.fur
            border.color: root.shade
            border.width: 2
        }

        // 腮红
        Rectangle {
            x: 96; y: 78; width: 18; height: 12; radius: 6
            color: "#FBD3D0"
            opacity: 0.9
        }

        // 眼睛
        Rectangle {
            x: 108; y: 62; width: 8; height: 9; radius: 4
            color: "#3B2A22"
        }
        Rectangle {
            x: 110; y: 64; width: 3; height: 3; radius: 1.5
            color: "#FFFFFF"
        }

        // 鼻子
        Rectangle {
            x: 124; y: 76; width: 11; height: 8; radius: 4
            color: "#E88C8C"
        }

        // 手臂，伸向萝卜
        Rectangle {
            x: 108; y: 104; width: 48; height: 14; radius: 7
            color: root.fur
            border.color: root.shade
            border.width: 2
            rotation: root.active ? -12 : -22
            transformOrigin: Item.Left
        }
    }
}
