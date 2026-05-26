import QtQuick
import QtQuick.Controls

Rectangle {
    id: root

    property string mode: "工程"
    property int nx: 4
    property int ny: 2
    property real widthValue: 2.0
    property real heightValue: 1.0
    property bool hasSolution: false

    signal repaintRequested()

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

                var maxW = width * 0.60
                var maxH = height * 0.52
                var plateW = maxW
                var plateH = plateW * root.heightValue / Math.max(root.widthValue, 0.0001)
                if (plateH > maxH) {
                    plateH = maxH
                    plateW = plateH * root.widthValue / Math.max(root.heightValue, 0.0001)
                }

                var px = (width - plateW) / 2
                var py = (height - plateH) / 2

                if (root.mode === "装配") {
                    ctx.strokeStyle = "#94A3B8"
                    ctx.lineWidth = 1
                    ctx.setLineDash([8, 6])
                    ctx.strokeRect(px - 32, py - 24, plateW, plateH)
                    ctx.setLineDash([])
                }

                ctx.fillStyle = "#F8FAFC"
                ctx.strokeStyle = "#334155"
                ctx.lineWidth = 2
                ctx.fillRect(px, py, plateW, plateH)
                ctx.strokeRect(px, py, plateW, plateH)

                var showMesh = root.mode === "网格" || root.mode === "求解" || root.mode === "结果"
                if (showMesh) {
                    ctx.strokeStyle = "#7D8EA3"
                    ctx.lineWidth = 1
                    for (var i = 1; i < root.nx; i++) {
                        var x = px + plateW * i / root.nx
                        ctx.beginPath()
                        ctx.moveTo(x, py)
                        ctx.lineTo(x, py + plateH)
                        ctx.stroke()
                    }
                    for (var j = 1; j < root.ny; j++) {
                        var y = py + plateH * j / root.ny
                        ctx.beginPath()
                        ctx.moveTo(px, y)
                        ctx.lineTo(px + plateW, y)
                        ctx.stroke()
                    }
                    for (var cx = 0; cx < root.nx; cx++) {
                        for (var cy = 0; cy < root.ny; cy++) {
                            var x0 = px + plateW * cx / root.nx
                            var x1 = px + plateW * (cx + 1) / root.nx
                            var y0 = py + plateH * cy / root.ny
                            var y1 = py + plateH * (cy + 1) / root.ny
                            ctx.beginPath()
                            ctx.moveTo(x0, y1)
                            ctx.lineTo(x1, y0)
                            ctx.stroke()
                        }
                    }
                }

                if (root.mode === "边界") {
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
                        ctx.arc(px - 12, by, 4, 0, Math.PI * 2)
                        ctx.fill()
                    }
                }

                if (root.mode === "载荷") {
                    ctx.strokeStyle = "#D97706"
                    ctx.fillStyle = "#D97706"
                    ctx.lineWidth = 2
                    for (var a = 1; a <= 5; a++) {
                        var ay = py + plateH * a / 6
                        var ax = px + plateW + 38
                        ctx.beginPath()
                        ctx.moveTo(ax, ay - 28)
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

                if (root.mode === "结果" && root.hasSolution) {
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

                ctx.fillStyle = "#334155"
                ctx.font = "13px 'Microsoft YaHei UI'"
                ctx.fillText("视口 / " + root.mode, 18, 28)
                ctx.fillStyle = "#64748B"
                ctx.font = "12px 'Microsoft YaHei UI'"
                ctx.fillText("矩形尺寸：" + root.widthValue + " × " + root.heightValue + "    网格：" + root.nx + " × " + root.ny, 18, 48)
            }

            Connections {
                target: root
                function onModeChanged() { viewport.requestPaint() }
                function onNxChanged() { viewport.requestPaint() }
                function onNyChanged() { viewport.requestPaint() }
                function onWidthValueChanged() { viewport.requestPaint() }
                function onHeightValueChanged() { viewport.requestPaint() }
                function onHasSolutionChanged() { viewport.requestPaint() }
            }
        }

        ViewportToolbar {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.margins: 14
            mode: root.mode
        }
    }
}
