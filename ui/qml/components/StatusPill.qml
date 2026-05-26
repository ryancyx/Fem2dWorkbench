import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string text: ""
    property string tone: "blue"

    width: Math.max(64, label.implicitWidth + 18)
    height: 24
    radius: 8
    color: tone === "green" ? "#DCFCE7" : tone === "amber" ? "#FEF3C7" : "#EAF2FF"
    border.color: tone === "green" ? "#86EFAC" : tone === "amber" ? "#FCD34D" : "#BFDBFE"

    Label {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.tone === "green" ? "#15803D" : root.tone === "amber" ? "#92400E" : "#1D4ED8"
        font.pixelSize: 11
        font.bold: true
    }
}
