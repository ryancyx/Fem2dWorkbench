import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    signal editParameters()
    signal createProject()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "工程总览"
            subtitle: "矩形板二维线弹性分析的参数化主流程。"
            badge: "Stage 7C"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            InfoCard {
                Layout.fillWidth: true
                title: "项目类型"
                body: "矩形板二维线弹性分析。当前工程使用单矩形零件、单材料截面和静力线性分析步。"
            }

            InfoCard {
                Layout.fillWidth: true
                title: "当前阶段"
                body: "参数化建模。通过参数弹窗定义几何、材料、网格和载荷，然后创建工程并求解。"
            }
        }

        IndustrialPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label {
                    text: "工程流程摘要"
                    color: "#111827"
                    font.pixelSize: 17
                    font.bold: true
                }

                Repeater {
                    model: [
                        "1. 定义矩形零件",
                        "2. 定义材料和厚度",
                        "3. 设置边界与载荷",
                        "4. 自动生成 CST 网格",
                        "5. 求解并查看结果"
                    ]

                    delegate: Label {
                        required property string modelData
                        Layout.fillWidth: true
                        text: modelData
                        color: "#374151"
                        font.pixelSize: 14
                    }
                }

                Item { Layout.fillHeight: true }

                RowLayout {
                    spacing: 10
                    SecondaryButton { text: "编辑参数"; onClicked: root.editParameters() }
                    PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
                }
            }
        }
    }
}
