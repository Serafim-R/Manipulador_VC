import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: manualPopup

    // a altura acompanha o conteudo (aba ativa + bloco de foco)
    width: 380
    modal: true
    focus: true
    anchors.centerIn: parent
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 16

    background: Rectangle {
        color: "#2b2b2b"
        radius: 8
        border.color: "#555555"
        border.width: 1
    }

    // 0 = cartesiano (X, Y, Z), 1 = juntas (J1..J6)
    property int modo: tabs.currentIndex

    function lerNumeros(campos) {
        var valores = []
        for (var i = 0; i < campos.length; i++) {
            if (campos[i].length === 0)
                return null
            var v = parseFloat(campos[i])
            if (isNaN(v))
                return null
            valores.push(v)
        }
        return valores
    }

    function enviar() {
        if (modo === 0) {
            var p = lerNumeros([fieldX.text, fieldY.text, fieldZ.text])
            if (p === null) {
                errorLabel.text = "Preencha X, Y e Z com numeros validos"
                return
            }
            errorLabel.text = ""
            backend.manualMove(p[0], p[1], p[2])
        } else {
            var textos = []
            for (var i = 0; i < 6; i++)
                textos.push(jointRepeater.itemAt(i).valor)
            var j = lerNumeros(textos)
            if (j === null) {
                errorLabel.text = "Preencha as 6 juntas com numeros validos"
                return
            }
            errorLabel.text = ""
            backend.manualJoints(j[0], j[1], j[2], j[3], j[4], j[5])
        }
        manualPopup.close()
    }

    ColumnLayout {
        width: manualPopup.availableWidth
        spacing: 12

        Label {
            text: "Movimentacao manual"
            font.bold: true
            font.pixelSize: 16
            color: "white"
        }

        TabBar {
            id: tabs
            Layout.fillWidth: true

            TabButton { text: "Posicao (X, Y, Z)" }
            TabButton { text: "Juntas (J1-J6)" }
        }

        StackLayout {
            Layout.fillWidth: true
            currentIndex: tabs.currentIndex

            // ---------- Cartesiano ----------
            GridLayout {
                columns: 2
                columnSpacing: 10
                rowSpacing: 10

                Label { text: "X (mm):"; color: "white" }
                TextField {
                    id: fieldX
                    Layout.fillWidth: true
                    placeholderText: "0.0"
                    validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onAccepted: manualPopup.enviar()
                }

                Label { text: "Y (mm):"; color: "white" }
                TextField {
                    id: fieldY
                    Layout.fillWidth: true
                    placeholderText: "0.0"
                    validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onAccepted: manualPopup.enviar()
                }

                Label { text: "Z (mm):"; color: "white" }
                TextField {
                    id: fieldZ
                    Layout.fillWidth: true
                    placeholderText: "0.0"
                    validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    onAccepted: manualPopup.enviar()
                }
            }

            // ---------- Juntas ----------
            ColumnLayout {
                spacing: 6

                Label {
                    text: "Valores enviados direto ao GRBL. Depois disso, " +
                          "movimentos em X, Y, Z exigem HOME."
                    color: "#aaaaaa"
                    font.pixelSize: 11
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                GridLayout {
                    columns: 2
                    columnSpacing: 16
                    rowSpacing: 8
                    Layout.fillWidth: true

                    Repeater {
                        id: jointRepeater
                        model: 6

                        RowLayout {
                            property alias valor: jointField.text

                            Layout.fillWidth: true
                            spacing: 6

                            Label {
                                text: "J" + (index + 1) + ":"
                                color: "white"
                            }
                            TextField {
                                id: jointField
                                Layout.fillWidth: true
                                placeholderText: "0.0"
                                validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                                inputMethodHints: Qt.ImhFormattedNumbersOnly
                                onAccepted: manualPopup.enviar()
                            }
                        }
                    }
                }
            }
        }

        // ---------- Foco da camera ----------
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#555555"
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Foco da camera"
                color: "white"
                font.bold: true
            }
            Item { Layout.fillWidth: true }
            Label {
                text: focoSlider.value.toFixed(0)
                color: "white"
                font.pixelSize: 16
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Button {
                text: "-"
                implicitWidth: 36
                onClicked: { focoSlider.decrease(); focoTimer.restart() }
            }
            Slider {
                id: focoSlider
                Layout.fillWidth: true
                // escala da Logitech: 0-250, passo 5; maior = foca mais perto
                from: 0
                to: 250
                stepSize: 5
                snapMode: Slider.SnapAlways
                onMoved: focoTimer.restart()
            }
            Button {
                text: "+"
                implicitWidth: 36
                onClicked: { focoSlider.increase(); focoTimer.restart() }
            }
        }

        Label {
            text: "Vale ate reiniciar o app. Para manter, grave o valor em " +
                  "CameraManager.FOCO_FIXO e refaca as calibracoes."
            color: "#aaaaaa"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        // agrupa o arraste do slider: so manda o foco depois que ele para,
        // em vez de um comando V4L2 (e uma linha de log) por passo
        Timer {
            id: focoTimer
            interval: 200
            onTriggered: backend.setCameraFocus(Math.round(focoSlider.value))
        }

        // ---------- Correcao de posicao (pontos conhecidos) ----------
        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: "#555555"
        }

        Label {
            text: "Correcao de posicao"
            color: "white"
            font.bold: true
        }

        Label {
            text: "Reconhecer, HOME, leve a ponta ao centro de um objeto " +
                  "detectado (aba X, Y, Z) e registre. Quanto mais pontos " +
                  "espalhados pela mesa, melhor."
            color: "#aaaaaa"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        Label {
            id: correcaoLabel
            color: "#8fd18f"
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                text: "Registrar ponto"
                Layout.fillWidth: true
                onClicked: correcaoLabel.text = backend.registrarPontoCorrecao()
            }

            // dois cliques: apagar os pontos joga fora uma coleta inteira
            Button {
                id: limparButton
                property bool confirmando: false
                text: confirmando ? "Confirmar?" : "Limpar pontos"
                onClicked: {
                    if (!confirmando) {
                        confirmando = true
                        limparTimer.restart()
                        return
                    }
                    confirmando = false
                    correcaoLabel.text = backend.limparPontosCorrecao()
                }
            }

            Timer {
                id: limparTimer
                interval: 3000
                onTriggered: limparButton.confirmando = false
            }
        }

        Label {
            id: errorLabel
            color: "#ff6b6b"
            visible: text.length > 0
            text: ""
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Item { Layout.fillWidth: true }

            Button {
                text: "Fechar"
                onClicked: manualPopup.close()
            }

            Button {
                text: "Enviar"
                highlighted: true
                onClicked: manualPopup.enviar()
            }
        }
    }

    onOpened: {
        // preenche com o estado atual, para ajustar a partir de onde o
        // robo esta em vez de digitar tudo de novo
        var p = backend.currentPosition()
        fieldX.text = p[0].toFixed(1)
        fieldY.text = p[1].toFixed(1)
        fieldZ.text = p[2].toFixed(1)

        var j = backend.currentJoints()
        for (var i = 0; i < 6; i++)
            jointRepeater.itemAt(i).valor = j[i].toFixed(1)

        focoSlider.value = backend.cameraFocus()
        correcaoLabel.text = backend.resumoCorrecao()
        limparButton.confirmando = false
        errorLabel.text = ""

        if (modo === 0)
            fieldX.forceActiveFocus()
    }
}
