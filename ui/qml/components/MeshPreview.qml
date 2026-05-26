import QtQuick

Canvas {
    id: root

    property string mode: "part"
    property int nx: 4
    property int ny: 2
    property real widthValue: 2.0
    property real heightValue: 1.0

    implicitWidth: 420
    implicitHeight: 240

    onModeChanged: requestPaint()
    onNxChanged: requestPaint()
    onNyChanged: requestPaint()
    onWidthValueChanged: requestPaint()
    onHeightValueChanged: requestPaint()
    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()

        var margin = 26
        var w = width - 2 * margin
        var h = height - 2 * margin
        var ratio = widthValue / Math.max(heightValue, 0.0001)
        if (ratio > w / h) {
            h = w / ratio
        } else {
            w = h * ratio
        }
        var x = (width - w) / 2
        var y = (height - h) / 2

        ctx.fillStyle = "#F9FAFB"
        ctx.fillRect(0, 0, width, height)

        ctx.fillStyle = "#FFFFFF"
        ctx.strokeStyle = "#111827"
        ctx.lineWidth = 2
        ctx.fillRect(x, y, w, h)
        ctx.strokeRect(x, y, w, h)

        if (mode === "mesh") {
            ctx.strokeStyle = "#93C5FD"
            ctx.lineWidth = 1
            for (var i = 1; i < nx; ++i) {
                var gx = x + w * i / nx
                ctx.beginPath()
                ctx.moveTo(gx, y)
                ctx.lineTo(gx, y + h)
                ctx.stroke()
            }
            for (var j = 1; j < ny; ++j) {
                var gy = y + h * j / ny
                ctx.beginPath()
                ctx.moveTo(x, gy)
                ctx.lineTo(x + w, gy)
                ctx.stroke()
            }
            ctx.strokeStyle = "#BFDBFE"
            for (var col = 0; col < nx; ++col) {
                for (var row = 0; row < ny; ++row) {
                    var x0 = x + w * col / nx
                    var y0 = y + h * row / ny
                    var x1 = x + w * (col + 1) / nx
                    var y1 = y + h * (row + 1) / ny
                    ctx.beginPath()
                    ctx.moveTo(x0, y1)
                    ctx.lineTo(x1, y0)
                    ctx.stroke()
                }
            }
        }

        if (mode === "boundary") {
            ctx.strokeStyle = "#16A34A"
            ctx.lineWidth = 5
            ctx.beginPath()
            ctx.moveTo(x, y)
            ctx.lineTo(x, y + h)
            ctx.stroke()
        }

        if (mode === "load") {
            ctx.strokeStyle = "#2563EB"
            ctx.lineWidth = 5
            ctx.beginPath()
            ctx.moveTo(x + w, y)
            ctx.lineTo(x + w, y + h)
            ctx.stroke()

            ctx.strokeStyle = "#2563EB"
            ctx.fillStyle = "#2563EB"
            ctx.lineWidth = 2
            for (var k = 0; k < 5; ++k) {
                var ay = y + h * (k + 0.5) / 5
                ctx.beginPath()
                ctx.moveTo(x + w + 18, ay - 18)
                ctx.lineTo(x + w + 18, ay + 10)
                ctx.stroke()
                ctx.beginPath()
                ctx.moveTo(x + w + 18, ay + 10)
                ctx.lineTo(x + w + 12, ay)
                ctx.lineTo(x + w + 24, ay)
                ctx.closePath()
                ctx.fill()
            }
        }

        ctx.fillStyle = "#6B7280"
        ctx.font = "12px sans-serif"
        ctx.fillText(widthValue + " x " + heightValue, x, y + h + 18)
    }
}
