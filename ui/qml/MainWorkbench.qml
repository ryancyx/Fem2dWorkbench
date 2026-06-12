import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import "components"

ApplicationWindow {
    id: root

    width: 1460
    height: 900
    minimumWidth: 1280
    minimumHeight: 760
    visible: true
    title: "Fem2dWorkbench"
    color: root.uiWindowBgColor

    property string currentMode: "建模与材料"
    // 视图缩放说明：viewportScaleDisplayBase 对应界面显示的 100%。
    // 需求：把旧缩放体系中的 35% 重新标记为界面上的 100%。
    // 注意：显示标定基准与绘制最小尺度基准分开，避免 100% 被强行撑回旧 100% 的大小。
    property real viewportLegacyScaleBase: 0.01
    property real viewportScaleDisplayBase: viewportLegacyScaleBase * 0.35
    property real defaultViewportScale: viewportScaleDisplayBase
    property real viewportScale: defaultViewportScale
    property real minViewportScale: viewportScaleDisplayBase * 0.01
    property real maxViewportScale: viewportScaleDisplayBase * 20.0
    property real viewportOffsetX: 0.0
    property real viewportOffsetY: 0.0
    property real lastMouseX: 0.0
    property real lastMouseY: 0.0
    property bool isPanning: false
    property bool viewportPanMode: false
    property bool isPanningViewport: false
    property bool isDraggingPoint: false
    property bool viewportClickCandidate: false
    property real viewportPressX: 0.0
    property real viewportPressY: 0.0
    property real panStartMouseX: 0.0
    property real panStartMouseY: 0.0
    property real panStartOffsetX: 0.0
    property real panStartOffsetY: 0.0
    property real clickMoveTolerance: 4.0
    property real sketchOriginX: 0.0
    property real sketchOriginY: 0.0
    property real sketchDrawScale: 100.0
    property real lastModelBoundsX: 0.0
    property real lastModelBoundsY: 0.0
    property real lastModelBoundsW: 0.0
    property real lastModelBoundsH: 0.0
    property real queryMarkerX: 0.0
    property real queryMarkerY: 0.0
    property bool hasQueryMarker: false
    property string viewportHint: ""
    property string selectedObjectType: "无"
    property string selectedObjectName: "未选择"
    property string selectedObjectDescription: "请在视口中点击点、边或闭合面。"
    property string resultOverlayMode: "none"
    property real leftPanelWidth: 300
    property real rightPanelWidth: 300
    property real defaultLeftPanelWidth: 300
    property real defaultRightPanelWidth: 300
    property real minLeftPanelWidth: 240
    property real minRightPanelWidth: 280
    property real minCenterPanelWidth: 620
    property real maxLeftPanelWidth: 420
    property real maxRightPanelWidth: 420
    property real splitterWidth: 8
    // v0.2.0 UI polish: conservative button/control metrics and shared visual tokens.
    property int uiButtonHeight: 34
    property int uiButtonCompactHeight: 30
    property int uiButtonHPadding: 12
    property int uiControlRadius: 10
    property int uiCardRadius: 14
    property color uiWindowBgColor: "#F6F8FB"
    property color uiPanelSoftColor: "#F8FAFC"
    property color uiCardColor: "#FFFFFF"
    property color uiBorderColor: "#D8E0EA"
    property color uiTextColor: "#111827"
    property color uiMutedTextColor: "#64748B"
    property color uiFocusBlue: "#7FA6D8"
    // Low-saturation professional palette. Keep uiAccentGreen names for compatibility,
    // but visually the primary operation color is a soft engineering blue.
    property color uiAccentGreen: "#EAF2FC"
    property color uiAccentGreenHover: "#DFEBF9"
    property color uiAccentGreenPressed: "#D4E3F5"
    property color uiStrongBlue: "#DDEAF8"
    property color uiStrongBlueHover: "#D1E1F4"
    property color uiStrongBluePressed: "#C5D8EE"
    property color uiDangerRed: "#FCE7E4"
    property color uiDangerRedHover: "#F9D8D3"
    property color uiDangerRedPressed: "#F2C5BE"
    property color uiPrimaryBorder: "#AFC7E8"
    property color uiPrimaryBorderHover: "#9BBBE2"
    property color uiStrongBorder: "#8FAFDB"
    property color uiStrongBorderHover: "#7FA4D5"
    property color uiDangerBorder: "#D36B62"
    property color uiDangerBorderHover: "#C95E55"
    property color uiNeutralFill: "#FFFFFF"
    property color uiNeutralFillHover: "#F4F7FB"
    property color uiNeutralFillPressed: "#EEF3F8"

    function buttonRoleForText(buttonText) {
        var s = String(buttonText || "")
        if (s.indexOf("删除") >= 0 || s.indexOf("清空") >= 0 || s.indexOf("清除") >= 0) {
            return "danger"
        }
        if (s.indexOf("求解") >= 0 || s.indexOf("开始") >= 0) {
            return "strongPrimary"
        }
        if (s.indexOf("生成") >= 0 || s.indexOf("添加") >= 0
                || s.indexOf("保存") >= 0 || s.indexOf("打开") >= 0 || s.indexOf("更新") >= 0
                || s.indexOf("连接") >= 0 || s.indexOf("分配") >= 0 || s.indexOf("创建") >= 0) {
            return "primary"
        }
        if (s.indexOf("显示") >= 0 || s.indexOf("导出") >= 0 || s.indexOf("查询") >= 0
                || s.indexOf("适配") >= 0 || s.indexOf("放大") >= 0 || s.indexOf("缩小") >= 0) {
            return "neutral"
        }
        return "secondary"
    }

    function buttonFillColor(role, enabled, down, hovered) {
        if (!enabled) {
            return "#EEF2F7"
        }
        if (role === "strongPrimary") {
            return down ? uiStrongBluePressed : (hovered ? uiStrongBlueHover : uiStrongBlue)
        }
        if (role === "primary") {
            return down ? uiAccentGreenPressed : (hovered ? uiAccentGreenHover : uiAccentGreen)
        }
        if (role === "danger") {
            return down ? uiDangerRedPressed : (hovered ? uiDangerRedHover : uiDangerRed)
        }
        if (role === "neutral") {
            return down ? uiNeutralFillPressed : (hovered ? uiNeutralFillHover : uiNeutralFill)
        }
        return down ? "#EEF3F8" : (hovered ? "#F7F9FC" : "#FFFFFF")
    }

    function buttonBorderColor(role, enabled, hovered, activeFocus) {
        if (!enabled) {
            return "#D3DCE8"
        }
        if (activeFocus) {
            return uiFocusBlue
        }
        if (role === "strongPrimary") {
            return hovered ? uiStrongBorderHover : uiStrongBorder
        }
        if (role === "primary") {
            return hovered ? uiPrimaryBorderHover : uiPrimaryBorder
        }
        if (role === "danger") {
            return hovered ? uiDangerBorderHover : uiDangerBorder
        }
        if (role === "neutral") {
            return hovered ? "#C4D2E3" : "#D3DCE8"
        }
        return hovered ? "#C8D4E3" : uiBorderColor
    }

    function buttonTextColor(role, enabled) {
        if (!enabled) {
            return "#94A3B8"
        }
        if (role === "strongPrimary") {
            return "#244B78"
        }
        if (role === "primary") {
            return "#2F5E96"
        }
        if (role === "danger") {
            return "#873A34"
        }
        return "#243244"
    }

    component PanelResizeHandle: Item {
        // Drag resizing is intentionally disabled.
        // Side panels are controlled by visible capsule toggle handles instead.
        property bool resizeLeft: true
        width: 0
        visible: false
    }


    component WorkbenchButton: Item {
        id: control

        property string text: ""
        property string visualRole: ""
        property int leftPadding: root.uiButtonHPadding
        property int rightPadding: root.uiButtonHPadding
        property int topPadding: 6
        property int bottomPadding: 6
        property font font: Qt.font({ pixelSize: 12, bold: false })
        property bool hovered: buttonMouseArea.containsMouse
        property bool down: buttonMouseArea.pressed

        signal clicked()

        function effectiveRole() {
            return visualRole !== "" ? visualRole : root.buttonRoleForText(control.text)
        }

        implicitHeight: root.uiButtonHeight
        implicitWidth: Math.max(92, buttonLabel.implicitWidth + leftPadding + rightPadding)
        opacity: enabled ? 1.0 : 0.72
        activeFocusOnTab: true
        clip: true

        Rectangle {
            id: buttonBackground
            anchors.fill: parent
            radius: root.uiControlRadius
            antialiasing: true
            color: root.buttonFillColor(control.effectiveRole(), control.enabled, control.down, control.hovered)
            border.color: root.buttonBorderColor(control.effectiveRole(), control.enabled, control.hovered, control.activeFocus)
            border.width: 1.0
        }

        Text {
            id: buttonLabel
            anchors.fill: parent
            anchors.leftMargin: control.leftPadding
            anchors.rightMargin: control.rightPadding
            anchors.topMargin: control.topPadding
            anchors.bottomMargin: control.bottomPadding
            text: control.text
            color: root.buttonTextColor(control.effectiveRole(), control.enabled)
            font.pixelSize: control.font.pixelSize
            font.bold: control.font.bold || control.effectiveRole() === "primary" || control.effectiveRole() === "strongPrimary"
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        MouseArea {
            id: buttonMouseArea
            anchors.fill: parent
            hoverEnabled: true
            enabled: control.enabled
            cursorShape: Qt.PointingHandCursor
            onPressed: control.forceActiveFocus()
            onClicked: control.clicked()
        }

        Keys.onSpacePressed: if (control.enabled) control.clicked()
        Keys.onReturnPressed: if (control.enabled) control.clicked()
        Keys.onEnterPressed: if (control.enabled) control.clicked()
    }

    component WorkbenchTextArea: TextArea {
        id: control
        color: root.uiTextColor
        selectedTextColor: "#FFFFFF"
        selectionColor: "#8FB3DD"
        font.pixelSize: 12
        padding: 10
        wrapMode: TextEdit.Wrap
        background: Rectangle {
            radius: root.uiControlRadius
            color: control.readOnly ? root.uiPanelSoftColor : root.uiCardColor
            border.color: control.activeFocus ? root.uiFocusBlue : root.uiBorderColor
            border.width: 1.0
        }
    }

    component WorkbenchScrollTextArea: ScrollView {
        id: scrollControl
        property alias text: scrollTextArea.text
        property bool readOnly: true
        property int textPixelSize: 12
        clip: true
        ScrollBar.vertical.policy: ScrollBar.AsNeeded
        ScrollBar.horizontal.policy: ScrollBar.AsNeeded
        background: Rectangle {
            radius: root.uiControlRadius
            color: root.uiPanelSoftColor
            border.color: root.uiBorderColor
            border.width: 1.0
        }

        TextArea {
            id: scrollTextArea
            readOnly: scrollControl.readOnly
            color: root.uiTextColor
            selectedTextColor: "#FFFFFF"
            selectionColor: "#8FB3DD"
            font.pixelSize: scrollControl.textPixelSize
            padding: 10
            wrapMode: TextEdit.NoWrap
            selectByMouse: true
            background: Rectangle { color: "transparent" }
        }
    }

    component WorkbenchComboBox: ComboBox {
        id: control
        implicitHeight: root.uiButtonHeight
        font.pixelSize: 12

        // 统一修复下拉选择框文字颜色：
        // 选中 / 悬停 / 按下状态都使用浅色背景 + 深色文字，避免原生样式出现蓝底白字或文字被覆盖。
        palette.text: root.uiTextColor
        palette.buttonText: root.uiTextColor
        palette.windowText: root.uiTextColor
        palette.highlight: "#EAF2FB"
        palette.highlightedText: root.uiTextColor

        contentItem: Item {
            implicitWidth: comboDisplayText.implicitWidth + 40
            implicitHeight: root.uiButtonHeight

            Text {
                id: comboDisplayText
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 10
                anchors.rightMargin: 30
                text: control.displayText
                font: control.font
                color: control.enabled ? root.uiTextColor : "#94A3B8"
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
        }

        background: Rectangle {
            radius: root.uiControlRadius
            color: control.enabled ? root.uiCardColor : "#E5E7EB"
            border.color: control.activeFocus ? root.uiFocusBlue : (control.hovered ? "#C7D8EC" : root.uiBorderColor)
            border.width: 1.0
        }

        delegate: ItemDelegate {
            id: optionDelegate
            width: control.width
            height: 34
            highlighted: control.highlightedIndex === index
            hoverEnabled: true
            clip: true
            property bool optionSelected: control.currentIndex === index
            palette.text: root.uiTextColor
            palette.buttonText: root.uiTextColor
            palette.highlight: "#EAF2FB"
            palette.highlightedText: root.uiTextColor

            contentItem: Item {
                implicitWidth: optionText.implicitWidth + 20
                implicitHeight: optionDelegate.height

                Text {
                    id: optionText
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    text: modelData
                    font.pixelSize: 12
                    color: root.uiTextColor
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }
            }

            background: Rectangle {
                radius: 8
                color: (optionDelegate.highlighted || optionDelegate.optionSelected) ? "#EAF2FB" : (optionDelegate.hovered ? "#F5F8FC" : "transparent")
                border.color: (optionDelegate.highlighted || optionDelegate.optionSelected) ? "#C7D8EC" : "transparent"
                border.width: 1.0
            }
        }
        popup: Popup {
            y: control.height + 2
            width: control.width
            implicitHeight: Math.min(contentItem.implicitHeight + 2, 240)
            padding: 1
            background: Rectangle {
                radius: root.uiControlRadius
                color: root.uiCardColor
                border.color: root.uiBorderColor
                border.width: 1.0
            }
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: control.popup.visible ? control.delegateModel : null
                currentIndex: control.highlightedIndex
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            }
        }
    }

    component WorkbenchCheckBox: CheckBox {
        id: control
        spacing: 8
        font.pixelSize: 12
        opacity: enabled ? 1.0 : 0.72

        indicator: Rectangle {
            implicitWidth: 18
            implicitHeight: 18
            x: control.leftPadding
            y: Math.round((control.height - height) / 2)
            radius: 5
            color: control.checked ? root.uiAccentGreen : root.uiCardColor
            border.color: control.activeFocus ? root.uiFocusBlue : (control.checked ? root.uiAccentGreenPressed : (control.hovered ? "#C7D8EC" : root.uiBorderColor))
            border.width: 1.0

            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: root.uiCardColor
                font.pixelSize: 13
                font.bold: true
            }
        }

        contentItem: Text {
            text: control.text
            color: control.enabled ? "#334155" : "#94A3B8"
            font.pixelSize: control.font.pixelSize
            verticalAlignment: Text.AlignVCenter
            leftPadding: control.indicator.width + control.spacing
            elide: Text.ElideRight
        }
    }
    component DialogCheckOption: Item {
        id: control
        property string text: ""
        property string helperText: ""
        property bool checked: false
        property bool hovered: optionMouseArea.containsMouse
        property bool down: optionMouseArea.pressed
        signal toggled(bool checked)

        Layout.fillWidth: true
        implicitHeight: helperText === "" ? 38 : 52
        implicitWidth: 180
        activeFocusOnTab: true
        clip: true

        Rectangle {
            anchors.fill: parent
            radius: root.uiControlRadius
            antialiasing: true
            color: control.down ? "#EEF3F8" : (control.hovered ? "#F7FAFD" : "#FFFFFF")
            border.color: control.activeFocus ? root.uiFocusBlue : (control.checked ? root.uiPrimaryBorder : root.uiBorderColor)
            border.width: 1.0
        }

        Rectangle {
            id: optionIndicator
            width: 18
            height: 18
            radius: 5
            antialiasing: true
            anchors.left: parent.left
            anchors.leftMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            color: control.checked ? "#DDEAF8" : "#FFFFFF"
            border.color: control.checked ? root.uiStrongBorder : (control.hovered ? "#C4D2E3" : root.uiBorderColor)
            border.width: 1.0

            Text {
                anchors.centerIn: parent
                text: control.checked ? "✓" : ""
                color: "#244B78"
                font.pixelSize: 13
                font.bold: true
            }
        }

        Column {
            anchors.left: optionIndicator.right
            anchors.leftMargin: 10
            anchors.right: parent.right
            anchors.rightMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1

            Text {
                width: parent.width
                text: control.text
                color: control.enabled ? "#243244" : "#94A3B8"
                font.pixelSize: 12
                font.bold: control.checked
                elide: Text.ElideRight
            }

            Text {
                width: parent.width
                visible: control.helperText !== ""
                text: control.helperText
                color: "#64748B"
                font.pixelSize: 10
                elide: Text.ElideRight
            }
        }

        MouseArea {
            id: optionMouseArea
            anchors.fill: parent
            hoverEnabled: true
            enabled: control.enabled
            cursorShape: Qt.PointingHandCursor
            onPressed: control.forceActiveFocus()
            onClicked: {
                control.checked = !control.checked
                control.toggled(control.checked)
            }
        }

        Keys.onSpacePressed: {
            if (control.enabled) {
                control.checked = !control.checked
                control.toggled(control.checked)
            }
        }
        Keys.onReturnPressed: {
            if (control.enabled) {
                control.checked = !control.checked
                control.toggled(control.checked)
            }
        }
        Keys.onEnterPressed: {
            if (control.enabled) {
                control.checked = !control.checked
                control.toggled(control.checked)
            }
        }
    }

    component DialogSectionTitle: Text {
        color: "#172033"
        font.pixelSize: 14
        font.bold: true
        elide: Text.ElideRight
    }

    component DialogMetricRow: Rectangle {
        property string label: ""
        property string value: ""
        Layout.fillWidth: true
        Layout.preferredHeight: 36
        radius: root.uiControlRadius
        color: root.uiPanelSoftColor
        border.color: root.uiBorderColor
        border.width: 1.0

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            spacing: 8
            Text {
                text: parent.parent.label
                color: root.uiMutedTextColor
                font.pixelSize: 11
            }
            Text {
                Layout.fillWidth: true
                text: parent.parent.value
                textFormat: Text.RichText
                color: root.uiTextColor
                font.pixelSize: 12
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }
    }

    function modelPoints() {
        try {
            return JSON.parse(bridge.modelPointsJson)
        } catch (e) {
            return []
        }
    }

    function modelPointOptionsFromJson() {
        var rows = root.modelPoints()
        var options = []
        for (var i = 0; i < rows.length; i++) {
            var x = Number(rows[i].x)
            var y = Number(rows[i].y)
            options.push(String(rows[i].id) + " | x=" + x.toFixed(2) + " y=" + y.toFixed(2))
        }
        return options
    }

    function parsePointIdFromOption(optionText) {
        var raw = String(optionText || "")
        if (raw === "") {
            return ""
        }
        return raw.split("|")[0].trim()
    }

    function modelEdges() {
        try {
            return JSON.parse(bridge.modelEdgesJson)
        } catch (e) {
            return []
        }
    }

    function modelFaces() {
        try {
            return JSON.parse(bridge.modelFacesJson)
        } catch (e) {
            return []
        }
    }

    function faceMaterialRows() {
        try {
            return JSON.parse(bridge.faceMaterialJson)
        } catch (e) {
            return []
        }
    }

    function meshNodes() {
        try {
            return JSON.parse(bridge.meshNodesJson)
        } catch (e) {
            return []
        }
    }

    function meshElements() {
        try {
            return JSON.parse(bridge.meshElementsJson)
        } catch (e) {
            return []
        }
    }

    function boundaryConditions() {
        try {
            return JSON.parse(bridge.boundaryConditionsJson)
        } catch (e) {
            return []
        }
    }

    function boundaryConditionOptionsFromJson() {
        var rows = root.boundaryConditions()
        var options = []
        for (var i = 0; i < rows.length; i++) {
            var row = rows[i]
            var targetType = String(row.target_type || row.targetType || "")
            var targetId = String(row.target_id || row.targetId || "")
            var ux = row.ux_fixed === undefined ? row.uxFixed : row.ux_fixed
            var uy = row.uy_fixed === undefined ? row.uyFixed : row.uy_fixed
            options.push(String(row.id) + " | " + targetType + ":" + targetId + " | ux=" + (ux ? "1" : "0") + " uy=" + (uy ? "1" : "0"))
        }
        return options
    }

    function parseBoundaryConditionId(optionText) {
        var raw = String(optionText || "")
        if (raw === "") {
            return ""
        }
        return raw.split("|")[0].trim()
    }

    function loads() {
        try {
            return JSON.parse(bridge.loadsJson)
        } catch (e) {
            return []
        }
    }

    function resultNodeRows() {
        try {
            return JSON.parse(bridge.nodeRowsJson)
        } catch (e) {
            return []
        }
    }

    function resultElementRows() {
        try {
            return JSON.parse(bridge.elementRowsJson)
        } catch (e) {
            return []
        }
    }

    function deformationPlotData() {
        try {
            return JSON.parse(bridge.deformationPlotJson)
        } catch (e) {
            return {}
        }
    }

    function deformationPreviewData() {
        try {
            return JSON.parse(bridge.deformationPreviewJson)
        } catch (e) {
            return {}
        }
    }

    function displacementContourData() {
        try {
            return JSON.parse(bridge.displacementContourJson)
        } catch (e) {
            return {}
        }
    }

    function stressContourData() {
        try {
            return JSON.parse(bridge.stressContourJson)
        } catch (e) {
            return {}
        }
    }

    function stressContourExactData() {
        try {
            return JSON.parse(bridge.stressContourExactJson)
        } catch (e) {
            return {}
        }
    }

    function stressContourSmoothData() {
        try {
            return JSON.parse(bridge.stressContourSmoothJson)
        } catch (e) {
            return {}
        }
    }

    function contourImageCacheMap() {
        try {
            return JSON.parse(bridge.contourImageCacheJson)
        } catch (e) {
            return {}
        }
    }

    function fileUrlToLocalPath(fileUrl) {
        var text = fileUrl.toString()
        if (text.indexOf("file:///") === 0) {
            return decodeURIComponent(text.substring(8))
        }
        if (text.indexOf("file://") === 0) {
            return decodeURIComponent(text.substring(7))
        }
        return decodeURIComponent(text)
    }

    function localPathToFileUrl(path) {
        var text = String(path || "")
        if (text === "") {
            return ""
        }
        var normalized = text.replace(/\\/g, "/")
        if (normalized.indexOf("file:///") === 0) {
            return normalized
        }
        return "file:///" + normalized
    }

    function ensureProjectFileSuffix(path) {
        if (path.endsWith(".f2dw.json") || path.endsWith(".json")) {
            return path
        }
        return path + ".f2dw.json"
    }

    function saveCurrentProjectWithDialogFallback() {
        if (bridge.projectPath !== "") {
            bridge.saveCurrentProject(bridge.projectPath)
        } else {
            saveProjectDialog.open()
        }
    }

    function mouseXInWorkspace(item, mouseX, mouseY) {
        return item.mapToItem(mainWorkspaceRow, mouseX, mouseY).x
    }

    function availableWorkspaceWidth() {
        return Math.max(0, mainWorkspaceRow.width)
    }

    function clampPanelWidths() {
        var total = availableWorkspaceWidth()
        if (total <= 0) {
            return
        }
        var reserved = root.minCenterPanelWidth + root.splitterWidth * 2
        var maxSideTotal = Math.max(0, total - reserved)
        var left = Math.max(root.minLeftPanelWidth, Math.min(root.maxLeftPanelWidth, root.leftPanelWidth))
        var right = Math.max(root.minRightPanelWidth, Math.min(root.maxRightPanelWidth, root.rightPanelWidth))
        if (left + right > maxSideTotal) {
            var overflow = left + right - maxSideTotal
            if (right - root.minRightPanelWidth >= overflow) {
                right -= overflow
            } else {
                overflow -= right - root.minRightPanelWidth
                right = root.minRightPanelWidth
                left = Math.max(root.minLeftPanelWidth, left - overflow)
            }
        }
        root.leftPanelWidth= left
        root.rightPanelWidth= right
    }

    function clearViewportSelection() {
        selectedObjectType = "无"
        selectedObjectName = "未选择"
        selectedObjectDescription = "请在视口中点击点、边或闭合面。"
    }

    function clearBridgeSelectionIfNeeded() {
        bridge.clearSelection()
    }

    function clearSelection() {
        root.clearViewportSelection()
        root.clearBridgeSelectionIfNeeded()
        root.repaintViewport()
    }

    function shortSelectionTypeText() {
        return bridge.selectedGeometryType === "" ? "无" : bridge.selectedGeometryType
    }

    function shortSelectionNameText() {
        return bridge.selectedGeometryId === "" ? "未选择" : bridge.selectedGeometryId
    }

    function shortSelectionDetailText() {
        if (bridge.selectedGeometryType === "") {
            return "点击视口中的点、边或闭合面进行选择"
        }
        if (bridge.selectedGeometryType === "point") {
            return "当前为几何点"
        }
        if (bridge.selectedGeometryType === "edge") {
            return "当前为几何边"
        }
        return "当前为闭合面"
    }

    function leftPanelResultStatusText() {
        return bridge.hasSolution ? "结果：已有" : "结果：暂无"
    }

    function bottomStatusPrimaryText() {
        return root.viewportHint === "" ? bridge.statusText : root.viewportHint
    }

    function bottomStatusSecondaryText() {
        return "选择：" + root.shortSelectionTypeText() + " / " + root.shortSelectionNameText()
    }

    function fakeProgressAt(elapsedMs, estimatedMs, holdProgress) {
        if (estimatedMs <= 0) {
            return holdProgress
        }

        var r = Math.min(elapsedMs / estimatedMs, 1.0)

        if (r < 0.2) {
            return 30.0 * (r / 0.2)
        } else if (r < 0.7) {
            return 30.0 + 40.0 * ((r - 0.2) / 0.5)
        } else {
            return 70.0 + (holdProgress - 70.0) * ((r - 0.7) / 0.3)
        }
    }

    function busyOverlayMessage() {
        if (bridge.isBusy
                && bridge.busyProgressMode === "fake_determinate"
                && (Date.now() - busyOverlay.busyStartMs) > bridge.busyEstimatedMs) {
            return bridge.busyMessage + " 仍在处理，请稍候..."
        }
        return bridge.busyMessage
    }

    function ensureContourCacheAvailable() {
        if (!bridge.hasSolution) {
            root.viewportHint = "请先求解。"
            return false
        }
        if (!bridge.contourCacheValid) {
            root.viewportHint = "云图缓存已失效，请重新求解。"
            return false
        }
        return true
    }

    function ensureContourImageCacheAvailable() {
        if (!root.ensureContourCacheAvailable()) {
            return false
        }
        if (!bridge.contourImageCacheValid) {
            root.viewportHint = "云图图片缓存已失效，请重新求解。"
            return false
        }
        return true
    }

    function contourVariantKey(showMesh, showDeformed) {
        return "grid_" + (showMesh ? "on" : "off") + "_deformed_" + (showDeformed ? "on" : "off")
    }

    function contourImagePath(groupKey, variantKey) {
        var imageMap = root.contourImageCacheMap()
        var group = imageMap[groupKey] || {}
        return group[variantKey] || ""
    }

    function deformationPreviewImageSource() {
        return root.localPathToFileUrl(
            root.contourImagePath("deformation_preview", root.contourVariantKey(true, true))
        )
    }

    function displacementContourImageSource() {
        return root.localPathToFileUrl(
            root.contourImagePath("displacement", root.contourVariantKey(displacementShowMeshBox.checked, displacementShowDeformedBox.checked))
        )
    }

    function stressContourImageSource() {
        var groupKey = stressContourModeCombo.currentIndex === 0 ? "stress_exact" : "stress_smooth"
        return root.localPathToFileUrl(
            root.contourImagePath(groupKey, root.contourVariantKey(stressShowMeshBox.checked, stressShowDeformedBox.checked))
        )
    }

    function syncSelectionSummary() {
        if (bridge.selectedGeometryType === "") {
            clearViewportSelection()
            return
        }
        selectedObjectType = bridge.selectedGeometryType
        selectedObjectName = bridge.selectedGeometryId
        if (bridge.selectedGeometryType === "point") {
            selectedObjectDescription = "当前选择的是几何点，可用于连边、移动或施加集中力/点约束。"
        } else if (bridge.selectedGeometryType === "edge") {
            selectedObjectDescription = "当前选择的是几何边，可用于施加边约束或均布载荷。"
        } else {
            selectedObjectDescription = "当前选择的是闭合面，可用于材料与厚度分配。"
        }
    }

    function repaintViewport() {
        if (viewport) {
            viewport.requestPaint()
        }
    }

    function clampViewportScale(value) {
        return Math.max(root.minViewportScale, Math.min(root.maxViewportScale, value))
    }

    function resetViewportTransform() {
        root.viewportScale = root.defaultViewportScale
        root.viewportOffsetX = 0.0
        root.viewportOffsetY = 0.0
        root.repaintViewport()
    }

    function zoomViewportBy(factor) {
        root.viewportScale = root.clampViewportScale(root.viewportScale * factor)
        root.repaintViewport()
    }

    function zoomViewportAt(factor, mouseX, mouseY) {
        root.updateViewportGeometryFrame()
        var before = root.screenToModel(mouseX, mouseY)
        root.viewportScale = root.clampViewportScale(root.viewportScale * factor)
        root.updateViewportGeometryFrame()
        var after = root.screenPoint(before)
        root.viewportOffsetX += mouseX - after.x
        root.viewportOffsetY += mouseY - after.y
        root.repaintViewport()
    }

    function viewportScaleText() {
        var percent = root.viewportScale / root.viewportScaleDisplayBase * 100.0
        if (percent < 0.1) {
            return percent.toFixed(2) + "%"
        }
        if (percent < 10.0) {
            return percent.toFixed(1) + "%"
        }
        if (percent < 1000.0) {
            return percent.toFixed(0) + "%"
        }
        return percent.toFixed(0) + "%"
    }

    function switchMode(modeName) {
        currentMode = modeName
        resultOverlayMode = modeName === "求解结果" ? resultOverlayMode : "none"
        viewportPanMode = false
        isPanningViewport = false
        isPanning = false
        bridge.clearSelection()
        clearViewportSelection()
        viewportHint = ""
        repaintViewport()
    }

    function faceRowsPreview() {
        var rows = modelFaces()
        var lines = []
        for (var i = 0; i < rows.length; i++) {
            lines.push(rows[i].id + " | " + rows[i].edge_ids.join(", "))
        }
        return lines.join("\n")
    }

    function pointMapFromRows(points) {
        var map = {}
        for (var i = 0; i < points.length; i++) {
            map[points[i].id] = points[i]
        }
        return map
    }

    function edgeById(edgeId) {
        var edges = modelEdges()
        for (var i = 0; i < edges.length; i++) {
            if (edges[i].id === edgeId) {
                return edges[i]
            }
        }
        return null
    }

    function materialFillColor(hexColor, alpha) {
        var color = String(hexColor || "#8FB7D8")
        if (color.length !== 7 || color.charAt(0) !== "#") {
            color = "#8FB7D8"
        }
        var r = parseInt(color.substring(1, 3), 16)
        var g = parseInt(color.substring(3, 5), 16)
        var b = parseInt(color.substring(5, 7), 16)
        return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")"
    }

    function scalarRange(values) {
        if (values.length === 0) {
            return { min: 0.0, max: 1.0 }
        }
        var minValue = values[0]
        var maxValue = values[0]
        for (var i = 1; i < values.length; i++) {
            minValue = Math.min(minValue, values[i])
            maxValue = Math.max(maxValue, values[i])
        }
        if (Math.abs(maxValue - minValue) <= 1e-12) {
            maxValue = minValue + 1.0
        }
        return { min: minValue, max: maxValue }
    }

    function contourPaletteStops() {
        return [
            { position: 0.00, color: "#000080" },
            { position: 0.15, color: "#0000FF" },
            { position: 0.30, color: "#00FFFF" },
            { position: 0.45, color: "#00FF00" },
            { position: 0.60, color: "#FFFF00" },
            { position: 0.75, color: "#FF9900" },
            { position: 1.00, color: "#FF0000" }
        ]
    }

    function hexToRgb(color) {
        var text = String(color || "#000000")
        if (text.length !== 7 || text.charAt(0) !== "#") {
            text = "#000000"
        }
        return {
            r: parseInt(text.substring(1, 3), 16),
            g: parseInt(text.substring(3, 5), 16),
            b: parseInt(text.substring(5, 7), 16)
        }
    }

    function interpolateColor(colorA, colorB, t, alpha) {
        t = Math.max(0.0, Math.min(1.0, t))
        var a = root.hexToRgb(colorA)
        var b = root.hexToRgb(colorB)
        var red = Math.round(a.r + (b.r - a.r) * t)
        var green = Math.round(a.g + (b.g - a.g) * t)
        var blue = Math.round(a.b + (b.b - a.b) * t)
        var aText = alpha === undefined ? 1.0 : alpha
        return "rgba(" + red + ", " + green + ", " + blue + ", " + aText + ")"
    }

    function contourColor(value, minValue, maxValue, alpha) {
        var ratio = 0.5
        if (Math.abs(maxValue - minValue) > 1.0e-12) {
            ratio = (value - minValue) / (maxValue - minValue)
        }
        ratio = Math.max(0.0, Math.min(1.0, ratio))
        var stops = root.contourPaletteStops()
        for (var i = 0; i < stops.length - 1; i++) {
            var left = stops[i]
            var right = stops[i + 1]
            if (ratio <= right.position || i === stops.length - 2) {
                var localSpan = Math.max(1.0e-12, right.position - left.position)
                var localT = (ratio - left.position) / localSpan
                return root.interpolateColor(left.color, right.color, localT, alpha)
            }
        }
        return root.interpolateColor(stops[stops.length - 1].color, stops[stops.length - 1].color, 1.0, alpha)
    }

    function trimTrailingZeros(text) {
        var s = String(text)
        if (s.indexOf('.') < 0) {
            return s
        }
        while (s.length > 0 && s.charAt(s.length - 1) === '0') {
            s = s.slice(0, -1)
        }
        if (s.length > 0 && s.charAt(s.length - 1) === '.') {
            s = s.slice(0, -1)
        }
        return s === '' || s === '-0' ? '0' : s
    }

    function exponentToSuperscript(exponent) {
        var raw = String(Math.trunc(Number(exponent || 0)))
        var output = ""
        for (var i = 0; i < raw.length; i++) {
            var ch = raw.charAt(i)
            if (ch === "-") output += "⁻"
            else if (ch === "+") output += "⁺"
            else if (ch === "0") output += "⁰"
            else if (ch === "1") output += "¹"
            else if (ch === "2") output += "²"
            else if (ch === "3") output += "³"
            else if (ch === "4") output += "⁴"
            else if (ch === "5") output += "⁵"
            else if (ch === "6") output += "⁶"
            else if (ch === "7") output += "⁷"
            else if (ch === "8") output += "⁸"
            else if (ch === "9") output += "⁹"
        }
        return output
    }

    function formatPowerNumber(value, digits) {
        var n = Number(value || 0.0)
        if (!isFinite(n) || Math.abs(n) < 1.0e-15) {
            return '0'
        }
        var exponent = Math.floor(Math.log(Math.abs(n)) / Math.LN10)
        var mantissa = n / Math.pow(10.0, exponent)
        return root.trimTrailingZeros(mantissa.toFixed(digits || 3)) + '×10' + root.exponentToSuperscript(exponent)
    }

    function formatPlainNumber(value) {
        var n = Number(value || 0.0)
        if (!isFinite(n) || Math.abs(n) < 1.0e-15) {
            return '0'
        }

        var absValue = Math.abs(n)
        if (absValue >= 0.001 && absValue < 1000000.0) {
            var decimals = absValue >= 1000.0 ? 2 : (absValue >= 1.0 ? 3 : 6)
            return root.trimTrailingZeros(n.toFixed(decimals))
        }

        return root.formatPowerNumber(n, 3)
    }

    function formatRichNumber(value) {
        return root.formatPlainNumber(value)
    }

    function formatScientific(value) {
        return root.formatRichNumber(value)
    }

    function formatCanvasNumber(value) {
        return root.formatPlainNumber(value)
    }

    function formatStressKPa(valuePa) {
        return root.formatRichNumber(Number(valuePa || 0.0) / 1000.0)
    }

    function displacementDisplayMagnitude() {
        var data = root.displacementContourData()
        var minValue = Math.abs(Number((data.min_displacement || 0.0)))
        var maxValue = Math.abs(Number((data.max_displacement || 0.0)))
        var value = Math.max(minValue, maxValue)
        if (!isFinite(value) || value <= 0.0) {
            var summaryValue = Math.abs(Number(((root.deformationPlotData().summary || {}).max_displacement || 0.0)))
            value = isFinite(summaryValue) ? summaryValue : 0.0
        }
        return value
    }

    function displacementDisplayScale() {
        var maxAbs = root.displacementDisplayMagnitude()
        if (maxAbs >= 1000.0) {
            return 0.001
        }
        if (maxAbs >= 1.0) {
            return 1.0
        }
        if (maxAbs >= 0.001) {
            return 1000.0
        }
        if (maxAbs >= 0.000001) {
            return 1000000.0
        }
        if (maxAbs >= 0.000000001) {
            return 1000000000.0
        }
        return 1.0
    }

    function displacementUnitLabel() {
        var maxAbs = root.displacementDisplayMagnitude()
        if (maxAbs >= 1000.0) {
            return "km"
        }
        if (maxAbs >= 1.0) {
            return "m"
        }
        if (maxAbs >= 0.001) {
            return "mm"
        }
        if (maxAbs >= 0.000001) {
            return "μm"
        }
        if (maxAbs >= 0.000000001) {
            return "nm"
        }
        return "m"
    }

    function formatDisplacement(value) {
        return root.formatRichNumber(Number(value || 0.0) * root.displacementDisplayScale())
    }

    function formatDisplacementWithUnit(value) {
        return root.formatDisplacement(value) + " " + root.displacementUnitLabel()
    }

    function contourScaleText(scaleValue) {
        var factor = Number(scaleValue || 1.0)
        if (!isFinite(factor) || factor <= 0.0) {
            factor = 1.0
        }
        return factor.toFixed(3)
    }

    function drawColorLegend(ctx, x, y, width, height, minValue, maxValue, title, unitLabel) {
        ctx.save()
        ctx.fillStyle = "#F8FAFC"
        ctx.fillRect(x, y, width, height)
        ctx.strokeStyle = "#CBD5E1"
        ctx.lineWidth = 1
        ctx.strokeRect(x, y, width, height)

        var barWidth = Math.max(18, width * 0.32)
        var barX = x + 18
        var barY = y + 28
        var barHeight = Math.max(40, height - 56)
        var sampleCount = 96
        for (var i = 0; i < sampleCount; i++) {
            var t0 = i / sampleCount
            var t1 = (i + 1) / sampleCount
            var yy = barY + (1.0 - t1) * barHeight
            var hh = Math.max(1.0, (t1 - t0) * barHeight + 1.0)
            var scalar = minValue + (maxValue - minValue) * t0
            ctx.fillStyle = root.contourColor(scalar, minValue, maxValue, 1.0)
            ctx.fillRect(barX, yy, barWidth, hh)
        }
        ctx.strokeStyle = "#334155"
        ctx.lineWidth = 1
        ctx.strokeRect(barX, barY, barWidth, barHeight)

        ctx.fillStyle = "#0F172A"
        ctx.font = "bold 13px 'Microsoft YaHei UI'"
        ctx.fillText(title, x + 18, y + 16)
        if (unitLabel !== "") {
            ctx.fillStyle = "#64748B"
            ctx.font = "12px 'Microsoft YaHei UI'"
            ctx.fillText(unitLabel, x + 18, y + height - 10)
        }

        var tickCount = 7
        ctx.font = "12px 'Consolas'"
        ctx.fillStyle = "#334155"
        ctx.strokeStyle = "#64748B"
        for (var tick = 0; tick <= tickCount; tick++) {
            var ratio = tick / tickCount
            var ty = barY + (1.0 - ratio) * barHeight
            var value = minValue + (maxValue - minValue) * ratio
            ctx.beginPath()
            ctx.moveTo(barX + barWidth, ty)
            ctx.lineTo(barX + barWidth + 8, ty)
            ctx.stroke()
            ctx.fillText(root.formatCanvasNumber(value), barX + barWidth + 12, ty + 4)
        }
        ctx.restore()
    }

    function drawContourDialogBackground(ctx, width, height) {
        ctx.save()
        ctx.fillStyle = "#E2E8F0"
        ctx.fillRect(0, 0, width, height)
        ctx.fillStyle = "#F8FAFC"
        ctx.fillRect(12, 12, width - 24, height - 24)
        ctx.strokeStyle = "#CBD5E1"
        ctx.lineWidth = 1
        ctx.strokeRect(12, 12, width - 24, height - 24)
        ctx.restore()
    }

    function geometryBoundsFromPoints(points) {
        if (!points || points.length === 0) {
            return { minX: 0.0, minY: 0.0, maxX: 1.0, maxY: 1.0 }
        }
        var minX = points[0].x
        var minY = points[0].y
        var maxX = points[0].x
        var maxY = points[0].y
        for (var i = 1; i < points.length; i++) {
            minX = Math.min(minX, points[i].x)
            minY = Math.min(minY, points[i].y)
            maxX = Math.max(maxX, points[i].x)
            maxY = Math.max(maxY, points[i].y)
        }
        return { minX: minX, minY: minY, maxX: maxX, maxY: maxY }
    }

    function canvasTransformForPoints(points, width, height, padding) {
        var bounds = geometryBoundsFromPoints(points)
        var spanX = Math.max(bounds.maxX - bounds.minX, 1.0)
        var spanY = Math.max(bounds.maxY - bounds.minY, 1.0)
        var drawWidth = Math.max(width - padding * 2, 1.0)
        var drawHeight = Math.max(height - padding * 2, 1.0)
        var scale = Math.min(drawWidth / spanX, drawHeight / spanY)
        return {
            bounds: bounds,
            scale: scale,
            offsetX: padding + (drawWidth - spanX * scale) / 2 - bounds.minX * scale,
            offsetY: padding + (drawHeight - spanY * scale) / 2 + bounds.maxY * scale
        }
    }

    function canvasPoint(transform, point) {
        return {
            x: transform.offsetX + point.x * transform.scale,
            y: transform.offsetY - point.y * transform.scale
        }
    }

    function faceMaterialColor(faceId) {
        var rows = faceMaterialRows()
        for (var i = 0; i < rows.length; i++) {
            if (String(rows[i].face_id) === String(faceId) && rows[i].material_color) {
                return rows[i].material_color
            }
        }
        return bridge.activePartMaterialColor === "" ? "#8FB7D8" : bridge.activePartMaterialColor
    }

    function faceScreenPolygon(faceRow, pointMap) {
        if (!faceRow || !faceRow.point_ids || faceRow.point_ids.length < 3) {
            return []
        }
        var polygon = []
        for (var i = 0; i < faceRow.point_ids.length; i++) {
            if (pointMap[faceRow.point_ids[i]]) {
                polygon.push(pointMap[faceRow.point_ids[i]])
            }
        }
        return polygon
    }

    function orderedFacePolygon(faceRow, pointMap) {
        return faceScreenPolygon(faceRow, pointMap)
    }

    function polygonArea(polygon) {
        if (!polygon || polygon.length < 3) {
            return 0
        }
        var area = 0
        for (var i = 0; i < polygon.length; i++) {
            var next = polygon[(i + 1) % polygon.length]
            area += polygon[i].x * next.y - next.x * polygon[i].y
        }
        return Math.abs(area) * 0.5
    }

    function pointInPolygon(x, y, polygon) {
        var inside = false
        for (var i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            var xi = polygon[i].x
            var yi = polygon[i].y
            var xj = polygon[j].x
            var yj = polygon[j].y
            var intersect = ((yi > y) !== (yj > y))
                    && (x < (xj - xi) * (y - yi) / Math.max(1.0e-9, yj - yi) + xi)
            if (intersect) {
                inside = !inside
            }
        }
        return inside
    }

    function distancePointToSegment(px, py, ax, ay, bx, by) {
        var dx = bx - ax
        var dy = by - ay
        var lengthSquared = dx * dx + dy * dy
        if (lengthSquared <= 1.0e-9) {
            var ddx = px - ax
            var ddy = py - ay
            return Math.sqrt(ddx * ddx + ddy * ddy)
        }
        var t = ((px - ax) * dx + (py - ay) * dy) / lengthSquared
        t = Math.max(0.0, Math.min(1.0, t))
        var cx = ax + t * dx
        var cy = ay + t * dy
        var ex = px - cx
        var ey = py - cy
        return Math.sqrt(ex * ex + ey * ey)
    }

    function updateViewportGeometryFrame() {
        var points = modelPoints()
        var minX = 0.0
        var minY = 0.0
        var maxX = 1.0
        var maxY = 1.0
        if (points.length > 0) {
            minX = points[0].x
            minY = points[0].y
            maxX = points[0].x
            maxY = points[0].y
            for (var i = 1; i < points.length; i++) {
                minX = Math.min(minX, points[i].x)
                minY = Math.min(minY, points[i].y)
                maxX = Math.max(maxX, points[i].x)
                maxY = Math.max(maxY, points[i].y)
            }
        }
        var modelW = Math.max(1.0, maxX - minX)
        var modelH = Math.max(1.0, maxY - minY)
        var maxDrawW = viewport.width * 0.68
        var maxDrawH = viewport.height * 0.62
        var drawScale = Math.min(maxDrawW / modelW, maxDrawH / modelH) * root.viewportScale
        // 旧缩放体系中 viewportLegacyScaleBase 对应的最小绘制尺度是 48。
        // 当前 UI 把旧 35% 显示为 100%，但绘制尺寸仍按旧物理基准缩放，
        // 因此新 100% 的最小绘制尺度为 48 * 0.35 = 16.8。
        drawScale = Math.max(48.0 * (root.viewportScale / root.viewportLegacyScaleBase), drawScale)
        root.sketchDrawScale = drawScale
        root.lastModelBoundsW = modelW * drawScale
        root.lastModelBoundsH = modelH * drawScale
        root.lastModelBoundsX = (viewport.width - root.lastModelBoundsW) / 2 + root.viewportOffsetX
        root.lastModelBoundsY = (viewport.height - root.lastModelBoundsH) / 2 + root.viewportOffsetY
        root.sketchOriginX = root.lastModelBoundsX - minX * drawScale
        root.sketchOriginY = root.lastModelBoundsY + maxY * drawScale
    }

    function screenPoint(pointRow) {
        return {
            x: root.sketchOriginX + pointRow.x * root.sketchDrawScale,
            y: root.sketchOriginY - pointRow.y * root.sketchDrawScale
        }
    }

    function screenPointMap() {
        var map = {}
        var points = modelPoints()
        for (var i = 0; i < points.length; i++) {
            map[points[i].id] = root.screenPoint(points[i])
        }
        return map
    }

    function screenToModel(mouseX, mouseY) {
        return {
            x: (mouseX - root.sketchOriginX) / Math.max(root.sketchDrawScale, 1.0e-9),
            y: (root.sketchOriginY - mouseY) / Math.max(root.sketchDrawScale, 1.0e-9)
        }
    }

    function findNearestPointAt(mouseX, mouseY) {
        var points = modelPoints()
        var map = screenPointMap()
        var bestId = ""
        var bestDistance = 1.0e9
        for (var i = 0; i < points.length; i++) {
            var p = map[points[i].id]
            if (!p) {
                continue
            }
            var dx = mouseX - p.x
            var dy = mouseY - p.y
            var distance = Math.sqrt(dx * dx + dy * dy)
            if (distance < 11 && distance < bestDistance) {
                bestDistance = distance
                bestId = points[i].id
            }
        }
        return bestId
    }

    function findNearestEdgeAt(mouseX, mouseY) {
        var edges = modelEdges()
        var map = screenPointMap()
        var bestId = ""
        var bestDistance = 1.0e9
        for (var i = 0; i < edges.length; i++) {
            var a = map[edges[i].start_point_id]
            var b = map[edges[i].end_point_id]
            if (!a || !b) {
                continue
            }
            var distance = distancePointToSegment(mouseX, mouseY, a.x, a.y, b.x, b.y)
            if (distance < 10 && distance < bestDistance) {
                bestDistance = distance
                bestId = edges[i].id
            }
        }
        return bestId
    }

    function findFaceAt(mouseX, mouseY) {
        var faces = modelFaces()
        var pointMap = screenPointMap()
        var bestId = ""
        var bestArea = 1.0e18
        for (var i = faces.length - 1; i >= 0; i--) {
            var polygon = faceScreenPolygon(faces[i], pointMap)
            if (polygon.length >= 3 && pointInPolygon(mouseX, mouseY, polygon)) {
                var area = polygonArea(polygon)
                if (area < bestArea) {
                    bestArea = area
                    bestId = faces[i].id
                }
            }
        }
        return bestId
    }

    function clearViewportCanvas(ctx) {
        ctx.setTransform(1, 0, 0, 1, 0, 0)
        ctx.clearRect(0, 0, viewport.width, viewport.height)
    }

    function drawViewportBackground(ctx) {
        ctx.save()
        ctx.fillStyle = "#E4EBF3"
        ctx.fillRect(0, 0, viewport.width, viewport.height)
        ctx.restore()
    }

    function drawBaseGrid(ctx) {
        ctx.save()
        ctx.strokeStyle = "#D6DFEA"
        ctx.lineWidth = 1
        var grid = 32
        for (var gx = 0; gx <= viewport.width; gx += grid) {
            ctx.beginPath()
            ctx.moveTo(gx, 0)
            ctx.lineTo(gx, viewport.height)
            ctx.stroke()
        }
        for (var gy = 0; gy <= viewport.height; gy += grid) {
            ctx.beginPath()
            ctx.moveTo(0, gy)
            ctx.lineTo(viewport.width, gy)
            ctx.stroke()
        }
        ctx.restore()
    }

    function drawModelGeometry(ctx) {
        root.updateViewportGeometryFrame()
        var points = modelPoints()
        var edges = modelEdges()
        var faces = modelFaces()
        var pointMap = screenPointMap()

        for (var fi = 0; fi < faces.length; fi++) {
            var polygon = faceScreenPolygon(faces[fi], pointMap)
            if (polygon.length < 3) {
                continue
            }
            ctx.save()
            ctx.beginPath()
            for (var fp = 0; fp < polygon.length; fp++) {
                if (fp === 0) {
                    ctx.moveTo(polygon[fp].x, polygon[fp].y)
                } else {
                    ctx.lineTo(polygon[fp].x, polygon[fp].y)
                }
            }
            ctx.closePath()
            ctx.fillStyle = materialFillColor(faceMaterialColor(faces[fi].id), 0.22)
            ctx.fill()
            ctx.restore()
        }

        ctx.save()
        ctx.strokeStyle = "#475569"
        ctx.lineWidth = 2
        for (var ei = 0; ei < edges.length; ei++) {
            var a = pointMap[edges[ei].start_point_id]
            var b = pointMap[edges[ei].end_point_id]
            if (!a || !b) {
                continue
            }
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.stroke()
        }
        ctx.restore()

        ctx.save()
        for (var pi = 0; pi < points.length; pi++) {
            var p = pointMap[points[pi].id]
            if (!p) {
                continue
            }
            ctx.beginPath()
            ctx.arc(p.x, p.y, 5, 0, Math.PI * 2)
            ctx.fillStyle = "#FFFFFF"
            ctx.fill()
            ctx.strokeStyle = "#3F6FA8"
            ctx.lineWidth = 2
            ctx.stroke()
            ctx.fillStyle = "#1F2937"
            ctx.font = "12px 'Microsoft YaHei UI'"
            ctx.fillText(points[pi].id, p.x + 8, p.y - 8)
        }
        ctx.restore()
    }

    function drawMeshLayer(ctx) {
        if (!bridge.hasMesh) {
            return
        }
        var nodeMap = {}
        var nodes = meshNodes()
        var elements = meshElements()
        for (var i = 0; i < nodes.length; i++) {
            nodeMap[nodes[i].id] = screenPoint(nodes[i])
        }
        ctx.save()
        ctx.strokeStyle = "#0F766E"
        ctx.lineWidth = 1.1
        for (var j = 0; j < elements.length; j++) {
            var ids = elements[j].node_ids
            if (!nodeMap[ids[0]] || !nodeMap[ids[1]] || !nodeMap[ids[2]]) {
                continue
            }
            ctx.beginPath()
            ctx.moveTo(nodeMap[ids[0]].x, nodeMap[ids[0]].y)
            ctx.lineTo(nodeMap[ids[1]].x, nodeMap[ids[1]].y)
            ctx.lineTo(nodeMap[ids[2]].x, nodeMap[ids[2]].y)
            ctx.closePath()
            ctx.stroke()
        }
        ctx.restore()
    }

    function drawBoundaryLayer(ctx) {
        var pointMap = screenPointMap()
        var rows = boundaryConditions()
        ctx.save()
        ctx.strokeStyle = "#984646"
        ctx.fillStyle = "#984646"
        ctx.lineWidth = 3
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].target_type === "geometry_point" && pointMap[rows[i].target_id]) {
                var p = pointMap[rows[i].target_id]
                ctx.beginPath()
                ctx.arc(p.x, p.y, 8, 0, Math.PI * 2)
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(p.x - 8, p.y - 8)
                ctx.lineTo(p.x + 8, p.y + 8)
                ctx.moveTo(p.x - 8, p.y + 8)
                ctx.lineTo(p.x + 8, p.y - 8)
                ctx.stroke()
            } else if (rows[i].target_type === "geometry_edge") {
                var edge = edgeById(rows[i].target_id)
                if (!edge || !pointMap[edge.start_point_id] || !pointMap[edge.end_point_id]) {
                    continue
                }
                ctx.beginPath()
                ctx.moveTo(pointMap[edge.start_point_id].x, pointMap[edge.start_point_id].y)
                ctx.lineTo(pointMap[edge.end_point_id].x, pointMap[edge.end_point_id].y)
                ctx.stroke()
            }
        }
        ctx.restore()
    }

    function drawArrowToTarget(ctx, targetX, targetY, vectorX, vectorY, length) {
        var magnitude = Math.sqrt(vectorX * vectorX + vectorY * vectorY)
        var dirX = 0.0
        var dirY = 1.0
        if (magnitude > 1.0e-9) {
            dirX = vectorX / magnitude
            dirY = -vectorY / magnitude
        }
        var tailX = targetX - dirX * length
        var tailY = targetY - dirY * length
        ctx.beginPath()
        ctx.moveTo(tailX, tailY)
        ctx.lineTo(targetX, targetY)
        ctx.stroke()

        var normalX = -dirY
        var normalY = dirX
        var arrowSize = 10
        ctx.beginPath()
        ctx.moveTo(targetX, targetY)
        ctx.lineTo(
            targetX - dirX * arrowSize + normalX * arrowSize * 0.55,
            targetY - dirY * arrowSize + normalY * arrowSize * 0.55
        )
        ctx.lineTo(
            targetX - dirX * arrowSize - normalX * arrowSize * 0.55,
            targetY - dirY * arrowSize - normalY * arrowSize * 0.55
        )
        ctx.closePath()
        ctx.fill()
    }

    function pointAlongSegment(startPoint, endPoint, t) {
        return {
            x: startPoint.x + (endPoint.x - startPoint.x) * t,
            y: startPoint.y + (endPoint.y - startPoint.y) * t
        }
    }

    function drawDistributedLoadOnEdgeSegment(ctx, startPoint, endPoint, qx, qy, startT, endT) {
        var segStart = pointAlongSegment(startPoint, endPoint, startT)
        var segEnd = pointAlongSegment(startPoint, endPoint, endT)
        ctx.beginPath()
        ctx.moveTo(segStart.x, segStart.y)
        ctx.lineTo(segEnd.x, segEnd.y)
        ctx.stroke()
        for (var i = 0; i < 4; i++) {
            var t = (i + 0.5) / 4.0
            var headX = segStart.x + (segEnd.x - segStart.x) * t
            var headY = segStart.y + (segEnd.y - segStart.y) * t
            root.drawArrowToTarget(ctx, headX, headY, qx, qy, 28)
        }
    }

    function drawDistributedLoadOnEdge(ctx, startPoint, endPoint, qx, qy) {
        drawDistributedLoadOnEdgeSegment(ctx, startPoint, endPoint, qx, qy, 0.0, 1.0)
    }

    function barycentricPoint(a, b, c, r, s) {
        var wa = 1.0 - r - s
        var wb = r
        var wc = s
        return {
            x: a.x * wa + b.x * wb + c.x * wc,
            y: a.y * wa + b.y * wb + c.y * wc,
            value: wa * a.value + wb * b.value + wc * c.value
        }
    }

    function fillTrianglePatch(ctx, p1, p2, p3, minValue, maxValue) {
        var avg = (p1.value + p2.value + p3.value) / 3.0
        ctx.beginPath()
        ctx.moveTo(p1.x, p1.y)
        ctx.lineTo(p2.x, p2.y)
        ctx.lineTo(p3.x, p3.y)
        ctx.closePath()
        ctx.fillStyle = contourColor(avg, minValue, maxValue, 0.88)
        ctx.fill()
    }

    function drawInterpolatedTriangleContour(ctx, a, b, c, minValue, maxValue, subdivisions) {
        var n = Math.max(2, subdivisions)
        for (var r = 0; r < n; r++) {
            for (var s = 0; s < n - r; s++) {
                var p0 = barycentricPoint(a, b, c, r / n, s / n)
                var p1 = barycentricPoint(a, b, c, (r + 1) / n, s / n)
                var p2 = barycentricPoint(a, b, c, r / n, (s + 1) / n)
                fillTrianglePatch(ctx, p0, p1, p2, minValue, maxValue)
                if (s < n - r - 1) {
                    var p3 = barycentricPoint(a, b, c, (r + 1) / n, (s + 1) / n)
                    fillTrianglePatch(ctx, p1, p3, p2, minValue, maxValue)
                }
            }
        }
    }

    function drawResultLayer(ctx) {
        if (!bridge.hasSolution || resultOverlayMode === "none") {
            return
        }
        if (!bridge.hasMesh) {
            return
        }
        var nodeMap = {}
        var nodes = meshNodes()
        var elements = meshElements()
        var resultNodes = resultNodeRows()
        var resultElements = resultElementRows()
        var resultNodeMap = {}
        var resultElementMap = {}
        for (var i = 0; i < resultNodes.length; i++) {
            resultNodeMap[resultNodes[i].node_id] = resultNodes[i]
        }
        for (var j = 0; j < resultElements.length; j++) {
            resultElementMap[resultElements[j].element_id] = resultElements[j]
        }
        for (var n = 0; n < nodes.length; n++) {
            nodeMap[nodes[n].id] = screenPoint(nodes[n])
        }

        if (resultOverlayMode === "vonMises") {
            var values = []
            for (var e = 0; e < resultElements.length; e++) {
                values.push(resultElements[e].von_mises)
            }
            var range = scalarRange(values)
            ctx.save()
            for (var k = 0; k < elements.length; k++) {
                var ids = elements[k].node_ids
                var row = resultElementMap[elements[k].id]
                if (!row || !nodeMap[ids[0]] || !nodeMap[ids[1]] || !nodeMap[ids[2]]) {
                    continue
                }
                ctx.beginPath()
                ctx.moveTo(nodeMap[ids[0]].x, nodeMap[ids[0]].y)
                ctx.lineTo(nodeMap[ids[1]].x, nodeMap[ids[1]].y)
                ctx.lineTo(nodeMap[ids[2]].x, nodeMap[ids[2]].y)
                ctx.closePath()
                ctx.fillStyle = contourColor(row.von_mises, range.min, range.max, 0.45)
                ctx.fill()
            }
            ctx.restore()
            return
        }

        ctx.save()
        ctx.strokeStyle = "#7C3AED"
        ctx.lineWidth = 1.2
        var scaleFactor = 250.0
        for (var m = 0; m < elements.length; m++) {
            var nodeIds = elements[m].node_ids
            var aRow = resultNodeMap[nodeIds[0]]
            var bRow = resultNodeMap[nodeIds[1]]
            var cRow = resultNodeMap[nodeIds[2]]
            if (!aRow || !bRow || !cRow) {
                continue
            }
            var a = screenPoint({ x: aRow.x + aRow.ux * scaleFactor, y: aRow.y + aRow.uy * scaleFactor })
            var b = screenPoint({ x: bRow.x + bRow.ux * scaleFactor, y: bRow.y + bRow.uy * scaleFactor })
            var c = screenPoint({ x: cRow.x + cRow.ux * scaleFactor, y: cRow.y + cRow.uy * scaleFactor })
            ctx.beginPath()
            ctx.moveTo(a.x, a.y)
            ctx.lineTo(b.x, b.y)
            ctx.lineTo(c.x, c.y)
            ctx.closePath()
            ctx.stroke()
        }
        ctx.restore()
    }

    function drawQueryPointLayer(ctx) {
        if (!hasQueryMarker) {
            return
        }
        var p = screenPoint({ x: queryMarkerX, y: queryMarkerY })
        ctx.save()
        ctx.strokeStyle = "#F59E0B"
        ctx.fillStyle = "#F59E0B"
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(p.x, p.y, 6, 0, Math.PI * 2)
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2)
        ctx.fill()
        ctx.restore()
    }

    function drawLoadLayer(ctx) {
        var pointMap = screenPointMap()
        var rows = loads()
        ctx.save()
        ctx.strokeStyle = "#D97706"
        ctx.fillStyle = "#D97706"
        ctx.lineWidth = 3
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].target_type === "geometry_point" && pointMap[rows[i].target_id]) {
                var p = pointMap[rows[i].target_id]
                root.drawArrowToTarget(ctx, p.x, p.y, rows[i].qx, rows[i].qy, 35)
            } else if (rows[i].target_type === "geometry_edge") {
                var edge = edgeById(rows[i].target_id)
                if (!edge || !pointMap[edge.start_point_id] || !pointMap[edge.end_point_id]) {
                    continue
                }
                root.drawDistributedLoadOnEdgeSegment(
                    ctx,
                    pointMap[edge.start_point_id],
                    pointMap[edge.end_point_id],
                    rows[i].qx,
                    rows[i].qy,
                    rows[i].start_t,
                    rows[i].end_t
                )
            }
        }
        ctx.restore()
    }

    function drawSelectionLayer(ctx) {
        var pointMap = screenPointMap()
        ctx.save()
        if (bridge.selectedGeometryType === "face" && bridge.selectedFaceId !== "") {
            var faces = modelFaces()
            for (var i = 0; i < faces.length; i++) {
                if (faces[i].id !== bridge.selectedFaceId) {
                    continue
                }
                var polygon = faceScreenPolygon(faces[i], pointMap)
                if (polygon.length < 3) {
                    continue
                }
                ctx.beginPath()
                for (var fp = 0; fp < polygon.length; fp++) {
                    if (fp === 0) {
                        ctx.moveTo(polygon[fp].x, polygon[fp].y)
                    } else {
                        ctx.lineTo(polygon[fp].x, polygon[fp].y)
                    }
                }
                ctx.closePath()
                ctx.fillStyle = "rgba(37, 99, 235, 0.22)"
                ctx.strokeStyle = "#4F7FB8"
                ctx.lineWidth = 2.4
                ctx.fill()
                ctx.stroke()
            }
        } else if (bridge.selectedGeometryType === "edge" && bridge.selectedGeometryId !== "") {
            var edge = edgeById(bridge.selectedGeometryId)
            if (edge && pointMap[edge.start_point_id] && pointMap[edge.end_point_id]) {
                ctx.strokeStyle = "#4F7FB8"
                ctx.lineWidth = 4
                ctx.beginPath()
                ctx.moveTo(pointMap[edge.start_point_id].x, pointMap[edge.start_point_id].y)
                ctx.lineTo(pointMap[edge.end_point_id].x, pointMap[edge.end_point_id].y)
                ctx.stroke()
            }
        } else if (bridge.selectedGeometryType === "point" && bridge.selectedGeometryId !== "") {
            var point = pointMap[bridge.selectedGeometryId]
            if (point) {
                ctx.beginPath()
                ctx.arc(point.x, point.y, 7, 0, Math.PI * 2)
                ctx.fillStyle = "#F59E0B"
                ctx.fill()
                ctx.strokeStyle = "#3F6FA8"
                ctx.lineWidth = 2
                ctx.stroke()
            }
        }
        ctx.restore()
    }

    function handleModelingClick(mouseX, mouseY) {
        if (root.viewportPanMode) {
            return
        }
        var pointId = findNearestPointAt(mouseX, mouseY)
        var edgeId = findNearestEdgeAt(mouseX, mouseY)
        var faceId = findFaceAt(mouseX, mouseY)
        var modelPos = screenToModel(mouseX, mouseY)

        if (bridge.partEditTool === "添加节点") {
            bridge.addModelPointFromViewport(modelPos.x, modelPos.y)
            viewportHint = "已新增点。"
            repaintViewport()
            return
        }

        if (bridge.partEditTool === "连接边") {
            if (pointId === "") {
                bridge.clearSelection()
                viewportHint = "已清除未完成连边起点。"
            } else if (bridge.edgeStartPointId === "") {
                bridge.selectGeometryPoint(pointId)
                bridge.startEdgeFromSelectedPoint()
                viewportHint = "已记录起点，请点击第二个点完成连边。"
            } else {
                var connectOk = bridge.connectEdgeToPoint(pointId)
                if (connectOk) {
                    bridge.selectGeometryPoint(pointId)
                    viewportHint = "已完成连边。"
                } else {
                    viewportHint = bridge.statusText
                }
            }
            repaintViewport()
            return
        }

        if (bridge.partEditTool === "删除") {
            if (pointId !== "") {
                bridge.selectGeometryPoint(pointId)
                bridge.deleteSelectedSketchEntity()
                viewportHint = "已删除点。"
            } else if (edgeId !== "") {
                bridge.selectGeometryEdge(edgeId)
                bridge.deleteSelectedSketchEntity()
                viewportHint = "已删除边。"
            } else {
                bridge.clearSelection()
                viewportHint = "未命中可删除对象。"
            }
            repaintViewport()
            return
        }

        if (pointId !== "") {
            bridge.selectGeometryPoint(pointId)
            viewportHint = "已选择点。"
        } else if (edgeId !== "") {
            bridge.selectGeometryEdge(edgeId)
            viewportHint = "已选择边。"
        } else if (faceId !== "") {
            bridge.selectGeometryFace(faceId)
            viewportHint = "已选择闭合面。"
        } else {
            bridge.clearSelection()
            viewportHint = "已清空选择。"
        }
        repaintViewport()
    }

    function setModelingTool(toolName) {
        if (toolName === "移动视图") {
            root.viewportPanMode = true
            root.isPanningViewport = false
            root.isPanning = false
            bridge.clearSelection()
            viewportHint = "移动视图：拖动中央视口以平移。"
            repaintViewport()
            return
        }
        root.viewportPanMode = false
        root.isPanningViewport = false
        root.isPanning = false
        bridge.setModelTool(toolName)
        repaintViewport()
    }

    function handleTargetSelectionClick(mouseX, mouseY) {
        if (bridge.edgeLoadSegmentSelectionMode) {
            var selectionEdgeId = findNearestEdgeAt(mouseX, mouseY)
            if (selectionEdgeId === "") {
                viewportHint = "请选择当前边上的一点作为局部载荷区间端点。"
                repaintViewport()
                return
            }
            var modelPos = screenToModel(mouseX, mouseY)
            bridge.captureEdgeLoadSegmentSelectionPoint(selectionEdgeId, modelPos.x, modelPos.y)
            viewportHint = bridge.edgeLoadSegmentSelectionMode
                    ? "已记录一个端点，请继续在同一条边上选择另一个端点。"
                    : "局部载荷区间设置完成。"
            repaintViewport()
            return
        }
        var pointId = findNearestPointAt(mouseX, mouseY)
        var edgeId = findNearestEdgeAt(mouseX, mouseY)
        if (pointId !== "") {
            bridge.selectGeometryPoint(pointId)
            viewportHint = "当前目标已切换为几何点。"
        } else if (edgeId !== "") {
            bridge.selectGeometryEdge(edgeId)
            viewportHint = "当前目标已切换为几何边。"
        } else {
            bridge.clearSelection()
            viewportHint = "面不能作为约束或载荷目标。"
        }
        repaintViewport()
    }

    function handleResultQueryClick(mouseX, mouseY) {
        var modelPos = screenToModel(mouseX, mouseY)
        queryMarkerX = modelPos.x
        queryMarkerY = modelPos.y
        hasQueryMarker = true
        bridge.queryResultAtPoint(modelPos.x, modelPos.y)
        viewportHint = "已按点击位置查询结果。"
        repaintViewport()
    }

    function handleViewportClick(mouseX, mouseY) {
        // Always refresh the model-to-screen frame before hit testing or
        // converting a click to model coordinates. This avoids stale
        // coordinates after side-panel width/layout changes.
        updateViewportGeometryFrame()

        if (currentMode === "建模与材料") {
            handleModelingClick(mouseX, mouseY)
            return
        }
        if (currentMode === "约束与载荷") {
            handleTargetSelectionClick(mouseX, mouseY)
            return
        }
        if (currentMode === "求解结果" && bridge.hasSolution) {
            handleResultQueryClick(mouseX, mouseY)
            return
        }
        var pointId = findNearestPointAt(mouseX, mouseY)
        var edgeId = findNearestEdgeAt(mouseX, mouseY)
        var faceId = findFaceAt(mouseX, mouseY)
        if (pointId !== "") {
            bridge.selectGeometryPoint(pointId)
        } else if (edgeId !== "") {
            bridge.selectGeometryEdge(edgeId)
        } else if (faceId !== "") {
            bridge.selectGeometryFace(faceId)
        } else {
            bridge.clearSelection()
        }
        repaintViewport()
    }

    function handleViewportSelection(mouseX, mouseY) {
        handleViewportClick(mouseX, mouseY)
    }

    function startPointDragIfNeeded(mouseX, mouseY) {
        updateViewportGeometryFrame()
        if (currentMode === "建模与材料" && bridge.partEditTool === "移动节点") {
            var pointId = findNearestPointAt(mouseX, mouseY)
            if (pointId !== "") {
                bridge.selectGeometryPoint(pointId)
                isDraggingPoint = true
            }
        }
    }

    function onProjectChanged() {
        syncSelectionSummary()
        repaintViewport()
    }

    function onSketchChanged() {
        syncSelectionSummary()
        repaintViewport()
    }

    function onSketchMeshChanged() {
        repaintViewport()
    }

    function onResultChanged() {
        repaintViewport()
    }

    onWidthChanged: clampPanelWidths()
    Component.onCompleted: {
        clampPanelWidths()
        bridge.newProject()
        bridge.createEmptySketchForActivePart()
        root.setModelingTool("选择")
        repaintViewport()
    }

    Connections {
        target: bridge
        function onProjectChanged() { root.onProjectChanged() }
        function onSketchChanged() { root.onSketchChanged() }
        function onSketchMeshChanged() { root.onSketchMeshChanged() }
        function onResultChanged() { root.onResultChanged() }
        function onPartEditChanged() { root.onSketchChanged() }
    }

    FileDialog {
        id: openProjectDialog
        title: "打开工程"
        fileMode: FileDialog.OpenFile
        nameFilters: ["Fem2dWorkbench (*.f2dw.json *.json)"]
        onAccepted: {
            bridge.loadProject(root.fileUrlToLocalPath(selectedFile))
            root.resultOverlayMode = "none"
            root.hasQueryMarker = false
            root.repaintViewport()
        }
    }

    FileDialog {
        id: saveProjectDialog
        title: "保存工程"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Fem2dWorkbench (*.f2dw.json)"]
        onAccepted: bridge.saveCurrentProject(root.ensureProjectFileSuffix(root.fileUrlToLocalPath(selectedFile)))
    }

    FolderDialog {
        id: exportNodeResultsFolderDialog
        title: "选择节点结果导出目录"
        onAccepted: bridge.exportNodeResults(root.fileUrlToLocalPath(selectedFolder))
    }

    FolderDialog {
        id: exportElementResultsFolderDialog
        title: "选择单元结果导出目录"
        onAccepted: bridge.exportElementResults(root.fileUrlToLocalPath(selectedFolder))
    }

    FolderDialog {
        id: exportDisplacementContourFolderDialog
        title: "选择位移云图导出目录"
        onAccepted: bridge.exportDisplacementContourImages(root.fileUrlToLocalPath(selectedFolder))
    }

    FolderDialog {
        id: exportStressContourFolderDialog
        title: "选择应力云图导出目录"
        onAccepted: bridge.exportStressContourImages(root.fileUrlToLocalPath(selectedFolder))
    }

    FolderDialog {
        id: exportAllResultsFolderDialog
        title: "选择全部结果导出目录"
        onAccepted: bridge.exportAllResults(root.fileUrlToLocalPath(selectedFolder))
    }

    Dialog {
        id: materialEditorDialog
        title: "材料编辑器"
        modal: true
        parent: Overlay.overlay
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        width: Math.min(620, root.width - 80)
        height: Math.min(540, root.height - 80)
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        standardButtons: Dialog.Ok

        ScrollView {
            anchors.fill: parent
            anchors.margins: 16
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: Math.max(0, materialEditorDialog.width - 32)
                spacing: 10

                Label {
                    text: "当前材料"
                    color: "#1F2937"
                    font.pixelSize: 14
                    font.bold: true
                }

                WorkbenchTextArea {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 160
                    readOnly: true
                    text: bridge.materialRowsPreview
                    wrapMode: Text.WordWrap
                }

                WorkbenchComboBox {
                    id: materialEditCombo
                    Layout.fillWidth: true
                    model: bridge.materialOptions
                }

                FormField { id: materialNameField; Layout.fillWidth: true; label: "材料名称"; text: "new_material" }
                FormField {
                    id: materialEField
                    Layout.fillWidth: true
                    label: "弹性模量 (Pa)"
                    text: "210000000000"
                    suffix: "Pa"
                    placeholderText: "例如 210000000000（钢约 210 GPa）"
                }
                FormField { id: materialNuField; Layout.fillWidth: true; label: "泊松比"; text: "0.3" }
                FormField { id: materialUnitWeightField; Layout.fillWidth: true; label: "容重 (N/m³)"; text: "0.0" }
                FormField { id: materialColorField; Layout.fillWidth: true; label: "颜色"; text: "#8FB7D8" }

                Label {
                    Layout.fillWidth: true
                    text: "弹性模量当前按 Pa 录入；210 GPa 请填写 210000000000。"
                    color: "#64748B"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 12
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    WorkbenchButton {
                        text: "新增材料"
                        visualRole: "primary"
                        onClicked: bridge.addMaterial(
                            materialNameField.text,
                            Number(materialEField.text),
                            Number(materialNuField.text),
                            materialColorField.text,
                            Number(materialUnitWeightField.text)
                        )
                    }
                    WorkbenchButton {
                        text: "更新选中"
                        visualRole: "primary"
                        onClicked: bridge.updateMaterial(
                            root.parseMaterialIdFromOption(materialEditCombo.currentText),
                            materialNameField.text,
                            Number(materialEField.text),
                            Number(materialNuField.text),
                            materialColorField.text,
                            Number(materialUnitWeightField.text)
                        )
                    }
                    WorkbenchButton {
                        text: "删除选中"
                        visualRole: "danger"
                        onClicked: bridge.deleteMaterial(root.parseMaterialIdFromOption(materialEditCombo.currentText))
                    }
                }
            }
        }
    }

    Dialog {
        id: deformationPlotDialog
        title: ""
        modal: true
        parent: Overlay.overlay
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        width: Math.min(1040, root.width - 60)
        height: Math.min(720, root.height - 60)
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        background: Rectangle {
            radius: 18
            color: root.uiCardColor
            border.color: root.uiBorderColor
            border.width: 1.0
        }
        onOpened: {
            root.resultOverlayMode = "deformed"
            root.repaintViewport()
        }
        onClosed: {
            root.resultOverlayMode = "none"
            root.repaintViewport()
        }

        WorkbenchButton {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 12
            width: 36
            height: 32
            z: 100
            text: "×"
            visualRole: "neutral"
            leftPadding: 0
            rightPadding: 0
            font: Qt.font({ pixelSize: 16, bold: true })
            onClicked: deformationPlotDialog.close()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: "变形示意图"
                        color: root.uiTextColor
                        font.pixelSize: 16
                        font.bold: true
                    }
                    Label {
                        text: "带网格线的变形后轮廓"
                        color: root.uiMutedTextColor
                        font.pixelSize: 11
                    }
                }

            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: root.uiCardRadius
                color: root.uiPanelSoftColor
                border.color: root.uiBorderColor
                border.width: 1.0
                clip: true

                Image {
                    anchors.fill: parent
                    anchors.margins: 10
                    fillMode: Image.PreserveAspectFit
                    cache: false
                    source: root.deformationPreviewImageSource()
                }
            }
        }
    }

    Dialog {
        id: displacementContourDialog
        title: ""
        modal: true
        parent: Overlay.overlay
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        width: Math.min(1040, root.width - 60)
        height: Math.min(720, root.height - 60)
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        background: Rectangle {
            radius: 18
            color: root.uiCardColor
            border.color: root.uiBorderColor
            border.width: 1.0
        }
        onOpened: {}

        WorkbenchButton {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 12
            width: 36
            height: 32
            z: 100
            text: "×"
            visualRole: "neutral"
            leftPadding: 0
            rightPadding: 0
            font: Qt.font({ pixelSize: 16, bold: true })
            onClicked: displacementContourDialog.close()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: "位移云图"
                        color: root.uiTextColor
                        font.pixelSize: 16
                        font.bold: true
                    }
                    Label {
                        text: "位移幅值 |u| 彩色渐变云图（" + root.displacementUnitLabel() + "）"
                        color: root.uiMutedTextColor
                        font.pixelSize: 11
                    }
                }

            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: root.uiCardRadius
                    color: root.uiPanelSoftColor
                    border.color: root.uiBorderColor
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 8
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        source: root.displacementContourImageSource()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 280
                    Layout.fillHeight: true
                    radius: root.uiCardRadius
                    color: root.uiCardColor
                    border.color: root.uiBorderColor
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        DialogSectionTitle { text: "结果显示" }
                        DialogCheckOption {
                            id: displacementShowMeshBox
                            text: "显示网格线"
                            helperText: "叠加网格边线"
                            checked: false
                        }
                        DialogCheckOption {
                            id: displacementShowDeformedBox
                            text: "显示变形后轮廓"
                            helperText: "按当前显示选项切换缓存图像"
                            checked: false
                        }
                        WorkbenchButton {
                            Layout.fillWidth: true
                            text: "导出云图"
                            visualRole: "neutral"
                            onClicked: exportDisplacementContourFolderDialog.open()
                        }
                        DialogMetricRow {
                            label: "Min (" + root.displacementUnitLabel() + ")"
                            value: root.formatDisplacement(Number((root.displacementContourData().min_displacement || 0.0)))
                        }
                        DialogMetricRow {
                            label: "Max (" + root.displacementUnitLabel() + ")"
                            value: root.formatDisplacement(Number((root.displacementContourData().max_displacement || 0.0)))
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                radius: root.uiControlRadius
                color: root.uiPanelSoftColor
                border.color: root.uiBorderColor

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: "位移云图 | Min = " + root.formatDisplacementWithUnit(Number((root.displacementContourData().min_displacement || 0.0)))
                              + " | Max = " + root.formatDisplacementWithUnit(Number((root.displacementContourData().max_displacement || 0.0)))
                        textFormat: Text.RichText
                        color: "#475569"
                        elide: Text.ElideRight
                    }
                    Label {
                        text: "单位：" + root.displacementUnitLabel()
                        color: "#64748B"
                    }
                }
            }
        }
    }

    Dialog {
        id: stressContourDialog
        title: ""
        modal: true
        parent: Overlay.overlay
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        width: Math.min(1040, root.width - 60)
        height: Math.min(720, root.height - 60)
        x: Math.round((parent.width - width) / 2)
        y: Math.round((parent.height - height) / 2)
        background: Rectangle {
            radius: 18
            color: root.uiCardColor
            border.color: root.uiBorderColor
            border.width: 1.0
        }
        onOpened: {}

        WorkbenchButton {
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 12
            width: 36
            height: 32
            z: 100
            text: "×"
            visualRole: "neutral"
            leftPadding: 0
            rightPadding: 0
            font: Qt.font({ pixelSize: 16, bold: true })
            onClicked: stressContourDialog.close()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: "应力云图"
                        color: root.uiTextColor
                        font.pixelSize: 16
                        font.bold: true
                    }
                    Label {
                        text: "Von Mises 应力云图（kPa）"
                        color: root.uiMutedTextColor
                        font.pixelSize: 11
                    }
                }

            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: root.uiCardRadius
                    color: root.uiPanelSoftColor
                    border.color: root.uiBorderColor
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 8
                        fillMode: Image.PreserveAspectFit
                        cache: false
                        source: root.stressContourImageSource()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 300
                    Layout.fillHeight: true
                    radius: root.uiCardRadius
                    color: root.uiCardColor
                    border.color: root.uiBorderColor
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 10

                        DialogSectionTitle { text: "结果显示" }
                        WorkbenchComboBox {
                            id: stressContourModeCombo
                            Layout.fillWidth: true
                            model: ["精确模式（单元常值）", "平滑模式（节点平均）"]
                            currentIndex: 1
                        }
                        DialogCheckOption {
                            id: stressShowMeshBox
                            text: "显示网格线"
                            helperText: "叠加单元边界"
                            checked: false
                        }
                        DialogCheckOption {
                            id: stressShowDeformedBox
                            text: "显示变形后轮廓"
                            helperText: "按当前模式切换缓存图像"
                            checked: false
                        }
                        WorkbenchButton {
                            Layout.fillWidth: true
                            text: "导出云图"
                            visualRole: "neutral"
                            onClicked: exportStressContourFolderDialog.open()
                        }
                        DialogMetricRow {
                            label: "Min (kPa)"
                            value: root.formatStressKPa(stressContourModeCombo.currentIndex === 0
                                  ? Number((root.stressContourExactData().min_von_mises || 0.0))
                                  : Number((root.stressContourSmoothData().min_von_mises || 0.0)))
                        }
                        DialogMetricRow {
                            label: "Max (kPa)"
                            value: root.formatStressKPa(stressContourModeCombo.currentIndex === 0
                                  ? Number((root.stressContourExactData().max_von_mises || 0.0))
                                  : Number((root.stressContourSmoothData().max_von_mises || 0.0)))
                        }
                        Item { Layout.fillHeight: true }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 56
                radius: root.uiControlRadius
                color: root.uiPanelSoftColor
                border.color: root.uiBorderColor

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: stressContourModeCombo.currentIndex === 0
                              ? "应力云图 | 精确模式（单元常值） | Max = " + root.formatStressKPa(Number((root.stressContourExactData().max_von_mises || 0.0)))
                              : "应力云图 | 平滑模式（节点平均） | Max = " + root.formatStressKPa(Number((root.stressContourSmoothData().max_von_mises || 0.0)))
                        textFormat: Text.RichText
                        color: "#475569"
                        elide: Text.ElideRight
                    }
                    Label {
                        text: "单位：kPa"
                        color: "#64748B"
                    }
                }
            }
        }
    }

    function parseMaterialIdFromOption(optionText) {
        var text = String(optionText)
        var idx = text.indexOf("|")
        if (idx < 0) {
            return text.trim()
        }
        return text.substring(0, idx).trim()
    }

    function parseFaceIdFromOption(optionText) {
        var text = String(optionText)
        var idx = text.indexOf("|")
        if (idx < 0) {
            return text.trim()
        }
        return text.substring(0, idx).trim()
    }

    function faceOptionsFromJson() {
        var faces = modelFaces()
        var faceMaterials = faceMaterialRows()
        var materialMap = {}
        for (var i = 0; i < faceMaterials.length; i++) {
            var row = faceMaterials[i]
            materialMap[row.face_id] = row.material_name || "未指定"
        }

        var options = []
        for (var j = 0; j < faces.length; j++) {
            var face = faces[j]
            var edgeCount = face.edge_ids ? face.edge_ids.length : 0
            var materialName = materialMap[face.id] || "未指定"
            options.push(face.id + " | " + edgeCount + " 边 | " + materialName)
        }
        return options
    }

    function faceOptionIndexById(faceId) {
        if (faceId === "") {
            return faceOptionsFromJson().length > 0 ? 0 : -1
        }
        var options = faceOptionsFromJson()
        for (var i = 0; i < options.length; i++) {
            if (parseFaceIdFromOption(options[i]) === faceId) {
                return i
            }
        }
        return options.length > 0 ? 0 : -1
    }

    function currentFaceDisplayText() {
        if (bridge.selectedFaceId !== "") {
            return bridge.selectedFaceId
        }
        var faceId = parseFaceIdFromOption(faceTargetCombo.currentText)
        return faceId === "" ? "未选择" : faceId
    }

    Rectangle {
        anchors.fill: parent
        color: root.uiWindowBgColor

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                color: root.uiCardColor
                border.color: root.uiBorderColor

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 18
                    anchors.rightMargin: 18
                    spacing: 12

                    Label {
                        text: "Fem2dWorkbench"
                        font.pixelSize: 22
                        font.bold: true
                        color: "#0F172A"
                    }

                    Item { Layout.fillWidth: true }

                    WorkbenchButton {
                        Layout.preferredHeight: root.uiButtonHeight
                        leftPadding: root.uiButtonHPadding
                        rightPadding: root.uiButtonHPadding
                        font.pixelSize: 12
                        text: "新建工程"
                        enabled: !bridge.isBusy
                        onClicked: { bridge.newProject(); bridge.createEmptySketchForActivePart(); root.resultOverlayMode = "none"; root.hasQueryMarker = false }
                    }
                    WorkbenchButton {
                        Layout.preferredHeight: root.uiButtonHeight
                        leftPadding: root.uiButtonHPadding
                        rightPadding: root.uiButtonHPadding
                        font.pixelSize: 12
                        text: "打开工程"
                        enabled: !bridge.isBusy
                        onClicked: openProjectDialog.open()
                    }
                    WorkbenchButton {
                        Layout.preferredHeight: root.uiButtonHeight
                        leftPadding: root.uiButtonHPadding
                        rightPadding: root.uiButtonHPadding
                        font.pixelSize: 12
                        text: "保存工程"
                        enabled: !bridge.isBusy
                        onClicked: root.saveCurrentProjectWithDialogFallback()
                    }
                    WorkbenchButton {
                        Layout.preferredHeight: root.uiButtonHeight
                        leftPadding: root.uiButtonHPadding
                        rightPadding: root.uiButtonHPadding
                        font.pixelSize: 12
                        text: "另存为"
                        enabled: !bridge.isBusy
                        onClicked: saveProjectDialog.open()
                    }
                }
            }

            RowLayout {
                id: mainWorkspaceRow
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: root.uiPanelSoftColor
                    border.color: root.uiBorderColor

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 62
                            color: root.uiCardColor
                            border.color: root.uiBorderColor

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
                                Rectangle {
                                    id: floatingWorkflowBar
                                    Layout.preferredWidth: 650
                                    Layout.minimumWidth: 560
                                    Layout.maximumWidth: 760
                                    Layout.preferredHeight: 40
                                    radius: 18
                                    color: "#F8FBFF"
                                    border.color: "#C4D3E5"
                                    border.width: 1.0
                                    clip: true

                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 6
                                        anchors.rightMargin: 6
                                        anchors.topMargin: 5
                                        anchors.bottomMargin: 5
                                        spacing: 6

                                        Repeater {
                                            model: ["建模与材料", "网格生成", "约束与载荷", "求解结果"]
                                            delegate: Rectangle {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                radius: 15
                                                color: modelData === root.currentMode ? "#E8F1FF" : "#FFFFFF"
                                                border.color: modelData === root.currentMode ? "#86A9D8" : "#D4DEE9"
                                                border.width: 1.0
                                                clip: true

                                                RowLayout {
                                                    anchors.fill: parent
                                                    anchors.leftMargin: 6
                                                    anchors.rightMargin: 6
                                                    spacing: 5

                                                    Rectangle {
                                                        Layout.preferredWidth: 22
                                                        Layout.preferredHeight: 22
                                                        Layout.alignment: Qt.AlignVCenter
                                                        radius: 11
                                                        color: modelData === root.currentMode ? "#D5E5FA" : "#F1F5F9"
                                                        border.color: modelData === root.currentMode ? "#7FA2D0" : "#D3DCE8"
                                                        Text {
                                                            anchors.centerIn: parent
                                                            text: String(index + 1)
                                                            color: modelData === root.currentMode ? "#244B78" : "#64748B"
                                                            font.pixelSize: 12
                                                            font.bold: true
                                                        }
                                                    }

                                                    Text {
                                                        Layout.fillWidth: true
                                                        Layout.alignment: Qt.AlignVCenter
                                                        text: modelData
                                                        color: modelData === root.currentMode ? "#163B65" : "#334155"
                                                        font.pixelSize: 12
                                                        font.bold: modelData === root.currentMode
                                                        horizontalAlignment: Text.AlignLeft
                                                        verticalAlignment: Text.AlignVCenter
                                                        elide: Text.ElideRight
                                                    }
                                                }

                                                MouseArea {
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: root.switchMode(modelData)
                                                }
                                            }
                                        }
                                    }
                                }
                                Item { Layout.fillWidth: true }
                                WorkbenchButton {
                                    Layout.preferredWidth: 64
                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                    leftPadding: 6
                                    rightPadding: 6
                                    font.pixelSize: 11
                                    text: "适配视图"
                                    onClicked: root.resetViewportTransform()
                                }
                                WorkbenchButton {
                                    Layout.preferredWidth: 48
                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                    leftPadding: 6
                                    rightPadding: 6
                                    font.pixelSize: 11
                                    text: "放大"
                                    onClicked: root.zoomViewportBy(1.15)
                                }
                                WorkbenchButton {
                                    Layout.preferredWidth: 48
                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                    leftPadding: 6
                                    rightPadding: 6
                                    font.pixelSize: 11
                                    text: "缩小"
                                    onClicked: root.zoomViewportBy(1.0 / 1.15)
                                }
                                WorkbenchButton {
                                    Layout.preferredWidth: 64
                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                    leftPadding: 6
                                    rightPadding: 6
                                    font.pixelSize: 11
                                    text: "移动视图"
                                    visualRole: root.viewportPanMode ? "strongPrimary" : "neutral"
                                    onClicked: root.setModelingTool("移动视图")
                                }
                                WorkbenchButton {
                                    Layout.preferredWidth: 64
                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                    leftPadding: 6
                                    rightPadding: 6
                                    font.pixelSize: 11
                                    text: "视图复位"
                                    onClicked: {
                                        root.viewportPanMode = false
                                        root.isPanningViewport = false
                                        root.isPanning = false
                                        root.resetViewportTransform()
                                    }
                                }
                            }
                        }

                        Canvas {
                            id: viewport
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            renderTarget: Canvas.FramebufferObject

                            onPaint: {
                                var ctx = getContext("2d")
                                root.clearViewportCanvas(ctx)
                                root.drawViewportBackground(ctx)
                                root.drawBaseGrid(ctx)
                                root.drawModelGeometry(ctx)
                                root.drawMeshLayer(ctx)
                                root.drawBoundaryLayer(ctx)
                                root.drawResultLayer(ctx)
                                root.drawQueryPointLayer(ctx)
                                root.drawLoadLayer(ctx)
                                root.drawSelectionLayer(ctx)
                            }

                            MouseArea {
                                anchors.fill: parent
                                acceptedButtons: Qt.LeftButton | Qt.RightButton
                                hoverEnabled: true
                                cursorShape: root.viewportPanMode
                                             ? (root.isPanningViewport ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
                                             : Qt.ArrowCursor

                                onWheel: function(wheel) {
                                    if (root.viewportPanMode && (wheel.modifiers & Qt.ControlModifier)) {
                                        var factor = wheel.angleDelta.y > 0 ? 1.10 : (1.0 / 1.10)
                                        root.zoomViewportAt(factor, wheel.x, wheel.y)
                                        wheel.accepted = true
                                    }
                                }

                                onPressed: function(mouse) {
                                    root.lastMouseX = mouse.x
                                    root.lastMouseY = mouse.y
                                    root.viewportPressX = mouse.x
                                    root.viewportPressY = mouse.y
                                    root.viewportClickCandidate = mouse.button === Qt.LeftButton

                                    if (root.viewportPanMode && mouse.button === Qt.LeftButton) {
                                        root.isPanningViewport = true
                                        root.isPanning = false
                                        root.viewportClickCandidate = false
                                        root.panStartMouseX = mouse.x
                                        root.panStartMouseY = mouse.y
                                        root.panStartOffsetX = root.viewportOffsetX
                                        root.panStartOffsetY = root.viewportOffsetY
                                        mouse.accepted = true
                                        return
                                    }

                                    if (mouse.button === Qt.RightButton) {
                                        root.isPanning = true
                                        root.viewportClickCandidate = false
                                    } else {
                                        root.startPointDragIfNeeded(mouse.x, mouse.y)
                                        if (root.isDraggingPoint) {
                                            root.viewportClickCandidate = false
                                        }
                                    }
                                }

                                onPositionChanged: function(mouse) {
                                    var dx = mouse.x - root.viewportPressX
                                    var dy = mouse.y - root.viewportPressY
                                    if (root.viewportClickCandidate && Math.sqrt(dx * dx + dy * dy) > root.clickMoveTolerance) {
                                        root.viewportClickCandidate = false
                                    }

                                    if (root.isPanningViewport) {
                                        root.viewportOffsetX = root.panStartOffsetX + (mouse.x - root.panStartMouseX)
                                        root.viewportOffsetY = root.panStartOffsetY + (mouse.y - root.panStartMouseY)
                                        root.repaintViewport()
                                        mouse.accepted = true
                                    } else if (root.isDraggingPoint) {
                                        root.updateViewportGeometryFrame()
                                        var modelPos = root.screenToModel(mouse.x, mouse.y)
                                        bridge.updateSelectedSketchPoint(modelPos.x, modelPos.y)
                                        root.repaintViewport()
                                    } else if (root.isPanning) {
                                        root.viewportOffsetX += mouse.x - root.lastMouseX
                                        root.viewportOffsetY += mouse.y - root.lastMouseY
                                        root.lastMouseX = mouse.x
                                        root.lastMouseY = mouse.y
                                        root.repaintViewport()
                                    }
                                }

                                onReleased: function(mouse) {
                                    if (root.isPanningViewport) {
                                        root.viewportClickCandidate = false
                                        root.isDraggingPoint = false
                                        root.isPanningViewport = false
                                        root.isPanning = false
                                        mouse.accepted = true
                                        return
                                    }
                                    if (root.viewportClickCandidate
                                            && mouse.button === Qt.LeftButton
                                            && !root.isDraggingPoint
                                            && !root.isPanning) {
                                        root.handleViewportClick(mouse.x, mouse.y)
                                    }

                                    root.viewportClickCandidate = false
                                    root.isDraggingPoint = false
                                    root.isPanningViewport = false
                                    root.isPanning = false
                                }

                                onCanceled: {
                                    root.viewportClickCandidate = false
                                    root.isDraggingPoint = false
                                    root.isPanningViewport = false
                                    root.isPanning = false
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 72
                            color: root.uiCardColor
                            border.color: root.uiBorderColor
                            clip: true

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 3

                                    Label {
                                        Layout.fillWidth: true
                                        text: "提示：" + root.bottomStatusPrimaryText()
                                        color: "#475569"
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: root.shortSelectionDetailText()
                                        color: "#64748B"
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 168
                                    Layout.preferredHeight: 44
                                    Layout.alignment: Qt.AlignVCenter
                                    radius: 14
                                    color: "#F8FBFF"
                                    border.color: "#D4DEE9"
                                    clip: true
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.topMargin: 6
                                        anchors.bottomMargin: 6
                                        spacing: 1
                                        Text { Layout.fillWidth: true; text: "当前选择"; color: "#64748B"; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text { Layout.fillWidth: true; text: root.shortSelectionTypeText() + " / " + root.shortSelectionNameText(); color: "#1F2937"; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight }
                                    }
                                }

                                Rectangle {
                                    Layout.preferredWidth: 168
                                    Layout.preferredHeight: 44
                                    Layout.alignment: Qt.AlignVCenter
                                    radius: 14
                                    color: "#F8FBFF"
                                    border.color: "#D4DEE9"
                                    clip: true
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: 10
                                        anchors.rightMargin: 10
                                        anchors.topMargin: 6
                                        anchors.bottomMargin: 6
                                        spacing: 1
                                        Text { Layout.fillWidth: true; text: "模型概览"; color: "#64748B"; font.pixelSize: 10; elide: Text.ElideRight }
                                        Text { Layout.fillWidth: true; text: "点 " + bridge.modelPointCount + " / 边 " + bridge.modelEdgeCount + " / 面 " + bridge.modelFaceCount; color: "#1F2937"; font.pixelSize: 12; font.bold: true; elide: Text.ElideRight }
                                    }
                                }

                                Label {
                                    Layout.alignment: Qt.AlignVCenter
                                    text: "缩放：" + root.viewportScaleText()
                                    color: "#64748B"
                                    font.pixelSize: 12
                                }
                            }
                        }
                    }
                }

                PanelResizeHandle {
                    id: rightPanelResizeHandle
                    Layout.fillHeight: true
                    resizeLeft: false
                }

                ScrollView {
                    id: rightPanelScroll
                    Layout.minimumWidth: root.rightPanelWidth
                    Layout.preferredWidth: root.rightPanelWidth
                    Layout.maximumWidth: root.rightPanelWidth
                    Layout.fillHeight: true
                    clip: true
                    focusPolicy: Qt.NoFocus
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Rectangle {
                        width: rightPanelScroll.availableWidth > 0 ? rightPanelScroll.availableWidth : root.rightPanelWidth
                        color: root.uiCardColor
                        border.color: root.uiBorderColor
                        implicitHeight: rightPanelColumn.implicitHeight + 32

                        ColumnLayout {
                            id: rightPanelColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 14
                            spacing: 14

                            Rectangle {
                                visible: root.currentMode === "建模与材料"
                                Layout.fillWidth: true
                                color: root.uiPanelSoftColor
                                border.color: root.uiBorderColor
                                radius: root.uiControlRadius
                                implicitHeight: modelingColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: modelingColumn
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Label { text: "建模工具"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 10

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6
                                            Repeater {
                                                model: ["选择", "删除"]
                                                delegate: WorkbenchButton {
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                                    leftPadding: root.uiButtonHPadding
                                                    rightPadding: root.uiButtonHPadding
                                                    font.pixelSize: 12
                                                    text: modelData
                                                    onClicked: root.setModelingTool(modelData)
                                                }
                                            }
                                        }

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6
                                            Repeater {
                                                model: ["添加节点", "移动节点", "连接边"]
                                                delegate: WorkbenchButton {
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: root.uiButtonCompactHeight
                                                    leftPadding: root.uiButtonHPadding
                                                    rightPadding: root.uiButtonHPadding
                                                    font.pixelSize: 12
                                                    text: modelData
                                                    onClicked: root.setModelingTool(modelData)
                                                }
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        FormField { id: pointXField; Layout.fillWidth: true; label: "点 X"; text: "0.0" }
                                        FormField { id: pointYField; Layout.fillWidth: true; label: "点 Y"; text: "0.0" }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.topMargin: 2
                                        Layout.preferredHeight: root.uiButtonHeight
                                        leftPadding: root.uiButtonHPadding
                                        rightPadding: root.uiButtonHPadding
                                        font.pixelSize: 12
                                        text: "按坐标添加点"
                                        onClicked: bridge.addModelPoint(Number(pointXField.text), Number(pointYField.text))
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: "起点 ID"; color: "#334155"; font.pixelSize: 11 }
                                            WorkbenchComboBox {
                                                id: edgeStartCombo
                                                Layout.fillWidth: true
                                                model: root.modelPointOptionsFromJson()
                                                currentIndex: count > 0 ? 0 : -1
                                                displayText: count > 0 ? currentText : "暂无节点"
                                            }
                                        }
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 4
                                            Label { text: "终点 ID"; color: "#334155"; font.pixelSize: 11 }
                                            WorkbenchComboBox {
                                                id: edgeEndCombo
                                                Layout.fillWidth: true
                                                model: root.modelPointOptionsFromJson()
                                                currentIndex: count > 1 ? 1 : (count > 0 ? 0 : -1)
                                                displayText: count > 0 ? currentText : "暂无节点"
                                            }
                                        }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.topMargin: 2
                                        Layout.preferredHeight: root.uiButtonHeight
                                        leftPadding: root.uiButtonHPadding
                                        rightPadding: root.uiButtonHPadding
                                        font.pixelSize: 12
                                        text: "连接边"
                                        onClicked: {
                                            var startId = root.parsePointIdFromOption(edgeStartCombo.currentText)
                                            var endId = root.parsePointIdFromOption(edgeEndCombo.currentText)
                                            if (startId === "" || endId === "") {
                                                viewportHint = "请先创建至少两个节点，并在下拉框中选择起点和终点。"
                                                return
                                            }
                                            if (startId === endId) {
                                                viewportHint = "起点和终点不能相同。"
                                                return
                                            }
                                            bridge.connectModelEdge(startId, endId)
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.topMargin: 2
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "生成闭合面"
                                            onClicked: bridge.buildModelFaces()
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "清空几何"
                                            onClicked: bridge.clearModelGeometry()
                                        }
                                    }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "几何列表"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Label { text: "点列表"; color: "#334155"; font.pixelSize: 12 }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 88; readOnly: true; text: bridge.sketchNodeRowsPreview }
                                    Label { text: "边列表"; color: "#334155"; font.pixelSize: 12 }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 88; readOnly: true; text: bridge.sketchEdgeRowsPreview }
                                    Label { text: "闭合面列表"; color: "#334155"; font.pixelSize: 12 }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 88; readOnly: true; text: root.faceRowsPreview() }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        implicitHeight: materialAssignColumn.implicitHeight + 26
                                        radius: root.uiCardRadius
                                        color: "#F9FBFF"
                                        border.color: root.uiPrimaryBorder
                                        border.width: 1.0
                                        clip: true

                                        ColumnLayout {
                                            id: materialAssignColumn
                                            anchors.fill: parent
                                            anchors.margins: 13
                                            spacing: 11

                                            Label { text: "材料分配"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                            Label { text: "目标闭合面"; color: "#334155"; font.pixelSize: 12 }
                                            WorkbenchComboBox {
                                                id: faceTargetCombo
                                                Layout.fillWidth: true
                                                model: root.faceOptionsFromJson()
                                                currentIndex: root.faceOptionIndexById(bridge.selectedFaceId)
                                                displayText: count > 0 ? currentText : "请先生成闭合面"
                                                onActivated: function(index) {
                                                    var faceId = root.parseFaceIdFromOption(faceTargetCombo.textAt(index))
                                                    if (faceId !== "") {
                                                        bridge.selectGeometryFace(faceId)
                                                        root.repaintViewport()
                                                    }
                                                }
                                            }
                                            Label { text: "选中材料"; color: "#334155"; font.pixelSize: 12 }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 8
                                                WorkbenchComboBox {
                                                    id: materialAssignCombo
                                                    Layout.fillWidth: true
                                                    Layout.preferredWidth: 1
                                                    model: bridge.materialOptions
                                                }
                                                WorkbenchButton {
                                                    Layout.fillWidth: true
                                                    Layout.preferredWidth: 1
                                                    Layout.preferredHeight: root.uiButtonHeight
                                                    leftPadding: root.uiButtonHPadding
                                                    rightPadding: root.uiButtonHPadding
                                                    font.pixelSize: 12
                                                    text: "打开材料编辑器"
                                                    onClicked: materialEditorDialog.open()
                                                }
                                            }
                                            FormField { id: thicknessAssignField; Layout.fillWidth: true; label: "厚度"; text: String(bridge.activePartThickness) }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.topMargin: 3
                                                spacing: 8
                                                WorkbenchButton {
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: 42
                                                    visualRole: "strongPrimary"
                                                    text: "应用到选中闭合面"
                                                    onClicked: {
                                                        var faceId = root.parseFaceIdFromOption(faceTargetCombo.currentText)
                                                        if (faceId === "") {
                                                            viewportHint = "请先生成并选择闭合面。"
                                                            return
                                                        }
                                                        bridge.selectGeometryFace(faceId)
                                                        bridge.assignMaterialToSelectedFace(
                                                            root.parseMaterialIdFromOption(materialAssignCombo.currentText),
                                                            Number(thicknessAssignField.text)
                                                        )
                                                        root.repaintViewport()
                                                    }
                                                }
                                                WorkbenchButton {
                                                    Layout.fillWidth: true
                                                    Layout.preferredHeight: 42
                                                    visualRole: "strongPrimary"
                                                    text: "应用到全部闭合面"
                                                    onClicked: bridge.assignMaterialToAllFaces(
                                                        root.parseMaterialIdFromOption(materialAssignCombo.currentText),
                                                        Number(thicknessAssignField.text)
                                                    )
                                                }
                                            }

                                            Label { text: "闭合面材料列表"; color: "#334155"; font.pixelSize: 12 }
                                            WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 96; readOnly: true; text: bridge.faceMaterialRowsPreview }
                                        }
                                    }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "网格生成"
                                Layout.fillWidth: true
                                color: root.uiPanelSoftColor
                                border.color: root.uiBorderColor
                                radius: root.uiControlRadius
                                implicitHeight: meshColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: meshColumn
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 12

                                    Label { text: "网格生成"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Label { text: "唯一正式网格器：Gmsh CST 三角网格"; color: "#334155"; wrapMode: Text.WordWrap }
                                    FormField { id: meshTargetSizeField; Layout.fillWidth: true; label: "target_size"; text: String(bridge.meshTargetSize > 0 ? bridge.meshTargetSize : 0.8) }
                                    FormField { id: meshMinAngleField; Layout.fillWidth: true; label: "min_angle"; text: String(bridge.meshMinAngle) }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.topMargin: 2
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "生成网格"
                                            enabled: !bridge.isBusy
                                            onClicked: bridge.generateMeshAsync(Number(meshTargetSizeField.text), Number(meshMinAngleField.text))
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "清除网格"
                                            enabled: !bridge.isBusy
                                            onClicked: bridge.clearMesh()
                                        }
                                    }
                                    Text { text: "网格后端状态：" + (bridge.currentMeshType === "none" ? "未生成" : bridge.currentMeshType); color: "#334155" }
                                    Text { text: "节点数：" + bridge.sketchMeshNodeCount; color: "#334155" }
                                    Text { text: "单元数：" + bridge.sketchMeshElementCount; color: "#334155" }
                                    Text { text: "面积误差 / 质量摘要"; color: "#334155" }
                                    WorkbenchTextArea { Layout.fillWidth: true; Layout.preferredHeight: 140; readOnly: true; text: bridge.meshQualitySummaryText === "" ? bridge.statusText : bridge.meshQualitySummaryText }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "约束与载荷"
                                Layout.fillWidth: true
                                color: root.uiPanelSoftColor
                                border.color: root.uiBorderColor
                                radius: root.uiControlRadius
                                implicitHeight: targetColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: targetColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "约束与载荷"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Text {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            wrapMode: Text.WordWrap
                                            text: bridge.selectedTargetType === "" ? "当前目标：未选择" : "当前目标：" + bridge.selectedTargetType + " | " + bridge.selectedTargetId
                                            color: "#334155"
                                        }
                                        WorkbenchCheckBox {
                                            id: gravityEnabledBox
                                            Layout.alignment: Qt.AlignVCenter
                                            text: "求解时考虑自重"
                                            checked: bridge.gravityEnabled
                                            onToggled: bridge.setGravityEnabled(checked)
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "重力方向：竖直向下"
                                        color: "#64748B"
                                        wrapMode: Text.WordWrap
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchCheckBox { id: uxFixedBox; Layout.fillWidth: true; text: "固定 Ux"; checked: true }
                                        WorkbenchCheckBox { id: uyFixedBox; Layout.fillWidth: true; text: "固定 Uy"; checked: true }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: root.uiButtonHeight
                                        text: "添加约束"
                                        visualRole: "primary"
                                        onClicked: bridge.addConstraintToSelectedTarget(uxFixedBox.checked, uyFixedBox.checked)
                                    }

                                    Label { text: "删除约束"; color: "#334155"; font.pixelSize: 12 }
                                    WorkbenchComboBox {
                                        id: deleteBcCombo
                                        Layout.fillWidth: true
                                        model: root.boundaryConditionOptionsFromJson()
                                        currentIndex: count > 0 ? 0 : -1
                                        displayText: count > 0 ? currentText : "暂无约束"
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "删除约束"
                                            onClicked: {
                                                var bcId = root.parseBoundaryConditionId(deleteBcCombo.currentText)
                                                if (bcId !== "") {
                                                    bridge.deleteBoundaryCondition(bcId)
                                                }
                                            }
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "清空约束"
                                            onClicked: bridge.clearConstraints()
                                        }
                                    }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 104; readOnly: true; text: bridge.boundaryConditionRowsPreview }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "载荷"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        FormField { id: loadXField; Layout.fillWidth: true; label: "Fx / qx"; text: "0.0" }
                                        FormField { id: loadYField; Layout.fillWidth: true; label: "Fy / qy"; text: "-1000.0" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        FormField { id: loadStartTField; Layout.fillWidth: true; label: "start_t"; text: String(bridge.edgeLoadStartT) }
                                        FormField { id: loadEndTField; Layout.fillWidth: true; label: "end_t"; text: String(bridge.edgeLoadEndT) }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            text: "整边模式"
                                            onClicked: {
                                                bridge.useFullEdgeLoadRange()
                                                loadStartTField.text = String(bridge.edgeLoadStartT)
                                                loadEndTField.text = String(bridge.edgeLoadEndT)
                                            }
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            text: "应用区间参数"
                                            onClicked: bridge.setSelectedEdgeLoadSegmentRange(
                                                Number(loadStartTField.text),
                                                Number(loadEndTField.text)
                                            )
                                        }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: root.uiButtonHeight
                                        text: bridge.edgeLoadSegmentSelectionMode ? "取消区间设置" : "设置局部载荷区间"
                                        onClicked: {
                                            if (bridge.edgeLoadSegmentSelectionMode) {
                                                bridge.cancelEdgeLoadSegmentSelection()
                                            } else {
                                                bridge.beginEdgeLoadSegmentSelection()
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            text: "添加集中力"
                                            onClicked: bridge.addLoadToSelectedTarget("nodal_concentrated", Number(loadXField.text), Number(loadYField.text))
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            text: bridge.hasEdgeLoadSegment ? "添加局部均布载荷" : "添加均布载荷"
                                            onClicked: bridge.addLoadToSelectedTarget("edge_uniform", Number(loadXField.text), Number(loadYField.text))
                                        }
                                    }
                                    FormField { id: deleteLoadField; Layout.fillWidth: true; label: "删除载荷 ID"; text: "load_1" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "删除载荷"
                                            onClicked: bridge.deleteLoad(deleteLoadField.text)
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "清空载荷"
                                            onClicked: bridge.clearLoads()
                                        }
                                    }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 104; readOnly: true; text: bridge.loadRowsPreview }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "求解结果"
                                Layout.fillWidth: true
                                color: root.uiPanelSoftColor
                                border.color: root.uiBorderColor
                                radius: root.uiControlRadius
                                implicitHeight: resultColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: resultColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "求解结果"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: root.uiButtonHeight
                                        leftPadding: root.uiButtonHPadding
                                        rightPadding: root.uiButtonHPadding
                                        font.pixelSize: 12
                                        text: "求解当前模型"
                                        enabled: !bridge.isBusy
                                        onClicked: bridge.solveCurrentModelAsync()
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "求解状态：" + bridge.statusText
                                        color: "#334155"
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                    }
                                    Text { Layout.fillWidth: true; text: "最大位移：" + (bridge.maxDisplacement === "" ? "—" : bridge.maxDisplacement); color: "#334155"; elide: Text.ElideRight }
                                    Text { Layout.fillWidth: true; text: "最大 Von Mises：" + (bridge.maxVonMises === "" ? "—" : bridge.maxVonMises); color: "#334155"; elide: Text.ElideRight }
                                    Text { Layout.fillWidth: true; text: "Warning 数量：" + bridge.warningCount; color: "#334155"; elide: Text.ElideRight }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "云图缓存：" + (bridge.contourCacheValid ? "已生成" : "已失效，请重新求解")
                                        color: "#64748B"
                                        elide: Text.ElideRight
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "图片缓存：" + (bridge.contourImageCacheValid ? "已生成" : "已失效，请重新求解")
                                        color: "#64748B"
                                        elide: Text.ElideRight
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "显示变形示意图"
                                            onClicked: {
                                                if (!root.ensureContourImageCacheAvailable()) {
                                                    return
                                                }
                                                deformationPlotDialog.open()
                                            }
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "显示位移云图"
                                            onClicked: {
                                                if (!root.ensureContourImageCacheAvailable()) {
                                                    return
                                                }
                                                displacementContourDialog.open()
                                            }
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: root.uiButtonHPadding
                                            rightPadding: root.uiButtonHPadding
                                            font.pixelSize: 12
                                            text: "显示应力云图"
                                            onClicked: {
                                                if (!root.ensureContourImageCacheAvailable()) {
                                                    return
                                                }
                                                stressContourDialog.open()
                                            }
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        FormField { id: queryXField; Layout.fillWidth: true; label: "查询 X"; text: String(bridge.resultQueryX) }
                                        FormField { id: queryYField; Layout.fillWidth: true; label: "查询 Y"; text: String(bridge.resultQueryY) }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: root.uiButtonHeight
                                        text: "查询结果"
                                        onClicked: {
                                            root.queryMarkerX = Number(queryXField.text)
                                            root.queryMarkerY = Number(queryYField.text)
                                            root.hasQueryMarker = true
                                            bridge.queryResultAtPoint(Number(queryXField.text), Number(queryYField.text))
                                        }
                                    }
                                    WorkbenchScrollTextArea { Layout.fillWidth: true; Layout.preferredHeight: 150; readOnly: true; text: bridge.resultQueryText }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "导出"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: 8
                                            rightPadding: 8
                                            font.pixelSize: 11
                                            text: "导出节点结果"
                                            onClicked: exportNodeResultsFolderDialog.open()
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: 8
                                            rightPadding: 8
                                            font.pixelSize: 11
                                            text: "导出单元结果"
                                            onClicked: exportElementResultsFolderDialog.open()
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: 8
                                            rightPadding: 8
                                            font.pixelSize: 11
                                            text: "导出位移云图"
                                            visualRole: "neutral"
                                            onClicked: exportDisplacementContourFolderDialog.open()
                                        }
                                        WorkbenchButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: root.uiButtonHeight
                                            leftPadding: 8
                                            rightPadding: 8
                                            font.pixelSize: 11
                                            text: "导出应力云图"
                                            visualRole: "neutral"
                                            onClicked: exportStressContourFolderDialog.open()
                                        }
                                    }
                                    WorkbenchButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: root.uiButtonHeight
                                        leftPadding: root.uiButtonHPadding
                                        rightPadding: root.uiButtonHPadding
                                        font.pixelSize: 12
                                        text: "导出全部结果"
                                        visualRole: "primary"
                                        onClicked: exportAllResultsFolderDialog.open()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Rectangle {
        id: busyOverlay
        anchors.fill: parent
        visible: bridge.isBusy || busyOverlay.visualFinishActive
        color: "#66000000"
        z: 9999

        property real flowOffset: -0.4
        property real progressShineOffset: -0.35
        property double lastProgressTickMs: 0
        property real busyVisualProgress: 0
        property real busyTargetProgress: 0
        property double busyStartMs: 0
        property bool backendBusyWasActive: false
        property bool visualFinishActive: false
        property string displayTitle: bridge.busyTitle
        property string displayMessage: bridge.busyMessage
        property string displayStage: bridge.busyStage
        property string displayMode: bridge.busyProgressMode

        function clampProgress(value) {
            var numberValue = Number(value)
            if (!isFinite(numberValue)) {
                return 0
            }
            return Math.max(0, Math.min(100, numberValue))
        }

        function refreshDisplayTextFromBridge() {
            busyOverlay.displayTitle = bridge.busyTitle
            busyOverlay.displayMessage = root.busyOverlayMessage()
            busyOverlay.displayStage = bridge.busyStage
            busyOverlay.displayMode = bridge.busyProgressMode
        }

        function currentFakeTarget() {
            var elapsed = Date.now() - busyOverlay.busyStartMs
            return root.fakeProgressAt(
                elapsed,
                bridge.busyEstimatedMs,
                bridge.busyHoldProgress
            )
        }

        function currentTargetProgress() {
            if (busyOverlay.visualFinishActive) {
                return 100
            }

            var realTarget = busyOverlay.clampProgress(bridge.busyProgress)
            var mode = bridge.busyProgressMode

            if (mode === "fake_determinate") {
                return busyOverlay.clampProgress(Math.max(realTarget, busyOverlay.currentFakeTarget()))
            }

            if (mode === "determinate") {
                return realTarget
            }

            return busyOverlay.busyVisualProgress
        }

        function updateBusyVisualProgress() {
            if (bridge.isBusy) {
                busyOverlay.refreshDisplayTextFromBridge()
            }

            var now = Date.now()
            var dt = busyOverlay.lastProgressTickMs > 0 ? (now - busyOverlay.lastProgressTickMs) : 16
            busyOverlay.lastProgressTickMs = now
            dt = Math.max(8, Math.min(48, dt))

            var target = busyOverlay.currentTargetProgress()

            // 视觉进度只前进，不因为真实阶段回退或状态刷新而倒退。
            if (target < busyOverlay.busyVisualProgress) {
                target = busyOverlay.busyVisualProgress
            }

            busyOverlay.busyTargetProgress = target

            var diff = target - busyOverlay.busyVisualProgress
            if (diff > 0.01) {
                // 时间步长驱动的平滑追赶：比固定每帧跳值更丝滑，也能适应不同机器帧率。
                var baseSpeed = busyOverlay.visualFinishActive ? 42.0 : 13.0       // percent / second
                var catchupSpeed = Math.min(36.0, diff * 0.85)                    // percent / second
                var speed = baseSpeed + catchupSpeed
                var step = speed * dt / 1000.0

                // 限制单次最大跳变，避免真实进度粗跳时视觉进度跟着突变。
                var maxStep = busyOverlay.visualFinishActive ? 1.10 : 0.58
                step = Math.max(0.035, Math.min(step, maxStep))
                busyOverlay.busyVisualProgress = Math.min(busyOverlay.busyVisualProgress + step, target)
            }

            if (busyOverlay.visualFinishActive && busyOverlay.busyVisualProgress >= 99.8) {
                busyOverlay.busyVisualProgress = 100
                if (!busyFinishCloseTimer.running) {
                    busyFinishCloseTimer.start()
                }
            }
        }

        function startVisualBusy() {
            busyFinishCloseTimer.stop()
            busyOverlay.visualFinishActive = false
            busyOverlay.backendBusyWasActive = true
            busyOverlay.busyStartMs = Date.now()
            busyOverlay.lastProgressTickMs = 0
            busyOverlay.lastProgressTickMs = 0
            busyOverlay.busyVisualProgress = 0
            busyOverlay.busyTargetProgress = 0
            busyOverlay.refreshDisplayTextFromBridge()
        }

        function startVisualFinish() {
            // 后端任务已经完成，但前端遮罩先保留，让视觉进度平滑走到 100% 后再关闭。
            if (!busyOverlay.backendBusyWasActive) {
                return
            }

            busyOverlay.backendBusyWasActive = false
            busyOverlay.visualFinishActive = true
            busyOverlay.lastProgressTickMs = 0
            busyOverlay.displayMode = "fake_determinate"
            busyOverlay.displayMessage = busyOverlay.displayMessage === "" ? "完成" : "完成"
            busyOverlay.displayStage = "完成"
            busyOverlay.busyTargetProgress = 100

            if (busyOverlay.busyVisualProgress < 1) {
                busyOverlay.busyVisualProgress = 1
            }
        }

        function clearVisualBusy() {
            busyOverlay.visualFinishActive = false
            busyOverlay.backendBusyWasActive = false
            busyOverlay.lastProgressTickMs = 0
            busyOverlay.busyVisualProgress = 0
            busyOverlay.busyTargetProgress = 0
            busyOverlay.displayTitle = ""
            busyOverlay.displayMessage = ""
            busyOverlay.displayStage = ""
            busyOverlay.displayMode = "determinate"
        }

        NumberAnimation on flowOffset {
            running: busyOverlay.visible && busyOverlay.displayMode === "indeterminate"
            loops: Animation.Infinite
            from: -0.4
            to: 1.2
            duration: 1300
        }

        NumberAnimation on progressShineOffset {
            running: busyOverlay.visible && busyOverlay.displayMode !== "indeterminate"
            loops: Animation.Infinite
            from: -0.35
            to: 1.25
            duration: 1150
            easing.type: Easing.InOutSine
        }

        Timer {
            id: fakeProgressTimer
            interval: 16
            repeat: true
            running: busyOverlay.visible && busyOverlay.displayMode !== "indeterminate"
            onTriggered: busyOverlay.updateBusyVisualProgress()
        }

        Timer {
            id: busyFinishCloseTimer
            interval: 320
            repeat: false
            onTriggered: busyOverlay.clearVisualBusy()
        }

        Connections {
            target: bridge

            function onBusyStateChanged() {
                if (bridge.isBusy) {
                    if (!busyOverlay.backendBusyWasActive || busyOverlay.visualFinishActive) {
                        busyOverlay.startVisualBusy()
                    } else {
                        busyOverlay.refreshDisplayTextFromBridge()
                    }
                } else {
                    busyOverlay.startVisualFinish()
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            enabled: busyOverlay.visible
        }

        Rectangle {
            width: 420
            height: 180
            radius: 12
            anchors.centerIn: parent
            color: root.uiCardColor
            border.color: "#CBD5E1"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12

                Label {
                    text: busyOverlay.displayTitle
                    font.bold: true
                    font.pixelSize: 16
                    color: "#0F172A"
                }

                Label {
                    Layout.fillWidth: true
                    text: busyOverlay.displayMessage
                    wrapMode: Text.WordWrap
                    color: "#475569"
                }

                Rectangle {
                    id: determinateProgressTrack
                    Layout.fillWidth: true
                    Layout.preferredHeight: 12
                    visible: busyOverlay.displayMode !== "indeterminate"
                    radius: 6
                    color: "#E2E8F0"
                    clip: true

                    Rectangle {
                        id: determinateProgressFill
                        width: Math.max(parent.height, parent.width * busyOverlay.busyVisualProgress / 100.0)
                        height: parent.height
                        radius: 6
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#7FA6D8" }
                            GradientStop { position: 0.55; color: "#8FB3DD" }
                            GradientStop { position: 1.0; color: "#B8D0EA" }
                        }

                        Behavior on width {
                            NumberAnimation {
                                duration: 120
                                easing.type: Easing.OutCubic
                            }
                        }

                        Rectangle {
                            width: Math.max(46, determinateProgressTrack.width * 0.20)
                            height: parent.height * 1.8
                            y: -parent.height * 0.4
                            radius: parent.radius
                            x: busyOverlay.progressShineOffset * (determinateProgressFill.width + width) - width
                            rotation: 16
                            opacity: 0.62
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.00; color: Qt.rgba(1, 1, 1, 0.00) }
                                GradientStop { position: 0.45; color: Qt.rgba(1, 1, 1, 0.42) }
                                GradientStop { position: 0.55; color: Qt.rgba(1, 1, 1, 0.72) }
                                GradientStop { position: 1.00; color: Qt.rgba(1, 1, 1, 0.00) }
                            }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 12
                    visible: busyOverlay.displayMode === "indeterminate"
                    radius: 6
                    color: "#E2E8F0"
                    clip: true

                    Rectangle {
                        width: parent.width * 0.32
                        height: parent.height
                        radius: 6
                        x: busyOverlay.flowOffset * (parent.width + width) - width
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#D4E3F5" }
                            GradientStop { position: 0.5; color: "#8FB3DD" }
                            GradientStop { position: 1.0; color: "#EDF4FB" }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Label {
                        text: busyOverlay.displayStage
                        color: "#64748B"
                        font.pixelSize: 12
                    }
                    Item { Layout.fillWidth: true }
                    Label {
                        text: busyOverlay.displayMode === "indeterminate"
                              ? "处理中..."
                              : (Math.round(busyOverlay.busyVisualProgress) + "%")
                        color: "#0F172A"
                        font.pixelSize: 12
                    }
                }
            }
        }
    }


}
