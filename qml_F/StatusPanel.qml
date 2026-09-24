import QtQuick
import QtQuick.Controls
import Manipulador_IA 
import QtQuick.Layouts

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
        currentIndex: 0

        Item {
            id: infos

            Text {
                id: text1
                x: 0
                y: 8
                width: parent.width
                text: qsTr("Posição Cartesiana (Mundo)")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
            }

            // Posição X
            Text {
                id: posX
                x: 33
                y: 50
                width: 100
                height: 35
                text: qsTr("Posição X:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 150
                y: 50
                width: 470
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: posXedit
                    anchors.fill: parent
                    text: qsTr("0.00 mm")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    selectByMouse: true
                    readOnly: true
                }
            }

            // Posição Y
            Text {
                id: posY
                x: 33
                y: 95
                width: 100
                height: 35
                text: qsTr("Posição Y:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 150
                y: 95
                width: 470
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: posYedit
                    anchors.fill: parent
                    text: qsTr("0.00 mm")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    selectByMouse: true
                    readOnly: true
                }
            }

            // Posição Z
            Text {
                id: posZ
                x: 33
                y: 140
                width: 100
                height: 35
                text: qsTr("Posição Z:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 150
                y: 140
                width: 470
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: posZedit
                    anchors.fill: parent
                    text: qsTr("0.00 mm")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    selectByMouse: true
                    readOnly: true
                }
            }

            // Ângulos das Juntas
            Text {
                id: text2
                x: 0
                y: 195
                width: parent.width
                text: qsTr("Ângulos das Juntas")
                font.pixelSize: 20
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                font.bold: true
            }

            // Linha 1: J1 e J4 (A)
            Text {
                id: lblJ1
                x: 33
                y: 245
                width: 70
                height: 35
                text: qsTr("J1:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 110
                y: 245
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j1Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
            }

            Text {
                id: lblJ4
                x: 340
                y: 245
                width: 90
                height: 35
                text: qsTr("J4 (A):")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 440
                y: 245
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j4Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
            }

            // Linha 2: J2 e J5 (B)
            Text {
                id: lblJ2
                x: 33
                y: 295
                width: 70
                height: 35
                text: qsTr("J2:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 110
                y: 295
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j2Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
            }

            Text {
                id: lblJ5
                x: 340
                y: 295
                width: 90
                height: 35
                text: qsTr("J5 (B):")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 440
                y: 295
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j5Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
            }

            // Linha 3: J3 e J6 (C)
            Text {
                id: lblJ3
                x: 33
                y: 345
                width: 70
                height: 35
                text: qsTr("J3:")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 110
                y: 345
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j3Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
            }

            Text {
                id: lblJ6
                x: 340
                y: 345
                width: 90
                height: 35
                text: qsTr("J6 (C):")
                font.pixelSize: 18
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
            }

            Rectangle {
                x: 440
                y: 345
                width: 180
                height: 35
                color: "#f8f9fa"
                radius: 4
                border.color: "#cccccc"
                border.width: 1

                TextEdit {
                    id: j6Edit
                    anchors.fill: parent
                    text: qsTr("0.0°")
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    readOnly: true
                    selectByMouse: true
                }
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

            Rectangle {
                id: manip_ind
                x: 226
                y: 59
                width: 40
                height: 40
                radius: width / 2
                border.color: "#000000"
                color: "#3fae49"
            }

            Text {
                id: manip_status_txt
                x: 286
                y: 59
                width: 370
                height: 40
                text: qsTr("Pronto")
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
                color: "#000000"
            }

            Text {
                id: status_manip1
                x: 59
                y: 154
                text: qsTr("Câmera")
                font.pixelSize: 20
                font.bold: true
            }

            Rectangle {
                id: cam_ind
                x: 226
                y: 154
                width: 40
                height: 40
                radius: width / 2
                border.color: "#000000"
                property bool camOn: false
                color: camOn ? "#3fae49" : "#7c7878"
            }

            Text {
                id: cam_fps
                x: 286
                y: 154
                width: 370
                height: 40
                text: cam_ind.camOn ? fpsValor.toFixed(0) + " fps" : qsTr("desligada")
                font.pixelSize: 18
                verticalAlignment: Text.AlignVCenter
                color: cam_ind.camOn ? "#000000" : "#7c7878"

                property real fpsValor: 0
            }
        }
    }

    Connections {
        target: backend

        function onPositionChanged(x, y, z) {
            posXedit.text = x.toFixed(2) + " mm"
            posYedit.text = y.toFixed(2) + " mm"
            posZedit.text = z.toFixed(2) + " mm"
        }

        function onJointsChanged(j1, j2, j3, j4, j5, j6) {
            j1Edit.text = j1.toFixed(1) + "°"
            j2Edit.text = j2.toFixed(1) + "°"
            j3Edit.text = j3.toFixed(1) + "°"
            j4Edit.text = j4.toFixed(1) + "°"
            j5Edit.text = j5.toFixed(1) + "°"
            j6Edit.text = j6.toFixed(1) + "°"
        }

        function onStatusChanged(texto) {
            manip_status_txt.text = texto
            if (texto.indexOf("Erro") !== -1) {
                manip_ind.color = "#e74c3c"
            } else if (texto === "Pronto") {
                manip_ind.color = "#3fae49"
            } else {
                manip_ind.color = "#f39c12"
            }
        }

        function onCameraStatusChanged(ativa, fps) {
            cam_ind.camOn = ativa
            cam_fps.fpsValor = fps
        }
    }

    Component.onCompleted: {
        if (typeof backend !== "undefined" && backend.syncRobotState) {
            backend.syncRobotState()
        }
    }
}
