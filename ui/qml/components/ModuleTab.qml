import QtQuick
import QtQuick.Controls

Button {
    id: root

    property bool selected: false

    implicitWidth: 66
    implicitHeight: 30
    padding: 0

    background: Rectangle {
        radius: 8
        color: root.selected ? "#EAF2FF" : (root.hovered ? "#F1F5F9" : "transparent")
        border.color: root.selected ? "#BFDBFE" : "transparent"

        Rectangle {
            visible: root.selected
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width: 3
            height: 18
            radius: 2
            color: "#2563EB"
        }
    }

    contentItem: Label {
        text: root.text
        color: root.selected ? "#1D4ED8" : "#1F2937"
        font.pixelSize: 13
        font.bold: root.selected
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
}
