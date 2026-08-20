import QtQuick
import QtQuick.Controls

Item {
    id: root
    width: 1920
    height: 1080

    Rectangle {
        id: framecam_position
        x: 47
        y: 200
        width: 855
        height: 530
        color: "#00000000"
        border.width: 3
        Image {
            id: cameraImage
            
            anchors.fill: parent

            fillMode: Image.PreserveAspectFit

            cache: false

            property int refresh: 0

            source: "image://camera/current?" + refresh
        }
    }

    Connections {

        target: backend

        function onCameraFrameChanged() {

            cameraImage.refresh++

        }

    }
}

/*import QtQuick
import QtQuick.Controls

Item {

    width: 800
    height: 600

    Image {

        id: img

        anchors.fill: parent

        source: "image://camera/current"

        onStatusChanged: {

            console.log(status)

        }

    }

}*/
