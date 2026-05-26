import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root

    property string title: ""
    property string subtitle: ""
    property string badge: ""

    Layout.fillWidth: true
    spacing: 10

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2

        Label {
            text: root.title
            color: "#1F2937"
            font.pixelSize: 18
            font.bold: true
        }

        Label {
            text: root.subtitle
            color: "#64748B"
            font.pixelSize: 12
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }

    StatusPill {
        visible: root.badge !== ""
        text: root.badge
        tone: "blue"
    }
}
