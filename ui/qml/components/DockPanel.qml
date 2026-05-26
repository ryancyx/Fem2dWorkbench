import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property int currentIndex: 0
    property string consoleText: ""
    property string nodeText: ""
    property string elementText: ""

    signal currentIndexChangedByUser(int index)
    signal exportRequested()

    color: "#F8FAFC"
    border.color: "#D3DCE8"
    implicitHeight: 218

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 40
            color: "#F8FAFC"
            border.color: "#D3DCE8"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 8

                DockTab { text: "状态日志"; index: 0; active: root.currentIndex === 0; onClicked: root.setIndex(index) }
                DockTab { text: "节点位移"; index: 1; active: root.currentIndex === 1; onClicked: root.setIndex(index) }
                DockTab { text: "单元结果"; index: 2; active: root.currentIndex === 2; onClicked: root.setIndex(index) }
                DockTab { text: "导出"; index: 3; active: root.currentIndex === 3; onClicked: root.setIndex(index) }

                Item { Layout.fillWidth: true }

                Label {
                    text: "输出面板"
                    color: "#64748B"
                    font.pixelSize: 12
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: root.currentIndex

            ResultTextArea { text: root.consoleText }
            ResultTextArea { text: root.nodeText === "" ? "暂无节点结果。请先创建工程并求解。" : root.nodeText }
            ResultTextArea { text: root.elementText === "" ? "暂无单元结果。请先创建工程并求解。" : root.elementText }

            Rectangle {
                color: "#FFFFFF"

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 8

                    Label {
                        text: "导出目录：outputs/latest"
                        color: "#1F2937"
                        font.pixelSize: 14
                        font.bold: true
                    }

                    Label {
                        text: "将生成节点位移、单元结果与摘要文本。"
                        color: "#64748B"
                        font.pixelSize: 12
                    }

                    PrimaryButton {
                        text: "导出结果"
                        buttonWidth: 118
                        onClicked: root.exportRequested()
                    }
                }
            }
        }
    }

    function setIndex(index) {
        currentIndex = index
        currentIndexChangedByUser(index)
    }

    component DockTab: Rectangle {
        id: tab

        property string text: ""
        property int index: 0
        property bool active: false

        signal clicked()

        width: 92
        height: 28
        radius: 8
        color: active ? "#EAF2FF" : (mouse.containsMouse ? "#F1F5F9" : "#FFFFFF")
        border.color: active ? "#BFDBFE" : "#D3DCE8"

        Label {
            anchors.centerIn: parent
            text: tab.text
            color: tab.active ? "#1D4ED8" : "#1F2937"
            font.pixelSize: 12
            font.bold: tab.active
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: tab.clicked()
        }
    }

    component ResultTextArea: TextArea {
        readOnly: true
        font.family: "Consolas"
        font.pixelSize: 12
        wrapMode: TextArea.NoWrap
        color: "#1F2937"
        selectByMouse: true
        background: Rectangle {
            color: "#FFFFFF"
            border.color: "#EEF2F7"
            radius: 6
        }
    }
}
