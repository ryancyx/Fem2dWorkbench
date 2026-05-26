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
            title: "零件"
            subtitle: "当前版本支持单矩形零件。"
            badge: "矩形"
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            ParameterCard {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                title: "几何参数"
                rows: [
                    { label: "几何类型", value: "矩形" },
                    { label: "宽度", value: String(root.modelWidth) },
                    { label: "高度", value: String(root.modelHeight) },
                    { label: "零件 ID", value: "part_rectangle" }
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
                        mode: "part"
                        widthValue: root.modelWidth
                        heightValue: root.modelHeight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "提示：当前版本支持单矩形零件，后续可扩展草图和多区域几何。"
                        color: "#6B7280"
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        SecondaryButton { text: "编辑几何参数"; onClicked: root.editParameters() }
                        PrimaryButton { text: "创建/更新工程"; onClicked: root.createProject() }
                    }
                }
            }
        }
    }
}
