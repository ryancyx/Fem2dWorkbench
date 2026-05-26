import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    property alias text: input.text
    property string label: ""
    property string suffix: ""
    property string placeholderText: ""

    spacing: 5

    Label {
        text: root.label
        color: "#1F2937"
        font.pixelSize: 13
        font.bold: true
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 6

        TextField {
            id: input
            Layout.fillWidth: true
            selectByMouse: true
            placeholderText: root.placeholderText
            color: "#1F2937"
            font.pixelSize: 13
            background: Rectangle {
                radius: 6
                color: "#FFFFFF"
                border.color: input.activeFocus ? "#93C5FD" : "#D3DCE8"
            }
        }

        Label {
            visible: root.suffix !== ""
            text: root.suffix
            color: "#64748B"
            font.pixelSize: 12
        }
    }
}
