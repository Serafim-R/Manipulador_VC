import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: manualPopup

    width: 300
    height: 280
    modal: true
    focus: true
    anchors.centerIn: parent
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        color: "#2b2b2b"
        radius: 8
        border.color: "#555555"
        border.width: 1
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Label {
            text: "Movimentacao manual"
            font.bold: true
            font.pixelSize: 16
            color: "white"
        }

        GridLayout {
            columns: 2
            columnSpacing: 10
            rowSpacing: 10
            Layout.fillWidth: true

            Label { text: "X:"; color: "white" }
            TextField {
                id: fieldX
                Layout.fillWidth: true
                placeholderText: "0.0"
                validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }

            Label { text: "Y:"; color: "white" }
            TextField {
                id: fieldY
                Layout.fillWidth: true
                placeholderText: "0.0"
                validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }

            Label { text: "Z:"; color: "white" }
            TextField {
                id: fieldZ
                Layout.fillWidth: true
                placeholderText: "0.0"
                validator: DoubleValidator { notation: DoubleValidator.StandardNotation }
                inputMethodHints: Qt.ImhFormattedNumbersOnly
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
                text: "Cancelar"
                onClicked: manualPopup.close()
            }

            Button {
                text: "Enviar"
                highlighted: true
                onClicked: {
                    if (fieldX.text.length === 0 || fieldY.text.length === 0 || fieldZ.text.length === 0) {
                        errorLabel.text = "Preencha todas as coordenadas"
                        return
                    }

                    var x = parseFloat(fieldX.text)
                    var y = parseFloat(fieldY.text)
                    var z = parseFloat(fieldZ.text)

                    if (isNaN(x) || isNaN(y) || isNaN(z)) {
                        errorLabel.text = "Coordenadas invalidas"
                        return
                    }

                    errorLabel.text = ""
                    backend.manualMove(x, y, z)
                    manualPopup.close()
                }
            }
        }
    }

    onOpened: {
        fieldX.text = ""
        fieldY.text = ""
        fieldZ.text = ""
        errorLabel.text = ""
        fieldX.forceActiveFocus()
    }
}
