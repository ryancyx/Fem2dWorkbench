import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root

    property string currentMode: "工程"
    signal modeSelected(string modeName)
    signal editParameters()
    signal createProject()
    signal solve()
    signal exportResults()

    implicitHeight: 98
    spacing: 0

    Rectangle {
        Layout.fillWidth: true
        height: 54
        color: "#F8FAFC"
        border.color: "#D3DCE8"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            spacing: 14

            Rectangle {
                width: 30
                height: 30
                radius: 8
                color: "#2563EB"

                Label {
                    anchors.centerIn: parent
                    text: "F"
                    color: "#FFFFFF"
                    font.pixelSize: 17
                    font.bold: true
                }
            }

            ColumnLayout {
                spacing: 0

                Label {
                    text: "Fem2dWorkbench"
                    color: "#1F2937"
                    font.pixelSize: 19
                    font.bold: true
                }

                Label {
                    text: "二维有限元工程工作台"
                    color: "#64748B"
                    font.pixelSize: 12
                }
            }

            Rectangle { width: 1; height: 26; color: "#D3DCE8" }

            Label {
                text: "当前模块：" + root.currentMode
                color: "#1F2937"
                font.pixelSize: 13
            }

            Label {
                text: modeDescription()
                color: "#64748B"
                font.pixelSize: 12
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            SecondaryButton { text: "参数"; buttonWidth: 76; onClicked: root.editParameters() }
            SecondaryButton { text: "创建/更新"; buttonWidth: 96; onClicked: root.createProject() }
            PrimaryButton { text: "求解"; buttonWidth: 96; onClicked: root.solve() }
            SecondaryButton { text: "导出"; buttonWidth: 76; onClicked: root.exportResults() }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        height: 44
        color: "#FFFFFF"
        border.color: "#D3DCE8"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8

            ModuleTab { text: "工程"; selected: root.currentMode === "工程"; onClicked: root.modeSelected("工程") }
            ModuleTab { text: "零件"; selected: root.currentMode === "零件"; onClicked: root.modeSelected("零件") }
            ModuleTab { text: "属性"; selected: root.currentMode === "属性"; onClicked: root.modeSelected("属性") }
            ModuleTab { text: "装配"; selected: root.currentMode === "装配"; onClicked: root.modeSelected("装配") }

            Rectangle { width: 1; height: 22; color: "#D3DCE8" }

            ModuleTab { text: "边界"; selected: root.currentMode === "边界"; onClicked: root.modeSelected("边界") }
            ModuleTab { text: "载荷"; selected: root.currentMode === "载荷"; onClicked: root.modeSelected("载荷") }
            ModuleTab { text: "网格"; selected: root.currentMode === "网格"; onClicked: root.modeSelected("网格") }
            ModuleTab { text: "求解"; selected: root.currentMode === "求解"; onClicked: root.modeSelected("求解") }
            ModuleTab { text: "结果"; selected: root.currentMode === "结果"; onClicked: root.modeSelected("结果") }
            ModuleTab { text: "导出"; selected: root.currentMode === "导出"; onClicked: root.modeSelected("导出") }

            Item { Layout.fillWidth: true }
        }
    }

    function modeDescription() {
        if (currentMode === "工程") return "工程总览与完整有限元分析流程。"
        if (currentMode === "零件") return "定义二维矩形零件的几何尺寸。"
        if (currentMode === "属性") return "定义材料参数、厚度与平面应力属性。"
        if (currentMode === "装配") return "当前为单零件单实例装配，后续支持多零件。"
        if (currentMode === "边界") return "左边界固定 ux 与 uy。"
        if (currentMode === "载荷") return "右边界施加竖向均布载荷。"
        if (currentMode === "网格") return "矩形区域自动生成结构化 CST 三角形网格。"
        if (currentMode === "求解") return "编译工程模型并调用线性静力求解器。"
        if (currentMode === "结果") return "查看节点位移、单元结果与摘要。"
        if (currentMode === "导出") return "导出节点位移、单元结果与摘要文件。"
        return ""
    }
}
