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
    color: "#EEF3F8"

    property string currentMode: "建模与材料"
    property real viewportScale: 1.0
    property real viewportOffsetX: 0.0
    property real viewportOffsetY: 0.0
    property real lastMouseX: 0.0
    property real lastMouseY: 0.0
    property bool isPanning: false
    property bool isDraggingPoint: false
    property bool viewportClickCandidate: false
    property real viewportPressX: 0.0
    property real viewportPressY: 0.0
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
    property real rightPanelWidth: 380
    property bool leftPanelVisible: true
    property bool rightPanelVisible: true
    property real defaultLeftPanelWidth: 300
    property real defaultRightPanelWidth: 380
    property real minLeftPanelWidth: 240
    property real minRightPanelWidth: 320
    property real minCenterPanelWidth: 620
    property real maxLeftPanelWidth: 420
    property real maxRightPanelWidth: 520
    property real splitterWidth: 8
    property real resizeStartMouseX: 0.0
    property real resizeStartLeftWidth: 300
    property real resizeStartRightWidth: 380

    component PanelResizeHandle: Item {
        // Drag resizing is intentionally disabled.
        // Side panels are controlled by visible capsule toggle handles instead.
        property bool resizeLeft: true
        width: 0
        visible: false
    }

    function modelPoints() {
        try {
            return JSON.parse(bridge.modelPointsJson)
        } catch (e) {
            return []
        }
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

    function stressContourData() {
        try {
            return JSON.parse(bridge.stressContourJson)
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
        root.leftPanelWidth = left
        root.rightPanelWidth = right
    }

    function resizeLeftPanelBy(delta) {
        var total = availableWorkspaceWidth()
        var maxLeftByCenter = total - root.rightPanelWidth - root.minCenterPanelWidth - root.splitterWidth * 2
        root.leftPanelWidth = Math.max(
            root.minLeftPanelWidth,
            Math.min(root.maxLeftPanelWidth, Math.min(maxLeftByCenter, root.resizeStartLeftWidth + delta))
        )
    }

    function resizeRightPanelBy(delta) {
        var total = availableWorkspaceWidth()
        var maxRightByCenter = total - root.leftPanelWidth - root.minCenterPanelWidth - root.splitterWidth * 2
        root.rightPanelWidth = Math.max(
            root.minRightPanelWidth,
            Math.min(root.maxRightPanelWidth, Math.min(maxRightByCenter, root.resizeStartRightWidth - delta))
        )
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

    function switchMode(modeName) {
        currentMode = modeName
        resultOverlayMode = modeName === "求解结果" ? resultOverlayMode : "none"
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

    function contourColor(value, minValue, maxValue, alpha) {
        var t = (value - minValue) / Math.max(1e-12, maxValue - minValue)
        t = Math.max(0.0, Math.min(1.0, t))
        var r = Math.round(42 + 213 * t)
        var g = Math.round(123 + 88 * (1.0 - Math.abs(t - 0.5) * 2.0))
        var b = Math.round(235 - 180 * t)
        return "rgba(" + r + ", " + g + ", " + b + ", " + alpha + ")"
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

    function orderedFacePolygon(faceRow, pointMap) {
        if (!faceRow || !faceRow.edge_ids || faceRow.edge_ids.length < 3) {
            return []
        }
        var edges = modelEdges()
        var edgeMap = {}
        var adjacency = {}
        for (var i = 0; i < edges.length; i++) {
            edgeMap[edges[i].id] = edges[i]
        }
        for (var j = 0; j < faceRow.edge_ids.length; j++) {
            var edge = edgeMap[faceRow.edge_ids[j]]
            if (!edge) {
                continue
            }
            if (!adjacency[edge.start_point_id]) {
                adjacency[edge.start_point_id] = []
            }
            if (!adjacency[edge.end_point_id]) {
                adjacency[edge.end_point_id] = []
            }
            adjacency[edge.start_point_id].push(edge.end_point_id)
            adjacency[edge.end_point_id].push(edge.start_point_id)
        }
        var startEdge = edgeMap[faceRow.edge_ids[0]]
        if (!startEdge) {
            return []
        }
        var orderedIds = []
        var startId = startEdge.start_point_id
        var currentId = startId
        var previousId = ""
        var guard = 0
        while (guard < faceRow.edge_ids.length + 2) {
            orderedIds.push(currentId)
            var neighbors = adjacency[currentId] || []
            var nextId = ""
            for (var k = 0; k < neighbors.length; k++) {
                if (neighbors[k] !== previousId) {
                    nextId = neighbors[k]
                    break
                }
            }
            if (nextId === "" || nextId === startId) {
                break
            }
            previousId = currentId
            currentId = nextId
            guard += 1
        }
        var polygon = []
        for (var m = 0; m < orderedIds.length; m++) {
            if (pointMap[orderedIds[m]]) {
                polygon.push(pointMap[orderedIds[m]])
            }
        }
        return polygon
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
        drawScale = Math.max(48.0, drawScale)
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
        for (var i = faces.length - 1; i >= 0; i--) {
            var polygon = orderedFacePolygon(faces[i], pointMap)
            if (polygon.length >= 3 && pointInPolygon(mouseX, mouseY, polygon)) {
                return faces[i].id
            }
        }
        return ""
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
            var polygon = orderedFacePolygon(faces[fi], pointMap)
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
            ctx.strokeStyle = "#1D4ED8"
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
        ctx.strokeStyle = "#B91C1C"
        ctx.fillStyle = "#B91C1C"
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
                root.drawDistributedLoadOnEdge(
                    ctx,
                    pointMap[edge.start_point_id],
                    pointMap[edge.end_point_id],
                    rows[i].qx,
                    rows[i].qy
                )
            } else if (rows[i].target_type === "geometry_edge_segment") {
                var segmentEdge = edgeById(rows[i].target_id)
                if (!segmentEdge || !pointMap[segmentEdge.start_point_id] || !pointMap[segmentEdge.end_point_id]) {
                    continue
                }
                root.drawDistributedLoadOnEdgeSegment(
                    ctx,
                    pointMap[segmentEdge.start_point_id],
                    pointMap[segmentEdge.end_point_id],
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
                var polygon = orderedFacePolygon(faces[i], pointMap)
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
                ctx.strokeStyle = "#2563EB"
                ctx.lineWidth = 2.4
                ctx.fill()
                ctx.stroke()
            }
        } else if (bridge.selectedGeometryType === "edge" && bridge.selectedGeometryId !== "") {
            var edge = edgeById(bridge.selectedGeometryId)
            if (edge && pointMap[edge.start_point_id] && pointMap[edge.end_point_id]) {
                ctx.strokeStyle = "#2563EB"
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
                ctx.strokeStyle = "#1D4ED8"
                ctx.lineWidth = 2
                ctx.stroke()
            }
        }
        ctx.restore()
    }

    function handleModelingClick(mouseX, mouseY) {
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
                viewportHint = "请点击一个点作为连边端点。"
            } else if (bridge.edgeStartPointId === "") {
                bridge.selectGeometryPoint(pointId)
                bridge.startEdgeFromSelectedPoint()
                viewportHint = "已记录起点，请点击第二个点完成连边。"
            } else {
                bridge.connectEdgeToPoint(pointId)
                bridge.selectGeometryPoint(pointId)
                viewportHint = "已完成连边。"
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
        bridge.setModelTool("选择")
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

    Dialog {
        id: materialEditorDialog
        title: "材料编辑器"
        modal: true
        width: 540
        height: 520
        standardButtons: Dialog.Ok

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            Label {
                text: "当前材料"
                color: "#1F2937"
                font.pixelSize: 14
                font.bold: true
            }

            TextArea {
                Layout.fillWidth: true
                Layout.preferredHeight: 160
                readOnly: true
                text: bridge.materialRowsPreview
                wrapMode: Text.WordWrap
            }

            ComboBox {
                id: materialEditCombo
                Layout.fillWidth: true
                model: bridge.materialOptions
            }

            FormField { id: materialNameField; Layout.fillWidth: true; label: "材料名称"; text: "new_material" }
            FormField { id: materialEField; Layout.fillWidth: true; label: "弹性模量"; text: "210000000000" }
            FormField { id: materialNuField; Layout.fillWidth: true; label: "泊松比"; text: "0.3" }
            FormField { id: materialColorField; Layout.fillWidth: true; label: "颜色"; text: "#8FB7D8" }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                PrimaryButton {
                    text: "新增材料"
                    onClicked: bridge.addMaterial(
                        materialNameField.text,
                        Number(materialEField.text),
                        Number(materialNuField.text),
                        materialColorField.text
                    )
                }
                SecondaryButton {
                    text: "更新选中"
                    onClicked: bridge.updateMaterial(
                        root.parseMaterialIdFromOption(materialEditCombo.currentText),
                        materialNameField.text,
                        Number(materialEField.text),
                        Number(materialNuField.text),
                        materialColorField.text
                    )
                }
                SecondaryButton {
                    text: "删除选中"
                    onClicked: bridge.deleteMaterial(root.parseMaterialIdFromOption(materialEditCombo.currentText))
                }
            }
        }
    }

    Dialog {
        id: deformationPlotDialog
        title: "显示变形图"
        modal: true
        width: 760
        height: 620
        standardButtons: Dialog.Ok
        onOpened: {
            var data = root.deformationPlotData()
            var summary = data.summary || {}
            deformationScaleField.text = String(summary.default_scale_factor || 1.0)
            root.resultOverlayMode = "deformed"
            deformationCanvas.requestPaint()
            root.repaintViewport()
        }
        onClosed: {
            root.resultOverlayMode = "none"
            root.repaintViewport()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                FormField {
                    id: deformationScaleField
                    Layout.preferredWidth: 180
                    label: "放大系数"
                    text: "1.0"
                }
                Button {
                    text: "刷新"
                    onClicked: deformationCanvas.requestPaint()
                }
                Button {
                    text: "导出云图数据"
                    onClicked: bridge.exportContourData("outputs/latest")
                }
                Item { Layout.fillWidth: true }
            }

            Canvas {
                id: deformationCanvas
                Layout.fillWidth: true
                Layout.fillHeight: true
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.fillStyle = "#F8FAFC"
                    ctx.fillRect(0, 0, width, height)

                    var data = root.deformationPlotData()
                    var nodes = data.nodes || []
                    var elements = data.elements || []
                    if (nodes.length === 0 || elements.length === 0) {
                        ctx.fillStyle = "#334155"
                        ctx.font = "14px 'Microsoft YaHei UI'"
                        ctx.fillText("请先求解。", 20, 36)
                        return
                    }

                    var factor = Number(deformationScaleField.text)
                    if (!isFinite(factor) || factor <= 0.0) {
                        factor = 1.0
                    }

                    var originalPoints = []
                    var deformedPoints = []
                    var originalMap = {}
                    var deformedMap = {}
                    for (var i = 0; i < nodes.length; i++) {
                        var node = nodes[i]
                        var original = { x: node.x, y: node.y }
                        var deformed = { x: node.x + node.ux * factor, y: node.y + node.uy * factor }
                        originalPoints.push(original)
                        deformedPoints.push(deformed)
                        originalMap[node.node_id] = original
                        deformedMap[node.node_id] = deformed
                    }

                    var transform = root.canvasTransformForPoints(originalPoints.concat(deformedPoints), width, height, 24)

                    ctx.strokeStyle = "#CBD5E1"
                    ctx.lineWidth = 1
                    for (var j = 0; j < elements.length; j++) {
                        var tri = elements[j].node_ids
                        var oa = root.canvasPoint(transform, originalMap[tri[0]])
                        var ob = root.canvasPoint(transform, originalMap[tri[1]])
                        var oc = root.canvasPoint(transform, originalMap[tri[2]])
                        ctx.beginPath()
                        ctx.moveTo(oa.x, oa.y)
                        ctx.lineTo(ob.x, ob.y)
                        ctx.lineTo(oc.x, oc.y)
                        ctx.closePath()
                        ctx.stroke()
                    }

                    ctx.strokeStyle = "#7C3AED"
                    ctx.lineWidth = 1.4
                    for (var k = 0; k < elements.length; k++) {
                        var ids = elements[k].node_ids
                        var da = root.canvasPoint(transform, deformedMap[ids[0]])
                        var db = root.canvasPoint(transform, deformedMap[ids[1]])
                        var dc = root.canvasPoint(transform, deformedMap[ids[2]])
                        ctx.beginPath()
                        ctx.moveTo(da.x, da.y)
                        ctx.lineTo(db.x, db.y)
                        ctx.lineTo(dc.x, dc.y)
                        ctx.closePath()
                        ctx.stroke()
                    }
                }
            }
        }
    }

    Dialog {
        id: stressContourDialog
        title: "显示 Von Mises 云图"
        modal: true
        width: 760
        height: 620
        standardButtons: Dialog.Ok
        onOpened: {
            root.resultOverlayMode = "vonMises"
            stressContourCanvas.requestPaint()
            root.repaintViewport()
        }
        onClosed: {
            root.resultOverlayMode = "none"
            root.repaintViewport()
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 10

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Button {
                    text: "导出云图数据"
                    onClicked: bridge.exportContourData("outputs/latest")
                }
                Item { Layout.fillWidth: true }
            }

            Canvas {
                id: stressContourCanvas
                Layout.fillWidth: true
                Layout.fillHeight: true
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.clearRect(0, 0, width, height)
                    ctx.fillStyle = "#F8FAFC"
                    ctx.fillRect(0, 0, width, height)

                    var data = root.stressContourData()
                    var nodes = data.nodes || []
                    var elements = data.elements || []
                    if (nodes.length === 0 || elements.length === 0) {
                        ctx.fillStyle = "#334155"
                        ctx.font = "14px 'Microsoft YaHei UI'"
                        ctx.fillText("请先求解。", 20, 36)
                        return
                    }

                    var nodeMap = {}
                    for (var i = 0; i < nodes.length; i++) {
                        nodeMap[nodes[i].id] = nodes[i]
                    }
                    var transform = root.canvasTransformForPoints(nodes, width, height, 24)
                    var values = []
                    for (var j = 0; j < elements.length; j++) {
                        values.push(elements[j].von_mises)
                    }
                    var range = root.scalarRange(values)

                    for (var k = 0; k < elements.length; k++) {
                        var row = elements[k]
                        var ids = row.node_ids
                        var a = root.canvasPoint(transform, nodeMap[ids[0]])
                        var b = root.canvasPoint(transform, nodeMap[ids[1]])
                        var c = root.canvasPoint(transform, nodeMap[ids[2]])
                        ctx.beginPath()
                        ctx.moveTo(a.x, a.y)
                        ctx.lineTo(b.x, b.y)
                        ctx.lineTo(c.x, c.y)
                        ctx.closePath()
                        ctx.fillStyle = root.contourColor(row.von_mises, range.min, range.max, 0.82)
                        ctx.fill()
                        ctx.strokeStyle = "rgba(15, 23, 42, 0.18)"
                        ctx.lineWidth = 0.8
                        ctx.stroke()
                    }

                    ctx.fillStyle = "#334155"
                    ctx.font = "13px 'Microsoft YaHei UI'"
                    ctx.fillText("min = " + range.min.toExponential(4), 20, 28)
                    ctx.fillText("max = " + range.max.toExponential(4), 20, 50)
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

    Rectangle {
        anchors.fill: parent
        color: "#EEF3F8"

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                color: "#FFFFFF"
                border.color: "#D3DCE8"

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

                    Label {
                        text: "单模型四模块工作流"
                        color: "#64748B"
                        font.pixelSize: 13
                    }

                    Item { Layout.fillWidth: true }

                    Button { text: "新建工程"; onClicked: { bridge.newProject(); bridge.createEmptySketchForActivePart(); root.resultOverlayMode = "none"; root.hasQueryMarker = false } }
                    Button { text: "打开工程"; onClicked: openProjectDialog.open() }
                    Button { text: "保存工程"; onClicked: root.saveCurrentProjectWithDialogFallback() }
                    Button { text: "另存为"; onClicked: saveProjectDialog.open() }
                }
            }

            RowLayout {
                id: mainWorkspaceRow
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                ScrollView {
                    Layout.preferredWidth: root.leftPanelWidth
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Rectangle {
                        width: root.leftPanelWidth
                        color: "#F8FAFC"
                        border.color: "#D3DCE8"
                        implicitHeight: leftPanelColumn.implicitHeight + 32

                        ColumnLayout {
                            id: leftPanelColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 14
                            spacing: 12

                            Label { text: "工作流"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }

                            Repeater {
                                model: ["建模与材料", "网格生成", "约束与载荷", "求解结果"]
                                delegate: Rectangle {
                                    Layout.fillWidth: true
                                    implicitHeight: 42
                                    radius: 10
                                    color: modelData === root.currentMode ? "#DBEAFE" : "#FFFFFF"
                                    border.color: modelData === root.currentMode ? "#60A5FA" : "#D3DCE8"
                                    Text {
                                        anchors.centerIn: parent
                                        text: modelData
                                        color: "#1F2937"
                                        font.pixelSize: 13
                                        font.bold: modelData === root.currentMode
                                    }
                                    MouseArea {
                                        anchors.fill: parent
                                        onClicked: root.switchMode(modelData)
                                    }
                                }
                            }

                            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                            Label { text: "当前选择"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                            Text { Layout.fillWidth: true; text: "类型：" + selectedObjectType; color: "#334155"; wrapMode: Text.WordWrap }
                            Text { Layout.fillWidth: true; text: "名称：" + selectedObjectName; color: "#334155"; wrapMode: Text.WordWrap }
                            Text { Layout.fillWidth: true; text: selectedObjectDescription; color: "#64748B"; wrapMode: Text.WordWrap }
                            Button { text: "清空选择"; onClicked: root.clearSelection() }

                            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                            Label { text: "模型概览"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                            Text { text: "点数：" + bridge.modelPointCount; color: "#334155" }
                            Text { text: "边数：" + bridge.modelEdgeCount; color: "#334155" }
                            Text { text: "闭合面数：" + bridge.modelFaceCount; color: "#334155" }
                            Text { text: "网格节点：" + bridge.sketchMeshNodeCount; color: "#334155" }
                            Text { text: "网格单元：" + bridge.sketchMeshElementCount; color: "#334155" }
                            Text { text: "状态：" + bridge.statusText; color: "#64748B"; wrapMode: Text.WordWrap }
                        }
                    }
                }

                PanelResizeHandle {
                    id: leftPanelResizeHandle
                    Layout.fillHeight: true
                    resizeLeft: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#F8FAFC"
                    border.color: "#D3DCE8"

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 48
                            color: "#FFFFFF"
                            border.color: "#D3DCE8"

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 8
                                Label { text: "视口"; font.pixelSize: 15; font.bold: true; color: "#0F172A" }
                                Item { Layout.fillWidth: true }
                                Button { text: "适配视图"; onClicked: { root.viewportScale = 1.0; root.viewportOffsetX = 0.0; root.viewportOffsetY = 0.0; root.repaintViewport() } }
                                Button { text: "放大"; onClicked: { root.viewportScale *= 1.15; root.repaintViewport() } }
                                Button { text: "缩小"; onClicked: { root.viewportScale /= 1.15; root.repaintViewport() } }
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

                                onPressed: function(mouse) {
                                    root.lastMouseX = mouse.x
                                    root.lastMouseY = mouse.y
                                    root.viewportPressX = mouse.x
                                    root.viewportPressY = mouse.y
                                    root.viewportClickCandidate = mouse.button === Qt.LeftButton

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
                                    if (root.viewportClickCandidate && Math.sqrt(dx * dx + dy * dy) > 4) {
                                        root.viewportClickCandidate = false
                                    }

                                    if (root.isDraggingPoint) {
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
                                    if (root.viewportClickCandidate
                                            && mouse.button === Qt.LeftButton
                                            && !root.isDraggingPoint
                                            && !root.isPanning) {
                                        root.handleViewportClick(mouse.x, mouse.y)
                                    }

                                    root.viewportClickCandidate = false
                                    root.isDraggingPoint = false
                                    root.isPanning = false
                                }

                                onCanceled: {
                                    root.viewportClickCandidate = false
                                    root.isDraggingPoint = false
                                    root.isPanning = false
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 42
                            color: "#FFFFFF"
                            border.color: "#D3DCE8"
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10
                                Label { text: "提示：" + (root.viewportHint === "" ? bridge.statusText : root.viewportHint); color: "#475569"; font.pixelSize: 12 }
                                Item { Layout.fillWidth: true }
                                Label { text: "缩放：" + Math.round(root.viewportScale * 100) + "%"; color: "#64748B"; font.pixelSize: 12 }
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
                    Layout.preferredWidth: root.rightPanelWidth
                    Layout.fillHeight: true
                    clip: true
                    ScrollBar.vertical.policy: ScrollBar.AlwaysOff
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    Rectangle {
                        width: root.rightPanelWidth
                        color: "#FFFFFF"
                        border.color: "#D3DCE8"
                        implicitHeight: rightPanelColumn.implicitHeight + 32

                        ColumnLayout {
                            id: rightPanelColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 14
                            spacing: 12

                            Rectangle {
                                visible: root.currentMode === "建模与材料"
                                Layout.fillWidth: true
                                color: "#F8FAFC"
                                border.color: "#D3DCE8"
                                radius: 10
                                implicitHeight: modelingColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: modelingColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "建模工具"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Repeater {
                                            model: ["选择", "添加节点", "连接边", "移动节点", "删除"]
                                            delegate: Button {
                                                text: modelData
                                                onClicked: bridge.setModelTool(modelData)
                                            }
                                        }
                                    }

                                    FormField { id: pointXField; Layout.fillWidth: true; label: "点 X"; text: "0.0" }
                                    FormField { id: pointYField; Layout.fillWidth: true; label: "点 Y"; text: "0.0" }
                                    Button { text: "按坐标添加点"; onClicked: bridge.addModelPoint(Number(pointXField.text), Number(pointYField.text)) }

                                    FormField { id: edgeStartField; Layout.fillWidth: true; label: "起点 ID"; text: "p1" }
                                    FormField { id: edgeEndField; Layout.fillWidth: true; label: "终点 ID"; text: "p2" }
                                    Button { text: "连接边"; onClicked: bridge.connectModelEdge(edgeStartField.text, edgeEndField.text) }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button { text: "生成闭合面"; onClicked: bridge.buildModelFaces() }
                                        Button { text: "清空几何"; onClicked: bridge.clearModelGeometry() }
                                    }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "几何列表"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Label { text: "点列表"; color: "#334155"; font.pixelSize: 12 }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 72; readOnly: true; text: bridge.sketchNodeRowsPreview }
                                    Label { text: "边列表"; color: "#334155"; font.pixelSize: 12 }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 72; readOnly: true; text: bridge.sketchEdgeRowsPreview }
                                    Label { text: "闭合面列表"; color: "#334155"; font.pixelSize: 12 }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 72; readOnly: true; text: root.faceRowsPreview() }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "材料分配"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    ComboBox { id: materialAssignCombo; Layout.fillWidth: true; model: bridge.materialOptions }
                                    FormField { id: thicknessAssignField; Layout.fillWidth: true; label: "厚度"; text: String(bridge.activePartThickness) }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "应用到选中闭合面"
                                            onClicked: bridge.assignMaterialToSelectedFace(
                                                root.parseMaterialIdFromOption(materialAssignCombo.currentText),
                                                Number(thicknessAssignField.text)
                                            )
                                        }
                                        Button {
                                            text: "应用到全部闭合面"
                                            onClicked: bridge.assignMaterialToAllFaces(
                                                root.parseMaterialIdFromOption(materialAssignCombo.currentText),
                                                Number(thicknessAssignField.text)
                                            )
                                        }
                                    }

                                    Button { text: "打开材料编辑器"; onClicked: materialEditorDialog.open() }

                                    Label { text: "闭合面材料列表"; color: "#334155"; font.pixelSize: 12 }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 84; readOnly: true; text: bridge.faceMaterialRowsPreview }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "网格生成"
                                Layout.fillWidth: true
                                color: "#F8FAFC"
                                border.color: "#D3DCE8"
                                radius: 10
                                implicitHeight: meshColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: meshColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "网格生成"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Label { text: "唯一正式网格器：Gmsh CST 三角网格"; color: "#334155"; wrapMode: Text.WordWrap }
                                    FormField { id: meshTargetSizeField; Layout.fillWidth: true; label: "target_size"; text: String(bridge.meshTargetSize) }
                                    FormField { id: meshMinAngleField; Layout.fillWidth: true; label: "min_angle"; text: String(bridge.meshMinAngle) }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button { text: "生成网格"; onClicked: bridge.generateMesh(Number(meshTargetSizeField.text), Number(meshMinAngleField.text)) }
                                        Button { text: "清除网格"; onClicked: bridge.clearMesh() }
                                    }
                                    Text { text: "网格后端状态：" + (bridge.currentMeshType === "none" ? "未生成" : bridge.currentMeshType); color: "#334155" }
                                    Text { text: "节点数：" + bridge.sketchMeshNodeCount; color: "#334155" }
                                    Text { text: "单元数：" + bridge.sketchMeshElementCount; color: "#334155" }
                                    Text { text: "面积误差 / 质量摘要"; color: "#334155" }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 140; readOnly: true; text: bridge.meshQualitySummaryText === "" ? bridge.statusText : bridge.meshQualitySummaryText }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "约束与载荷"
                                Layout.fillWidth: true
                                color: "#F8FAFC"
                                border.color: "#D3DCE8"
                                radius: 10
                                implicitHeight: targetColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: targetColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "约束与载荷"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Text {
                                        Layout.fillWidth: true
                                        wrapMode: Text.WordWrap
                                        text: bridge.selectedTargetType === "" ? "当前目标：未选择" : "当前目标：" + bridge.selectedTargetType + " | " + bridge.selectedTargetId
                                        color: "#334155"
                                    }

                                    CheckBox { id: uxFixedBox; text: "固定 Ux"; checked: true }
                                    CheckBox { id: uyFixedBox; text: "固定 Uy"; checked: true }
                                    Button { text: "添加约束"; onClicked: bridge.addConstraintToSelectedTarget(uxFixedBox.checked, uyFixedBox.checked) }

                                    FormField { id: deleteBcField; Layout.fillWidth: true; label: "删除约束 ID"; text: "bc_1" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button { text: "删除约束"; onClicked: bridge.deleteBoundaryCondition(deleteBcField.text) }
                                        Button { text: "清空约束"; onClicked: bridge.clearConstraints() }
                                    }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 92; readOnly: true; text: bridge.boundaryConditionRowsPreview }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "载荷"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    FormField { id: loadXField; Layout.fillWidth: true; label: "Fx / qx"; text: "0.0" }
                                    FormField { id: loadYField; Layout.fillWidth: true; label: "Fy / qy"; text: "-1000.0" }
                                    FormField { id: loadStartTField; Layout.fillWidth: true; label: "start_t"; text: String(bridge.edgeLoadStartT) }
                                    FormField { id: loadEndTField; Layout.fillWidth: true; label: "end_t"; text: String(bridge.edgeLoadEndT) }
                                    FormField { id: loadStartXField; Layout.fillWidth: true; label: "起点 X"; text: "0.0" }
                                    FormField { id: loadStartYField; Layout.fillWidth: true; label: "起点 Y"; text: "0.0" }
                                    FormField { id: loadEndXField; Layout.fillWidth: true; label: "终点 X"; text: "0.0" }
                                    FormField { id: loadEndYField; Layout.fillWidth: true; label: "终点 Y"; text: "0.0" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "整边模式"
                                            onClicked: {
                                                bridge.useFullEdgeLoadRange()
                                                loadStartTField.text = String(bridge.edgeLoadStartT)
                                                loadEndTField.text = String(bridge.edgeLoadEndT)
                                            }
                                        }
                                        Button {
                                            text: "应用区间参数"
                                            onClicked: bridge.setSelectedEdgeLoadSegmentRange(
                                                Number(loadStartTField.text),
                                                Number(loadEndTField.text)
                                            )
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "坐标投影区间"
                                            onClicked: bridge.setSelectedEdgeLoadSegmentFromCoordinates(
                                                Number(loadStartXField.text),
                                                Number(loadStartYField.text),
                                                Number(loadEndXField.text),
                                                Number(loadEndYField.text)
                                            )
                                        }
                                        Button {
                                            text: bridge.edgeLoadSegmentSelectionMode ? "取消区间设置" : "设置局部载荷区间"
                                            onClicked: {
                                                if (bridge.edgeLoadSegmentSelectionMode) {
                                                    bridge.cancelEdgeLoadSegmentSelection()
                                                } else {
                                                    bridge.beginEdgeLoadSegmentSelection()
                                                }
                                            }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "添加集中力"
                                            onClicked: bridge.addLoadToSelectedTarget("nodal_concentrated", Number(loadXField.text), Number(loadYField.text))
                                        }
                                        Button {
                                            text: bridge.hasEdgeLoadSegment ? "添加局部均布载荷" : "添加均布载荷"
                                            onClicked: bridge.addLoadToSelectedTarget("edge_uniform", Number(loadXField.text), Number(loadYField.text))
                                        }
                                    }
                                    FormField { id: deleteLoadField; Layout.fillWidth: true; label: "删除载荷 ID"; text: "load_1" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button { text: "删除载荷"; onClicked: bridge.deleteLoad(deleteLoadField.text) }
                                        Button { text: "清空载荷"; onClicked: bridge.clearLoads() }
                                    }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 92; readOnly: true; text: bridge.loadRowsPreview }
                                }
                            }

                            Rectangle {
                                visible: root.currentMode === "求解结果"
                                Layout.fillWidth: true
                                color: "#F8FAFC"
                                border.color: "#D3DCE8"
                                radius: 10
                                implicitHeight: resultColumn.implicitHeight + 20

                                ColumnLayout {
                                    id: resultColumn
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8

                                    Label { text: "求解结果"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Button { text: "求解当前模型"; onClicked: bridge.solveCurrentModel() }
                                    Text { text: "求解状态：" + bridge.statusText; color: "#334155"; wrapMode: Text.WordWrap }
                                    Text { text: "最大位移：" + (bridge.maxDisplacement === "" ? "—" : bridge.maxDisplacement); color: "#334155" }
                                    Text { text: "最大 Von Mises：" + (bridge.maxVonMises === "" ? "—" : bridge.maxVonMises); color: "#334155" }
                                    Text { text: "Warning 数量：" + bridge.warningCount; color: "#334155" }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        Button {
                                            text: "显示变形图"
                                            onClicked: {
                                                if (!bridge.hasSolution) {
                                                    root.viewportHint = "请先求解。"
                                                    return
                                                }
                                                deformationPlotDialog.open()
                                            }
                                        }
                                        Button {
                                            text: "显示 Von Mises 云图"
                                            onClicked: {
                                                if (!bridge.hasSolution) {
                                                    root.viewportHint = "请先求解。"
                                                    return
                                                }
                                                stressContourDialog.open()
                                            }
                                        }
                                    }

                                    FormField { id: queryXField; Layout.fillWidth: true; label: "查询 X"; text: String(bridge.resultQueryX) }
                                    FormField { id: queryYField; Layout.fillWidth: true; label: "查询 Y"; text: String(bridge.resultQueryY) }
                                    Button {
                                        text: "查询结果"
                                        onClicked: {
                                            root.queryMarkerX = Number(queryXField.text)
                                            root.queryMarkerY = Number(queryYField.text)
                                            root.hasQueryMarker = true
                                            bridge.queryResultAtPoint(Number(queryXField.text), Number(queryYField.text))
                                        }
                                    }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 150; readOnly: true; text: bridge.resultQueryText }

                                    Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: "#D3DCE8" }

                                    Label { text: "导出"; color: "#0F172A"; font.pixelSize: 15; font.bold: true }
                                    Button { text: "导出云图数据"; onClicked: bridge.exportContourData("outputs/latest") }
                                    Button { text: "导出全部结果"; onClicked: bridge.exportResults("outputs/latest") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


}
