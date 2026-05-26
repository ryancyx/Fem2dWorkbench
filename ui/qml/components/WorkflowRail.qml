import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property int currentIndex: 0
    signal pageSelected(int index)

    color: "#1F2937"
    implicitWidth: 242

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Label {
            Layout.fillWidth: true
            text: "工作流"
            color: "#F9FAFB"
            font.pixelSize: 18
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: "工程模块"
            color: "#9CA3AF"
            font.pixelSize: 12
        }

        Repeater {
            model: [
                { title: "工程", desc: "总览" },
                { title: "零件", desc: "矩形几何" },
                { title: "属性", desc: "截面材料" },
                { title: "装配", desc: "单实例" },
                { title: "分析步", desc: "静力线性" },
                { title: "边界", desc: "固定约束" },
                { title: "载荷", desc: "均布载荷" },
                { title: "网格", desc: "CST 网格" },
                { title: "求解", desc: "编译求解" },
                { title: "结果", desc: "结果查看" },
                { title: "导出", desc: "文件输出" }
            ]

            delegate: Rectangle {
                id: item

                required property int index
                required property var modelData

                Layout.fillWidth: true
                height: 48
                radius: 10
                color: item.index === root.currentIndex ? "#2563EB" : (hoverArea.containsMouse ? "#374151" : "transparent")
                border.color: item.index === root.currentIndex ? "#60A5FA" : "transparent"

                Behavior on color {
                    ColorAnimation { duration: 120 }
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 10

                    Rectangle {
                        Layout.preferredWidth: 26
                        Layout.preferredHeight: 26
                        radius: 13
                        color: item.index === root.currentIndex ? "#FFFFFF" : "#111827"
                        border.color: item.index === root.currentIndex ? "#FFFFFF" : "#4B5563"

                        Label {
                            anchors.centerIn: parent
                            text: String(item.index)
                            color: item.index === root.currentIndex ? "#2563EB" : "#D1D5DB"
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1

                        Label {
                            Layout.fillWidth: true
                            text: item.modelData.title
                            color: "#FFFFFF"
                            font.pixelSize: 14
                            font.bold: item.index === root.currentIndex
                            elide: Text.ElideRight
                        }

                        Label {
                            Layout.fillWidth: true
                            text: item.modelData.desc
                            color: item.index === root.currentIndex ? "#DBEAFE" : "#9CA3AF"
                            font.pixelSize: 11
                            elide: Text.ElideRight
                        }
                    }
                }

                MouseArea {
                    id: hoverArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: root.pageSelected(item.index)
                }
            }
        }

        Item { Layout.fillHeight: true }
    }
}
