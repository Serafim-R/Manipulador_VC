import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 800
    height: 600

    Image {
        id: img

        anchors.fill: parent
        fillMode: Image.PreserveAspectFit

        // cache precisa ser false, senão o QML reaproveita a imagem antiga
        // mesmo quando a URL muda
        cache: false

        property int refresh: 0

        // a query "?refresh" força o QML a tratar isso como uma nova imagem
        // e chamar requestImage() no provider de novo a cada frame
        source: "image://camera/current?" + refresh

        onStatusChanged: {
            console.log("Image status:", status)
        }
    }

    Connections {
        target: backend

        function onCameraFrameChanged() {
            img.refresh++
        }
    }
}
