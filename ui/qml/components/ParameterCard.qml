import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property var rows: []

    Layout.fillWidth: true
    implicitHeight: body.implicitHeight + 24
    radius: 10
    color: "#FFFFFF"
    border.color: "#D3DCE8"

    ColumnLayout {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 12
        spacing: 8

        Label {
            text: root.title
            color: "#1F2937"
            font.pixelSize: 14
            font.bold: true
        }

        Repeater {
            model: root.rows

            delegate: RowLayout {
                required property var modelData

                Layout.fillWidth: true

                Label {
                    text: modelData.label
                    color: "#64748B"
                    font.pixelSize: 12
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }

                Label {
                    text: modelData.value
                    color: "#1F2937"
                    font.pixelSize: 12
                    font.bold: true
                    horizontalAlignment: Text.AlignRight
                    Layout.preferredWidth: 136
                    elide: Text.ElideRight
                }
            }
        }
    }
}
