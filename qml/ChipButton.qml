import QtQuick

Rectangle {
    id: root

    property string label: ""
    property bool active: false
    property bool primary: false
    property color accent: "#F5A623"
    signal clicked()

    implicitWidth: textItem.implicitWidth + 34
    implicitHeight: 42
    radius: 14

    color: {
        if (root.primary) return mouse.containsMouse ? "#FFB43F" : root.accent
        if (mouse.containsMouse) return "#FFFFFF"
        return root.active ? "#FFE9C7" : "#FFF8EC"
    }
    border.width: 1.5
    border.color: root.primary ? "#00000000" : "#E9D7BF"

    Behavior on color { ColorAnimation { duration: 120 } }

    Text {
        id: textItem
        anchors.centerIn: parent
        text: root.label
        font.pixelSize: 15
        font.bold: root.primary
        color: root.primary ? "#FFFFFF" : "#6B5540"
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
