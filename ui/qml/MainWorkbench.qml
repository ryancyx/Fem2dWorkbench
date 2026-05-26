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
    property real viewportScale: 1.0
    property real viewportOffsetX: 0.0
    property real viewportOffsetY: 0.0
    property string viewportTool: "选择"
    property bool showGrid: true
    property bool showMesh: false
    property bool showBoundary: false
    property bool showLoad: false
    property bool showResultOverlay: false
    property real lastMouseX: 0.0
    property real lastMouseY: 0.0
    property bool isPanning: false

    function createOrUpdateProject() {
        bridge.createDefaultProject(modelWidth, modelHeight, youngModulus, poissonRatio, thickness, edgeQy)
        viewport.requestPaint()
    }

    function solveProject() {
        bridge.solveCurrentProject(meshNx, meshNy)
        setMode("结果")
        resultTabIndex = 1
        viewport.requestPaint()
    }

    function exportProjectResults() {
        bridge.exportResults("outputs/latest")
        resultTabIndex = 3
    }

    function setMode(modeName) {
        currentMode = modeName
        if (modeName === "边界") {
            showBoundary = true
        } else if (modeName === "载荷") {
            showLoad = true
        } else if (modeName === "网格") {
            showMesh = true
        } else if (modeName === "结果") {
            showMesh = true
            showResultOverlay = true
        }
        viewport.requestPaint()
    }

    function fitViewport() {
        viewportScale = 1.0
        viewportOffsetX = 0.0
        viewportOffsetY = 0.0
        viewport.requestPaint()
    }

    function setViewportTool(toolName) {
        viewportTool = toolName
    }

    function toggleMeshDisplay() {
        showMesh = !showMesh
        viewport.requestPaint()
    }

    function toggleBoundaryDisplay() {
        showBoundary = !showBoundary
        viewport.requestPaint()
    }

    function toggleLoadDisplay() {
        showLoad = !showLoad
        viewport.requestPaint()
    }

    function toggleResultOverlay() {
        showResultOverlay = !showResultOverlay
        viewport.requestPaint()
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
        viewport.requestPaint()
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

                Rectangle {
                    id: viewportPanel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#DCE6F0"
                    border.color: "#C2CEDB"
                    clip: true

                    function requestPaint() {
                        viewport.requestPaint()
                    }

                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 12
                        radius: 10
                        color: "#E4EBF3"
                        border.color: "#B9C6D6"
                        clip: true

                        Canvas {
                            id: viewport
                            anchors.fill: parent

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.clearRect(0, 0, width, height)
                                ctx.fillStyle = "#E4EBF3"
                                ctx.fillRect(0, 0, width, height)

                                if (root.showGrid) {
                                    ctx.strokeStyle = "#CBD5E1"
                                    ctx.lineWidth = 1
                                    var grid = 32
                                    for (var gx = 0; gx <= width; gx += grid) {
                                        ctx.beginPath()
                                        ctx.moveTo(gx, 0)
                                        ctx.lineTo(gx, height)
                                        ctx.stroke()
                                    }
                                    for (var gy = 0; gy <= height; gy += grid) {
                                        ctx.beginPath()
                                        ctx.moveTo(0, gy)
                                        ctx.lineTo(width, gy)
                                        ctx.stroke()
                                    }
                                }

                                var maxW = width * 0.60
                                var maxH = height * 0.52
                                var plateW = maxW
                                var plateH = plateW * root.modelHeight / Math.max(root.modelWidth, 0.0001)
                                if (plateH > maxH) {
                                    plateH = maxH
                                    plateW = plateH * root.modelWidth / Math.max(root.modelHeight, 0.0001)
                                }
                                plateW *= root.viewportScale
                                plateH *= root.viewportScale

                                var px = (width - plateW) / 2 + root.viewportOffsetX
                                var py = (height - plateH) / 2 + root.viewportOffsetY

                                if (root.currentMode === "装配") {
                                    ctx.strokeStyle = "#94A3B8"
                                    ctx.lineWidth = 1
                                    ctx.setLineDash([8, 6])
                                    ctx.strokeRect(px - 32 * root.viewportScale, py - 24 * root.viewportScale, plateW, plateH)
                                    ctx.setLineDash([])
                                }

                                ctx.fillStyle = "#F8FAFC"
                                ctx.strokeStyle = "#334155"
                                ctx.lineWidth = 2
                                ctx.fillRect(px, py, plateW, plateH)
                                ctx.strokeRect(px, py, plateW, plateH)

                                var meshVisible = root.showMesh || root.currentMode === "网格" || root.currentMode === "求解" || root.currentMode === "结果"
                                if (meshVisible) {
                                    ctx.strokeStyle = "#7D8EA3"
                                    ctx.lineWidth = 1
                                    for (var i = 1; i < root.meshNx; i++) {
                                        var x = px + plateW * i / root.meshNx
                                        ctx.beginPath()
                                        ctx.moveTo(x, py)
                                        ctx.lineTo(x, py + plateH)
                                        ctx.stroke()
                                    }
                                    for (var j = 1; j < root.meshNy; j++) {
                                        var y = py + plateH * j / root.meshNy
                                        ctx.beginPath()
                                        ctx.moveTo(px, y)
                                        ctx.lineTo(px + plateW, y)
                                        ctx.stroke()
                                    }
                                    for (var cx = 0; cx < root.meshNx; cx++) {
                                        for (var cy = 0; cy < root.meshNy; cy++) {
                                            var x0 = px + plateW * cx / root.meshNx
                                            var x1 = px + plateW * (cx + 1) / root.meshNx
                                            var y0 = py + plateH * cy / root.meshNy
                                            var y1 = py + plateH * (cy + 1) / root.meshNy
                                            ctx.beginPath()
                                            ctx.moveTo(x0, y1)
                                            ctx.lineTo(x1, y0)
                                            ctx.stroke()
                                        }
                                    }
                                }

                                var boundaryVisible = root.showBoundary || root.currentMode === "边界"
                                if (boundaryVisible) {
                                    ctx.strokeStyle = "#2563EB"
                                    ctx.lineWidth = 6
                                    ctx.beginPath()
                                    ctx.moveTo(px, py)
                                    ctx.lineTo(px, py + plateH)
                                    ctx.stroke()
                                    ctx.fillStyle = "#2563EB"
                                    for (var b = 0; b <= 5; b++) {
                                        var by = py + plateH * b / 5
                                        ctx.beginPath()
                                        ctx.arc(px - 12 * root.viewportScale, by, 4, 0, Math.PI * 2)
                                        ctx.fill()
                                    }
                                }

                                var loadVisible = root.showLoad || root.currentMode === "载荷"
                                if (loadVisible) {
                                    ctx.strokeStyle = "#D97706"
                                    ctx.fillStyle = "#D97706"
                                    ctx.lineWidth = 2
                                    for (var a = 1; a <= 5; a++) {
                                        var ay = py + plateH * a / 6
                                        var ax = px + plateW + 38 * root.viewportScale
                                        ctx.beginPath()
                                        ctx.moveTo(ax, ay - 28 * root.viewportScale)
                                        ctx.lineTo(ax, ay)
                                        ctx.stroke()
                                        ctx.beginPath()
                                        ctx.moveTo(ax - 6, ay - 8)
                                        ctx.lineTo(ax, ay)
                                        ctx.lineTo(ax + 6, ay - 8)
                                        ctx.closePath()
                                        ctx.fill()
                                    }
                                    ctx.lineWidth = 4
                                    ctx.beginPath()
                                    ctx.moveTo(px + plateW, py)
                                    ctx.lineTo(px + plateW, py + plateH)
                                    ctx.stroke()
                                }

                                var resultVisible = (root.showResultOverlay || root.currentMode === "结果") && bridge.hasSolution
                                if (resultVisible) {
                                    var grad = ctx.createLinearGradient(px, py, px + plateW, py + plateH)
                                    grad.addColorStop(0.0, "rgba(37,99,235,0.10)")
                                    grad.addColorStop(0.55, "rgba(22,163,74,0.12)")
                                    grad.addColorStop(1.0, "rgba(217,119,6,0.16)")
                                    ctx.fillStyle = grad
                                    ctx.fillRect(px, py, plateW, plateH)
                                    ctx.strokeStyle = "#334155"
                                    ctx.lineWidth = 2
                                    ctx.strokeRect(px, py, plateW, plateH)
                                }

                                var visibleFlags = []
                                if (meshVisible) visibleFlags.push("网格")
                                if (boundaryVisible) visibleFlags.push("约束")
                                if (loadVisible) visibleFlags.push("载荷")
                                if (resultVisible) visibleFlags.push("结果")
                                if (visibleFlags.length === 0) visibleFlags.push("基础模型")

                                ctx.fillStyle = "#334155"
                                ctx.font = "13px 'Microsoft YaHei UI'"
                                ctx.fillText("视口 / " + root.currentMode, 18, 28)
                                ctx.fillStyle = "#64748B"
                                ctx.font = "12px 'Microsoft YaHei UI'"
                                ctx.fillText("缩放：" + Math.round(root.viewportScale * 100) + "%    工具：" + root.viewportTool, 18, 48)
                                ctx.fillText("显示：" + visibleFlags.join(" / "), 18, 68)
                            }

                            Connections {
                                target: root
                                function onCurrentModeChanged() { viewport.requestPaint() }
                                function onModelWidthChanged() { viewport.requestPaint() }
                                function onModelHeightChanged() { viewport.requestPaint() }
                                function onMeshNxChanged() { viewport.requestPaint() }
                                function onMeshNyChanged() { viewport.requestPaint() }
                                function onViewportScaleChanged() { viewport.requestPaint() }
                                function onViewportOffsetXChanged() { viewport.requestPaint() }
                                function onViewportOffsetYChanged() { viewport.requestPaint() }
                                function onShowGridChanged() { viewport.requestPaint() }
                                function onShowMeshChanged() { viewport.requestPaint() }
                                function onShowBoundaryChanged() { viewport.requestPaint() }
                                function onShowLoadChanged() { viewport.requestPaint() }
                                function onShowResultOverlayChanged() { viewport.requestPaint() }
                            }
                        }

                        MouseArea {
                            id: viewportMouseArea
                            anchors.fill: parent
                            hoverEnabled: true
                            acceptedButtons: Qt.LeftButton
                            cursorShape: root.viewportTool === "平移"
                                         ? (root.isPanning ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
                                         : Qt.ArrowCursor

                            onWheel: function(wheel) {
                                var factor = wheel.angleDelta.y > 0 ? 1.1 : 0.9
                                root.viewportScale = Math.max(0.4, Math.min(4.0, root.viewportScale * factor))
                                viewport.requestPaint()
                                wheel.accepted = true
                            }

                            onPressed: function(mouse) {
                                if (root.viewportTool === "平移") {
                                    root.isPanning = true
                                    root.lastMouseX = mouse.x
                                    root.lastMouseY = mouse.y
                                } else {
                                    console.log("视口选择坐标:", mouse.x, mouse.y)
                                }
                            }

                            onPositionChanged: function(mouse) {
                                if (root.isPanning && root.viewportTool === "平移") {
                                    root.viewportOffsetX += mouse.x - root.lastMouseX
                                    root.viewportOffsetY += mouse.y - root.lastMouseY
                                    root.lastMouseX = mouse.x
                                    root.lastMouseY = mouse.y
                                    viewport.requestPaint()
                                }
                            }

                            onReleased: function(mouse) {
                                root.isPanning = false
                            }

                            onCanceled: root.isPanning = false
                        }

                        Rectangle {
                            anchors.left: parent.left
                            anchors.top: parent.top
                            anchors.margins: 14
                            width: toolbarRow.implicitWidth + 16
                            height: 36
                            radius: 8
                            color: "#F8FAFC"
                            border.color: "#D3DCE8"

                            RowLayout {
                                id: toolbarRow
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 6

                                ViewToolButton { text: "适应窗口"; onClicked: root.fitViewport() }
                                ViewToolButton { text: "选择"; active: root.viewportTool === "选择"; onClicked: root.setViewportTool("选择") }
                                ViewToolButton { text: "平移"; active: root.viewportTool === "平移"; onClicked: root.setViewportTool("平移") }
                                ViewToolButton { text: "网格"; active: root.showMesh; onClicked: root.toggleMeshDisplay() }
                                ViewToolButton { text: "约束"; active: root.showBoundary; onClicked: root.toggleBoundaryDisplay() }
                                ViewToolButton { text: "载荷"; active: root.showLoad; onClicked: root.toggleLoadDisplay() }
                                ViewToolButton { text: "结果"; active: root.showResultOverlay; onClicked: root.toggleResultOverlay() }
                            }
                        }
                    }
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
                    text: "工具：" + root.viewportTool
                    color: "#64748B"
                    font.pixelSize: 12
                }

                Rectangle { width: 1; height: 14; color: "#D3DCE8" }

                Label {
                    text: "缩放：" + Math.round(root.viewportScale * 100) + "%"
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

    component ViewToolButton: Rectangle {
        id: toolButton

        property string text: ""
        property bool active: false

        signal clicked()

        width: Math.max(56, label.implicitWidth + 18)
        height: 24
        radius: 6
        color: active ? "#EAF2FF" : (mouse.containsMouse ? "#F1F5F9" : "#FFFFFF")
        border.color: active ? "#BFDBFE" : "#D3DCE8"

        Label {
            id: label
            anchors.centerIn: parent
            text: toolButton.text
            color: toolButton.active ? "#1D4ED8" : "#1F2937"
            font.pixelSize: 11
            font.bold: toolButton.active
        }

        MouseArea {
            id: mouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: toolButton.clicked()
        }
    }
}
