import QtQuick
import QtQuick.Controls
import Manipulador_IA
import CameraModule 1.0

Item {
    id: root
    // mesma referencia usada por ControlPanel/StatusPanel/LogPanel: sem isso
    // o retangulo abaixo extravasa o pai e so aparece porque clip e false
    width: Constants.width
    height: Constants.height

    Rectangle {
        id: framecam_position
        x: 47
        y: 200
        width: 855
        height: 530
        color: "#202020"
        border.width: 3
        CameraItem {
            id: cameraView
            objectName: "cameraView"
            anchors.fill: parent
        }
    }

    Connections {
        target: backend

        function onCameraFrameChanged(image) {
            cameraView.updateImage(image)
        }
    }
}
