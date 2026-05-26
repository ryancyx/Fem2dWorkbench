import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string mode: "工程"

    width: 300
    height: 36
    radius: 8
    color: "#F8FAFC"
    border.color: "#D3DCE8"

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 6

        ToolChip { text: "适应窗口" }
        ToolChip { text: "平移" }
        ToolChip { text: "选择" }
        ToolChip { text: root.mode }
    }

    component ToolChip: Rectangle {
        property string text: ""

        width: Math.max(56, label.implicitWidth + 18)
        height: 24
        radius: 6
        color: "#F8FAFC"
        border.color: "#D3DCE8"

        Label {
            id: label
            anchors.centerIn: parent
            text: parent.text
            color: "#1F2937"
            font.pixelSize: 11
        }
    }
}
