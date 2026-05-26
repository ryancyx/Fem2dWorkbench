import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property bool hasSolution: false
    property string statusText: ""
    signal exportResults()

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "导出"
            subtitle: "将整理后的结果表导出为 CSV/TXT。"
            badge: "outputs/latest"
        }

        ParameterCard {
            Layout.fillWidth: true
            title: "导出文件"
            rows: [
                { label: "目录", value: "outputs/latest" },
                { label: "节点表", value: "node_displacements.csv" },
                { label: "单元表", value: "element_results.csv" },
                { label: "摘要", value: "summary.txt" }
            ]
        }

        IndustrialPanel {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 12

                Label {
                    text: "导出操作"
                    color: "#111827"
                    font.pixelSize: 17
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: root.hasSolution ? "当前已有求解结果，可以导出。" : "没有求解结果时，导出会返回状态提示。"
                    color: "#6B7280"
                    wrapMode: Text.WordWrap
                }

                PrimaryButton {
                    text: "导出结果"
                    enabled: root.hasSolution
                    onClicked: root.exportResults()
                }

                Label {
                    Layout.fillWidth: true
                    text: root.statusText
                    color: "#374151"
                    wrapMode: Text.WordWrap
                }

                Item { Layout.fillHeight: true }
            }
        }
    }
}
