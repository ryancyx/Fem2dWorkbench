import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property real modelWidth: 2.0
    property real modelHeight: 1.0
    property int meshNx: 4
    property int meshNy: 2
    signal editParameters()
    signal createProject()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "自动网格"
            subtitle: "基于矩形几何生成结构化 CST 三角形网格。"
            badge: "CST"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ParameterCard {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                title: "网格估算"
                rows: [
                    { label: "nx", value: String(root.meshNx) },
                    { label: "ny", value: String(root.meshNy) },
                    { label: "节点数", value: String((root.meshNx + 1) * (root.meshNy + 1)) },
                    { label: "单元数", value: String(2 * root.meshNx * root.meshNy) },
                    { label: "单元类型", value: "CST" }
                ]
            }

            IndustrialPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 12

                    MeshPreview {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        mode: "mesh"
                        nx: root.meshNx
                        ny: root.meshNy
                        widthValue: root.modelWidth
                        heightValue: root.modelHeight
                    }

                    RowLayout {
                        SecondaryButton { text: "编辑网格参数"; onClicked: root.editParameters() }
                        PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
                    }
                }
            }
        }
    }
}
