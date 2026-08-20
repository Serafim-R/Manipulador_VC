import QtQuick
import QtQuick.Controls
//import Manipulador_IA 1.0

Item {
    id: root
    width: Constants.width
    height: Constants.height

    Rectangle {
        id: results_place
        x: 47
        y: 777
        width: 1145
        height: 211
        color: "#00ffffff"
        border.width: 8
        Row {
            id: row_results
            x: 0
            y: 0
            width: 1137
            height: 203
            GroupBox {
                id: groupBox
                width: row_results.width / 2
                height: 200
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 0
                title: qsTr("Objetos Detectados")
                font.pointSize: 15
                font.bold: true
                TextEdit {
                    id: textEdit
                    x: 0
                    y: 0
                    width: 539
                    height: 143
                    text: qsTr("Objetos...")
                    font.pixelSize: 12
                }
            }

            GroupBox {
                id: groupBox1
                width: row_results.width / 2
                height: 200
                anchors.verticalCenter: parent.verticalCenter
                anchors.right: parent.right
                anchors.rightMargin: 0
                title: qsTr("Função")
                font.pointSize: 15
                font.bold: true
                TextEdit {
                    id: textEdit1
                    x: 0
                    y: 0
                    width: 545
                    height: 143
                    text: qsTr("Funções...")
                    font.pixelSize: 12
                }
            }
        }
    }

}
