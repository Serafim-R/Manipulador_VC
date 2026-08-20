import QtQuick
import QtQuick.Controls
//import Manipulador_IA 1.0

Item {
    id: root
    width: Constants.width
    height: Constants.height

    Column {
        id: buttons_box
        x: 973
        y: 339
        width: 219
        height: 253
        spacing: 10
        layer.enabled: true
        Button {
            id: button_calibrar
            width: 150
            height: 50
            text: qsTr("Calibrar")
            icon.width: 24
            icon.color: "#ffffff"
            highlighted: true
            font.pointSize: 15
            font.bold: true
            flat: false
            checkable: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Button {
            id: btn_reconhecer
            width: 150
            height: 50
            text: qsTr("Reconhecer")
            highlighted: true
            font.pointSize: 15
            font.bold: true
            flat: true
            checkable: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Button {
            id: button_manipular
            width: 150
            height: 50
            text: qsTr("Manipular")
            highlighted: true
            font.pointSize: 15
            font.bold: true
            flat: true
            checkable: true
            anchors.horizontalCenter: parent.horizontalCenter
        }

        Button {
            id: button_home
            width: 150
            height: 50
            visible: true
            text: qsTr("HOME")
            wheelEnabled: false
            highlighted: true
            font.pointSize: 15
            font.bold: true
            flat: true
            checked: false
            checkable: true
            autoRepeat: false
            autoExclusive: false
            anchors.horizontalCenter: parent.horizontalCenter

            onClicked: backend.home()
        }
        clip: false
        baselineOffset: 6
    }
}
