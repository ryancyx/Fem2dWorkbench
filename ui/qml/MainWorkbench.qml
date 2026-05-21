import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root

    width: 1280
    height: 800
    visible: true
    title: "Fem2dWorkbench"

    color: "#f3f4f6"

    Rectangle {
        anchors.fill: parent
        color: "#f3f4f6"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                height: 56
                color: "#111827"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    spacing: 12

                    Text {
                        text: "Fem2dWorkbench"
                        color: "white"
                        font.pixelSize: 20
                        font.bold: true
                    }

                    Text {
                        text: "二维有限元工程工作台"
                        color: "#d1d5db"
                        font.pixelSize: 14
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "新建工程"
                        onClicked: bridge.createNewProject()
                    }

                    Button {
                        text: "打开"
                        onClicked: bridge.openProject()
                    }

                    Button {
                        text: "保存"
                        onClicked: bridge.saveProject()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    width: 220
                    Layout.fillHeight: true
                    color: "#1f2937"

                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 8

                        Text {
                            text: "工作流程"
                            color: "#9ca3af"
                            font.pixelSize: 13
                        }

                        Repeater {
                            model: [
                                "工程",
                                "零件",
                                "属性",
                                "装配",
                                "分析步",
                                "载荷",
                                "边界条件",
                                "网格",
                                "求解",
                                "结果",
                                "网格编辑",
                                "导出"
                            ]

                            delegate: Rectangle {
                                width: parent.width
                                height: 36
                                radius: 8
                                color: index === 0 ? "#374151" : "transparent"

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    text: modelData
                                    color: "white"
                                    font.pixelSize: 14
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#ffffff"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 24
                        spacing: 18

                        Rectangle {
                            Layout.fillWidth: true
                            height: 110
                            radius: 16
                            color: "#eef2ff"
                            border.color: "#c7d2fe"

                            Column {
                                anchors.centerIn: parent
                                spacing: 8

                                Text {
                                    text: "阶段 0：空白 Workbench 窗口已就绪"
                                    color: "#111827"
                                    font.pixelSize: 24
                                    font.bold: true
                                    anchors.horizontalCenter: parent.horizontalCenter
                                }

                                Text {
                                    text: "下一步：迁移 Fem2dStudio 的 core/fem 与 core/solver，并建立 solver_api.py"
                                    color: "#4b5563"
                                    font.pixelSize: 15
                                    anchors.horizontalCenter: parent.horizontalCenter
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 16
                            color: "#f9fafb"
                            border.color: "#e5e7eb"

                            Text {
                                anchors.centerIn: parent
                                text: "这里未来会显示 ProjectPage / PartPage / MeshPage / ResultPage"
                                color: "#6b7280"
                                font.pixelSize: 18
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 34
                color: "#e5e7eb"

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    text: bridge.statusText
                    color: "#374151"
                    font.pixelSize: 13
                }
            }
        }
    }
}