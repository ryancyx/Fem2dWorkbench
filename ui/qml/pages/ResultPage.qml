import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property bool hasSolution: false
    property string maxDisplacement: ""
    property string maxVonMises: ""
    property string nodeRowsPreview: ""
    property string elementRowsPreview: ""
    property int nodeCount: 0
    property int elementCount: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 16

        PageHeader {
            title: "结果"
            subtitle: "查看求解摘要、节点位移和单元应力结果。"
            badge: root.hasSolution ? "已求解" : "无结果"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 14

            MetricCard { Layout.fillWidth: true; title: "最大位移"; value: root.hasSolution ? root.maxDisplacement : "-"; highlight: root.hasSolution }
            MetricCard { Layout.fillWidth: true; title: "最大冯·米塞斯"; value: root.hasSolution ? root.maxVonMises : "-"; highlight: root.hasSolution }
            MetricCard { Layout.fillWidth: true; title: "节点 / 单元"; value: root.hasSolution ? (root.nodeCount + " / " + root.elementCount) : "-" }
        }

        TabBar {
            id: resultTabs
            Layout.fillWidth: true
            TabButton { text: "摘要" }
            TabButton { text: "节点位移" }
            TabButton { text: "单元结果" }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: resultTabs.currentIndex

            ResultPreviewCard {
                title: "摘要"
                text: root.hasSolution
                      ? ("节点数: " + root.nodeCount + "\n单元数: " + root.elementCount
                         + "\n最大位移: " + root.maxDisplacement
                         + "\n最大冯·米塞斯: " + root.maxVonMises)
                      : "暂无结果。"
            }

            ResultPreviewCard {
                title: "节点位移"
                text: root.nodeRowsPreview
            }

            ResultPreviewCard {
                title: "单元结果"
                text: root.elementRowsPreview
            }
        }
    }
}
