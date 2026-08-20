import QtQuick
import QtQuick.Controls
import Manipulador_IA


Rectangle {
    id: rectangle_topMargin
    x: 0
    width: parent ? parent.width: 1920
    height: 120
    color: "#b611a66a"

    Text {
        id: label_txt1
        x: 50
        text: qsTr("Sistema de Manipulação IA - LabMan (v0.1)")
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 50
        anchors.topMargin: 30
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        font.pointSize: 20
        font.family: Constants.font.family
        font.bold: true
    }

    Image {
        id: ufrn_logo
        x: 1759
        y: 12
        width: 123
        height: 108
        source: "images/ufrn-logo-png_seeklogo-144360.png"
        fillMode: Image.PreserveAspectFit
    }
}
