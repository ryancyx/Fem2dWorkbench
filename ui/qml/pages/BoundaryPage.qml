import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property real modelWidth: 2.0
    property real modelHeight: 1.0
    signal editParameters()
    signal createProject()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "边界条件"
            subtitle: "左边界施加 ux/uy 固定约束。"
            badge: "左边界固定"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ParameterCard {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                title: "边界条件"
                rows: [
                    { label: "目标", value: "左边界" },
                    { label: "ux 固定", value: "是" },
                    { label: "uy 固定", value: "是" },
                    { label: "ux 值", value: "0.0" },
                    { label: "uy 值", value: "0.0" }
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
                        mode: "boundary"
                        widthValue: root.modelWidth
                        heightValue: root.modelHeight
                    }

                    RowLayout {
                        SecondaryButton { text: "编辑参数"; onClicked: root.editParameters() }
                        PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
                    }
                }
            }
        }
    }
}
