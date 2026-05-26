import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string currentMode: "工程"
    property real modelWidth: 2.0
    property real modelHeight: 1.0
    property int meshNx: 4
    property int meshNy: 2
    property real youngModulus: 210000000000
    property real poissonRatio: 0.3
    property real thickness: 0.01
    property real edgeQy: -1000
    property int nodeCount: 0
    property int elementCount: 0
    property string maxDisplacement: ""
    property string maxDisplacementNodeId: ""
    property string maxVonMises: ""
    property string maxVonMisesElementId: ""
    property int warningCount: 0
    property bool hasSolution: false

    signal editParameters()
    signal createProject()
    signal solve()
    signal exportResults()

    color: "#F8FAFC"
    border.color: "#D3DCE8"
    implicitWidth: 330

    function display(value) {
        if (!hasSolution) return "—"
        if (value === undefined || value === null || value === "") return "—"
        return String(value)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        PanelTitle {
            title: "属性 / 结果"
            subtitle: "当前对象与求解摘要"
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                width: root.width
                spacing: 12

                ParameterCard {
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    Layout.topMargin: 12
                    title: "当前对象"
                    rows: [
                        { label: "模块", value: root.currentMode },
                        { label: "零件", value: "矩形零件" },
                        { label: "属性", value: "钢材薄板属性" },
                        { label: "分析步", value: "线性静力" },
                        { label: "边界", value: "左边界固定" },
                        { label: "载荷", value: "右边界 qy = " + root.edgeQy },
                        { label: "网格", value: root.meshNx + " × " + root.meshNy + " CST" }
                    ]
                }

                SecondaryButton {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    text: "编辑参数"
                    onClicked: root.editParameters()
                }

                IndustrialPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    implicitHeight: summaryColumn.implicitHeight + 24

                    ColumnLayout {
                        id: summaryColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: "结果摘要"
                            color: "#1F2937"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        MetricCard { title: "节点数"; value: root.hasSolution ? String(root.nodeCount) : "—"; highlight: root.hasSolution }
                        MetricCard { title: "单元数"; value: root.hasSolution ? String(root.elementCount) : "—"; highlight: root.hasSolution }
                        MetricCard { title: "最大位移"; value: root.display(root.maxDisplacement) }
                        MetricCard { title: "最大位移节点"; value: root.display(root.maxDisplacementNodeId) }
                        MetricCard { title: "最大冯·米塞斯"; value: root.display(root.maxVonMises) }
                        MetricCard { title: "最大应力单元"; value: root.display(root.maxVonMisesElementId) }
                        MetricCard { title: "警告数量"; value: root.hasSolution ? String(root.warningCount) : "—" }
                    }
                }

                IndustrialPanel {
                    Layout.fillWidth: true
                    Layout.leftMargin: 12
                    Layout.rightMargin: 12
                    Layout.bottomMargin: 12
                    implicitHeight: actionColumn.implicitHeight + 24

                    ColumnLayout {
                        id: actionColumn
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 12
                        spacing: 8

                        Label {
                            text: "操作"
                            color: "#1F2937"
                            font.pixelSize: 14
                            font.bold: true
                        }

                        SecondaryButton { Layout.fillWidth: true; text: "创建/更新工程"; onClicked: root.createProject() }
                        PrimaryButton { Layout.fillWidth: true; text: "求解"; onClicked: root.solve() }
                        SecondaryButton { Layout.fillWidth: true; text: "导出"; onClicked: root.exportResults() }
                    }
                }
            }
        }
    }

    component PanelTitle: Rectangle {
        property string title: ""
        property string subtitle: ""

        Layout.fillWidth: true
        height: 58
        color: "#F8FAFC"
        border.color: "#D3DCE8"

        Column {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: 14
            spacing: 2

            Label { text: parent.parent.title; color: "#1F2937"; font.pixelSize: 16; font.bold: true }
            Label { text: parent.parent.subtitle; color: "#64748B"; font.pixelSize: 12 }
        }
    }
}
