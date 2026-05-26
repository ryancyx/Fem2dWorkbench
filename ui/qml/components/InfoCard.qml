import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string body: ""

    Layout.fillWidth: true
    implicitHeight: content.implicitHeight + 24
    radius: 10
    color: "#FFFFFF"
    border.color: "#D3DCE8"

    ColumnLayout {
        id: content
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 6

        Label {
            text: root.title
            color: "#1F2937"
            font.pixelSize: 14
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: root.body
            color: "#64748B"
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }
}
