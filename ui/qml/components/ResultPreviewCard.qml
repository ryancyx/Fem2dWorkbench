import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string text: ""

    Layout.fillWidth: true
    Layout.fillHeight: true
    radius: 10
    color: "#FFFFFF"
    border.color: "#D3DCE8"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        Label {
            text: root.title
            color: "#1F2937"
            font.pixelSize: 13
            font.bold: true
        }

        TextArea {
            Layout.fillWidth: true
            Layout.fillHeight: true
            readOnly: true
            selectByMouse: true
            text: root.text
            wrapMode: TextArea.NoWrap
            font.family: "Consolas"
            font.pixelSize: 12
            color: "#1F2937"
            background: Rectangle {
                radius: 6
                color: "#F8FAFC"
                border.color: "#EEF2F7"
            }
        }
    }
}
