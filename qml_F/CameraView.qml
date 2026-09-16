import QtQuick
import QtQuick.Controls
import CameraModule 1.0

Item {
    id: root
    width: 800
    height: 600

    Rectangle {
        id: framecam_position
        x: 47
        y: 200
        width: 855
        height: 530
        color: "#00000000"
        border.width: 3
        CameraItem {
            id: cameraView
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
