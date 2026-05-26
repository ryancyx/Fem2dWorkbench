import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string value: "—"
    property string subtitle: ""
    property bool highlight: false

    Layout.fillWidth: true
    implicitHeight: subtitle === "" ? 42 : 56
    radius: 8
    color: highlight ? "#EAF2FF" : "#F8FAFC"
    border.color: highlight ? "#BFDBFE" : "#D3DCE8"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        spacing: 8

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Label {
                text: root.title
                color: "#64748B"
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            Label {
                visible: root.subtitle !== ""
                text: root.subtitle
                color: "#94A3B8"
                font.pixelSize: 10
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        Label {
            text: root.value === "" ? "—" : root.value
            color: root.highlight ? "#1D4ED8" : "#1F2937"
            font.pixelSize: 13
            font.bold: true
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
            Layout.maximumWidth: 150
        }
    }
}
