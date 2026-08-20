import QtQuick
import QtQuick.Controls
//import Manipulador_IA 1.0
import QtQuick.Layouts
//import QtQuick.Studio.Components

Item {
    id: root
    width: Constants.width
    height: Constants.height

    Row {
        id: row
        x: 1177
        y: 126
        width: 221
        height: 68
        spacing: 10
        Button {
            id: info
            height: 60
            text: qsTr("Info")
            onClicked: { stackLayout1.currentIndex = 0 }
            highlighted: true
            font.pointSize: 15
            font.bold: true
            checkable: true
        }

        Button {
            id: stts
            height: 60
            text: "Status"
            onClicked: { stackLayout1.currentIndex = 1 }
            highlighted: true
            font.pointSize: 15
            font.bold: true
            checkable: true
        }
    }

    StackLayout {
        id: stackLayout1
        x: 1177
        y: 200
        width: 685
        height: 530
        Item {
            id: infos
            Text {
                id: posX
                x: 33
                y: 59
                width: 84
                height: 42
                text: qsTr("Posição X:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            TextEdit {
                id: posXedit
                x: 150
                y: 65
                width: 366
                height: 31
                text: qsTr("PosX")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                selectByMouse: true
                selectByKeyboard: false
                readOnly: true
                activeFocusOnPress: true
            }

            Text {
                id: posY
                x: 33
                y: 131
                width: 84
                height: 42
                text: qsTr("Posição Y:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            TextEdit {
                id: posYedit
                x: 150
                y: 137
                width: 366
                height: 31
                text: qsTr("PosY")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                selectByMouse: true
                readOnly: true
                activeFocusOnPress: true
            }

            Text {
                id: posZ
                x: 33
                y: 214
                width: 84
                height: 42
                text: qsTr("Posição Z:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            TextEdit {
                id: posZedit
                x: 150
                y: 220
                width: 366
                height: 31
                text: qsTr("PosZ")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                readOnly: true
            }

            Text {
                id: text1
                x: 302
                y: 8
                text: qsTr("Posições")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
            }

            Text {
                id: text2
                x: 306
                y: 269
                text: qsTr("Ângulos")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
            }

            Text {
                id: angA
                x: 33
                y: 318
                width: 84
                height: 42
                text: qsTr("ângulo A:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                id: angB
                x: 33
                y: 402
                width: 84
                height: 42
                text: qsTr("ângulo B:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                id: angC
                x: 33
                y: 473
                width: 84
                height: 42
                text: qsTr("ângulo C:")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        Item {
            id: status
            Text {
                id: status_manip
                x: 59
                y: 59
                text: qsTr("Manipulador")
                font.pixelSize: 20
                font.bold: true
            }

            Text {
                id: status_manip1
                x: 59
                y: 154
                text: qsTr("Cam")
                font.pixelSize: 20
                font.bold: true
            }

            Rectangle {
                id: cam_ind
                x: 226
                y: 154
                width: 40
                height: 40
                radius: width/2
                border.color: "#000000"
                color: "#7c7878"
                property bool camOn: false
                property bool camOff: false
            }

            Rectangle {
                id: manip_ind
                x: 226
                y: 59
                width: 40
                height: 40
                radius: width/2
                border.color: "#000000"
                color: "#7c7878"
                property bool camOn: false
                property bool camOff: false
            }
        }
        currentIndex: 0
    }
}
