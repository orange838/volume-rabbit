import QtQuick

Item {
    id: root
    width: 92
    height: 150

    property color bodyColor: "#F08A3C"
    property color bodyDark: "#C96A22"

    // 叶子
    Item {
        id: leaves
        x: 18
        y: 0
        width: 56
        height: 52

        Rectangle {
            x: 16; y: 2; width: 20; height: 46; radius: 10
            color: "#5FA845"
            rotation: -26
            transformOrigin: Item.Bottom
        }
        Rectangle {
            x: 22; y: -4; width: 22; height: 52; radius: 11
            color: "#6EBD4F"
            rotation: -4
            transformOrigin: Item.Bottom
        }
        Rectangle {
            x: 26; y: 2; width: 20; height: 46; radius: 10
            color: "#4F9238"
            rotation: 20
            transformOrigin: Item.Bottom
        }
    }

    // 萝卜身体
    Canvas {
        id: body
        x: 0
        y: 40
        width: root.width
        height: root.height - 40

        onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            var cx = width / 2
            ctx.beginPath()
            ctx.moveTo(cx - 26, 6)
            ctx.quadraticCurveTo(cx - 30, 30, cx - 6, height - 8)
            ctx.quadraticCurveTo(cx, height, cx + 6, height - 8)
            ctx.quadraticCurveTo(cx + 30, 30, cx + 26, 6)
            ctx.quadraticCurveTo(cx, -4, cx - 26, 6)
            ctx.closePath()

            var grad = ctx.createLinearGradient(cx - 26, 0, cx + 26, 0)
            grad.addColorStop(0, root.bodyDark)
            grad.addColorStop(0.35, root.bodyColor)
            grad.addColorStop(1, "#FBB066")
            ctx.fillStyle = grad
            ctx.fill()

            ctx.strokeStyle = "#B85E1C"
            ctx.lineWidth = 1.6
            ctx.stroke()

            // 纹理
            ctx.strokeStyle = "rgba(180,90,25,0.45)"
            ctx.lineWidth = 1.6
            for (var i = 1; i <= 3; i++) {
                var yy = 26 + i * 22
                ctx.beginPath()
                ctx.moveTo(cx - 16 + i, yy)
                ctx.quadraticCurveTo(cx, yy + 5, cx + 14 - i, yy - 2)
                ctx.stroke()
            }
        }
    }
}
