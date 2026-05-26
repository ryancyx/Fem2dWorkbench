import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property int meshNx: 4
    property int meshNy: 2
    property real edgeQy: -1000
    property int nodeCount: 0
    property int elementCount: 0
    property string statusText: ""
    signal solve()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "编译求解"
            subtitle: "执行网格到 FEMModel 编译，并调用静力线性求解器。"
            badge: "运行"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            ParameterCard {
                Layout.fillWidth: true
                title: "求解配置"
                rows: [
                    { label: "零件", value: "part_rectangle" },
                    { label: "分析步", value: "step_static" },
                    { label: "网格", value: root.meshNx + " × " + root.meshNy },
                    { label: "边界", value: "左边界固定" },
                    { label: "右边界 qy", value: String(root.edgeQy) }
                ]
            }

            ParameterCard {
                Layout.fillWidth: true
                title: "上次结果"
                rows: [
                    { label: "节点数", value: root.nodeCount > 0 ? String(root.nodeCount) : "-" },
                    { label: "单元数", value: root.elementCount > 0 ? String(root.elementCount) : "-" },
                    { label: "状态", value: root.statusText === "" ? "-" : root.statusText }
                ]
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
                    text: "求解操作"
                    color: "#111827"
                    font.pixelSize: 17
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: "如果尚未创建工程，求解入口会由桥接层返回状态提示。"
                    color: "#6B7280"
                    wrapMode: Text.WordWrap
                }

                PrimaryButton {
                    text: "求解"
                    onClicked: root.solve()
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
