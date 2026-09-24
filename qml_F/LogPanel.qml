import QtQuick
import QtQuick.Controls
import Manipulador_IA

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
        /*Row {
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
        }*/
        Row {
            id: row_results
            x: 0
            y: 0
            width: 1137
            height: 203
            spacing: 10

            GroupBox {
                id: groupBox
                width: row_results.width / 2 - 5
                height: 200

                title: qsTr("Objetos Detectados")
                font.pointSize: 15
                font.bold: true

                ScrollView {
                    anchors.fill: parent
                    clip: true

                    TextArea {
                        id: textEdit
                        readOnly: true
                        selectByMouse: true
                        font.pixelSize: 13
                        wrapMode: TextEdit.Wrap
                        placeholderText: qsTr("Nenhum objeto detectado ainda...")
                        background: Rectangle {
                            color: "#f8f9fa"
                            radius: 4
                            border.color: "#dee2e6"
                        }
                    }
                }
            }

            GroupBox {
                id: groupBox1
                width: row_results.width / 2 - 5
                height: 200

                title: qsTr("Logs e Ações")
                font.pointSize: 15
                font.bold: true

                ScrollView {
                    anchors.fill: parent
                    clip: true

                    TextArea {
                        id: textEdit1
                        readOnly: true
                        selectByMouse: true
                        font.pixelSize: 13
                        wrapMode: TextEdit.Wrap
                        placeholderText: qsTr("Aguardando inicialização do sistema...")
                        background: Rectangle {
                            color: "#f8f9fa"
                            radius: 4
                            border.color: "#dee2e6"
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: backend

        function onLogMessage(texto) {
            var agora = new Date()
            var hh = String(agora.getHours()).padStart(2, '0')
            var mm = String(agora.getMinutes()).padStart(2, '0')
            var ss = String(agora.getSeconds()).padStart(2, '0')
            var timestamp = "[" + hh + ":" + mm + ":" + ss + "] "
            textEdit1.append(timestamp + texto)
        }

        function onObjectDetected(classe) {
            var agora = new Date()
            var hh = String(agora.getHours()).padStart(2, '0')
            var mm = String(agora.getMinutes()).padStart(2, '0')
            var ss = String(agora.getSeconds()).padStart(2, '0')
            var timestamp = "[" + hh + ":" + mm + ":" + ss + "] "
            textEdit.append(timestamp + classe)
        }
    }
}
