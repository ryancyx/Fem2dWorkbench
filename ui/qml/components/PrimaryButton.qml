import QtQuick
import QtQuick.Controls

Button {
    id: root

    property bool primary: true
    property int buttonWidth: 96

    implicitWidth: buttonWidth
    implicitHeight: 30
    padding: 0

    background: Rectangle {
        radius: 8
        color: root.primary
               ? (root.hovered ? "#1D4ED8" : "#2563EB")
               : (root.hovered ? "#F1F5F9" : "#FFFFFF")
        border.color: root.primary
                      ? "#93C5FD"
                      : (root.hovered ? "#CBD5E1" : "#D3DCE8")
    }

    contentItem: Label {
        text: root.text
        color: root.primary ? "#FFFFFF" : "#1F2937"
        font.pixelSize: 12
        font.bold: root.primary
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}
