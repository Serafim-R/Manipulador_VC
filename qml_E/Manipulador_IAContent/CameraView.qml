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
            id: image
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.leftMargin: 10
            anchors.rightMargin: 10
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            fillMode: Image.PreserveAspectFit
        }
    }
}
