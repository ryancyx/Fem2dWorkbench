import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property real modelWidth: 2.0
    property real modelHeight: 1.0
    property real edgeQy: -1000
    signal editParameters()
    signal createProject()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "载荷"
            subtitle: "右边界施加均布边载荷，并在编译阶段等效为节点力。"
            badge: "均布边载荷"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ParameterCard {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                title: "载荷"
                rows: [
                    { label: "目标", value: "右边界" },
                    { label: "类型", value: "edge_uniform" },
                    { label: "qx", value: "0" },
                    { label: "qy", value: String(root.edgeQy) }
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
                        mode: "load"
                        widthValue: root.modelWidth
                        heightValue: root.modelHeight
                    }

                    RowLayout {
                        SecondaryButton { text: "编辑载荷参数"; onClicked: root.editParameters() }
                        PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
                    }
                }
            }
        }
    }
}
