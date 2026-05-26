import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root

    width: 1460
    height: 880
    minimumWidth: 1240
    minimumHeight: 760
    visible: true
    title: "Fem2dWorkbench"
    color: "#EEF3F8"

    property real modelWidth: 2.0
    property real modelHeight: 1.0
    property int meshNx: 4
    property int meshNy: 2
    property real youngModulus: 210000000000
    property real poissonRatio: 0.3
    property real thickness: 0.01
    property real edgeQy: -1000.0
    property string currentMode: "工程"
    property int resultTabIndex: 0

    function createOrUpdateProject() {
        bridge.createDefaultProject(modelWidth, modelHeight, youngModulus, poissonRatio, thickness, edgeQy)
        viewportPanel.requestPaint()
    }

    function solveProject() {
        bridge.solveCurrentProject(meshNx, meshNy)
        currentMode = "结果"
        resultTabIndex = 1
        viewportPanel.requestPaint()
    }

    function exportProjectResults() {
        bridge.exportResults("outputs/latest")
        resultTabIndex = 3
    }

    function setMode(modeName) {
        currentMode = modeName
    }

    function estimatedNodes() {
        return (meshNx + 1) * (meshNy + 1)
    }

    function estimatedElements() {
        return 2 * meshNx * meshNy
    }

    function openParameterDialog() {
        widthField.text = String(modelWidth)
        heightField.text = String(modelHeight)
        eField.text = String(youngModulus)
        nuField.text = String(poissonRatio)
        thicknessField.text = String(thickness)
        nxField.text = String(meshNx)
        nyField.text = String(meshNy)
        qyField.text = String(edgeQy)
        parameterDialog.open()
    }

    function applyParameters() {
        var w = Number(widthField.text)
        var h = Number(heightField.text)
        var e = Number(eField.text)
        var nu = Number(nuField.text)
        var t = Number(thicknessField.text)
        var nx = parseInt(nxField.text)
        var ny = parseInt(nyField.text)
        var qy = Number(qyField.text)

        if (isNaN(w) || isNaN(h) || isNaN(e) || isNaN(nu)
                || isNaN(t) || isNaN(nx) || isNaN(ny) || isNaN(qy)) {
            console.log("参数输入无效")
            return
        }

        modelWidth = w
        modelHeight = h
        youngModulus = e
        poissonRatio = nu
        thickness = t
        meshNx = nx
        meshNy = ny
        edgeQy = qy
        parameterDialog.close()
    }

    menuBar: MenuBar {
        Menu {
            title: "文件"
            MenuItem { text: "新建工程"; onTriggered: bridge.newProject() }
            MenuItem { text: "创建/更新工程"; onTriggered: root.createOrUpdateProject() }
            MenuItem { text: "保存工程"; onTriggered: bridge.saveCurrentProject("outputs/latest/current_project.f2dw.json") }
            MenuItem { text: "打开工程"; onTriggered: bridge.loadProject("outputs/latest/current_project.f2dw.json") }
            MenuItem { text: "导出结果"; onTriggered: root.exportProjectResults() }
            MenuSeparator {}
            MenuItem { text: "退出"; onTriggered: Qt.quit() }
        }

        Menu {
            title: "建模"
            MenuItem { text: "工程"; onTriggered: root.setMode("工程") }
            MenuItem { text: "零件"; onTriggered: root.setMode("零件") }
            MenuItem { text: "属性"; onTriggered: root.setMode("属性") }
            MenuItem { text: "装配"; onTriggered: root.setMode("装配") }
        }

        Menu {
            title: "分析"
            MenuItem { text: "边界条件"; onTriggered: root.setMode("边界") }
            MenuItem { text: "载荷"; onTriggered: root.setMode("载荷") }
            MenuItem { text: "网格"; onTriggered: root.setMode("网格") }
            MenuItem { text: "求解"; onTriggered: root.solveProject() }
        }

        Menu {
            title: "结果"
            MenuItem { text: "结果查看"; onTriggered: root.setMode("结果") }
            MenuItem { text: "导出结果"; onTriggered: root.exportProjectResults() }
        }

        Menu {
            title: "帮助"
            MenuItem { text: "关于 Fem2dWorkbench"; onTriggered: aboutDialog.open() }
        }
    }

    header: RibbonBar {
        currentMode: root.currentMode
        onModeSelected: function(modeName) { root.setMode(modeName) }
        onEditParameters: root.openParameterDialog()
        onCreateProject: root.createOrUpdateProject()
        onSolve: root.solveProject()
        onExportResults: root.exportProjectResults()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            ModelTreePanel {
                Layout.preferredWidth: 310
                Layout.fillHeight: true
                currentMode: root.currentMode
                modelWidth: root.modelWidth
                modelHeight: root.modelHeight
                meshNx: root.meshNx
                meshNy: root.meshNy
                youngModulus: root.youngModulus
                poissonRatio: root.poissonRatio
                thickness: root.thickness
                edgeQy: root.edgeQy
                onModeSelected: function(modeName) { root.setMode(modeName) }
                onEditParameters: root.openParameterDialog()
                onCreateProject: root.createOrUpdateProject()
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                ViewportPanel {
                    id: viewportPanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    mode: root.currentMode
                    nx: root.meshNx
                    ny: root.meshNy
                    widthValue: root.modelWidth
                    heightValue: root.modelHeight
                    hasSolution: bridge.hasSolution
                }

                DockPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 218
                    currentIndex: root.resultTabIndex
                    consoleText: bridge.statusText
                    nodeText: bridge.nodeRowsPreview
                    elementText: bridge.elementRowsPreview
                    onCurrentIndexChangedByUser: function(index) { root.resultTabIndex = index }
                    onExportRequested: root.exportProjectResults()
                }
            }

            PropertyInspector {
                Layout.preferredWidth: 330
                Layout.fillHeight: true
                currentMode: root.currentMode
                modelWidth: root.modelWidth
                modelHeight: root.modelHeight
                meshNx: root.meshNx
                meshNy: root.meshNy
                youngModulus: root.youngModulus
                poissonRatio: root.poissonRatio
                thickness: root.thickness
                edgeQy: root.edgeQy
                nodeCount: bridge.nodeCount
                elementCount: bridge.elementCount
                maxDisplacement: bridge.maxDisplacement
                maxDisplacementNodeId: bridge.maxDisplacementNodeId
                maxVonMises: bridge.maxVonMises
                maxVonMisesElementId: bridge.maxVonMisesElementId
                warningCount: bridge.warningCount
                hasSolution: bridge.hasSolution
                onEditParameters: root.openParameterDialog()
                onCreateProject: root.createOrUpdateProject()
                onSolve: root.solveProject()
                onExportResults: root.exportProjectResults()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 30
            color: "#F8FAFC"
            border.color: "#D3DCE8"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 12

                Label {
                    text: "Fem2dWorkbench"
                    color: "#1F2937"
                    font.pixelSize: 12
                    font.bold: true
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    text: "模块：" + root.currentMode
                    color: "#64748B"
                    font.pixelSize: 12
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    text: "工程：" + (bridge.hasProject ? bridge.projectName : "未创建")
                    color: "#64748B"
                    font.pixelSize: 12
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    text: "文件：" + (bridge.projectPath === "" ? "未保存" : bridge.projectPath)
                    color: "#64748B"
                    font.pixelSize: 12
                    elide: Text.ElideMiddle
                    Layout.maximumWidth: 260
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    text: bridge.hasProject ? (bridge.projectDirty ? "未保存" : "已保存") : "无工程"
                    color: bridge.projectDirty ? "#D97706" : (bridge.hasProject ? "#16A34A" : "#64748B")
                    font.pixelSize: 12
                    font.bold: bridge.hasProject
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    Layout.fillWidth: true
                    text: bridge.statusText
                    color: "#64748B"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }

                Label {
                    text: bridge.hasSolution ? "已求解" : "未求解"
                    color: bridge.hasSolution ? "#16A34A" : "#64748B"
                    font.pixelSize: 12
                    font.bold: bridge.hasSolution
                }

                Label {
                    text: "outputs/latest"
                    color: "#64748B"
                    font.pixelSize: 12
                }
            }
        }
    }

    Dialog {
        id: parameterDialog

        modal: true
        title: "参数设置"
        width: 560
        height: 560
        x: Math.round((root.width - width) / 2)
        y: Math.round((root.height - height) / 2)

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                Layout.fillWidth: true
                text: "应用参数后，请点击“创建/更新工程”和“求解”刷新结果。"
                color: "#64748B"
                font.pixelSize: 13
                wrapMode: Text.WordWrap
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: "#D3DCE8" }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 14
                rowSpacing: 10

                FormField { id: widthField; label: "宽度"; suffix: "m"; text: "2.0"; Layout.fillWidth: true }
                FormField { id: heightField; label: "高度"; suffix: "m"; text: "1.0"; Layout.fillWidth: true }
                FormField { id: eField; label: "弹性模量"; suffix: "Pa"; text: "210000000000"; Layout.fillWidth: true }
                FormField { id: nuField; label: "泊松比"; text: "0.3"; Layout.fillWidth: true }
                FormField { id: thicknessField; label: "厚度"; suffix: "m"; text: "0.01"; Layout.fillWidth: true }
                FormField { id: qyField; label: "右边界均布载荷"; suffix: "N/m²"; text: "-1000"; Layout.fillWidth: true }
                FormField { id: nxField; label: "横向网格数"; text: "4"; Layout.fillWidth: true }
                FormField { id: nyField; label: "纵向网格数"; text: "2"; Layout.fillWidth: true }
            }

            Item { Layout.fillHeight: true }
        }

        footer: RowLayout {
            spacing: 10

            Item { Layout.fillWidth: true }

            SecondaryButton {
                text: "取消"
                buttonWidth: 76
                onClicked: parameterDialog.close()
            }

            PrimaryButton {
                text: "应用参数"
                buttonWidth: 96
                onClicked: root.applyParameters()
            }
        }
    }

    Dialog {
        id: aboutDialog

        modal: true
        title: "关于 Fem2dWorkbench"
        width: 450
        standardButtons: Dialog.Ok

        ColumnLayout {
            width: parent.width
            spacing: 10

            Label {
                text: "Fem2dWorkbench"
                font.pixelSize: 24
                font.bold: true
                color: "#1F2937"
            }

            Label {
                text: "二维有限元工程工作台"
                font.pixelSize: 15
                color: "#64748B"
            }

            Label {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                text: "当前版本：工作台界面原型。\n当前后端支持：单矩形零件、CST 三角形网格、平面应力线性静力求解、结果导出。"
                color: "#64748B"
            }
        }
    }
}
