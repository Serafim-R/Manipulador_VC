import sys

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

app = QGuiApplication(sys.argv)

engine = QQmlApplicationEngine()

engine.loadData(b"""
import QtQuick
import QtQuick.Window

Window{
    visible: true
    width: 600
    height: 400

    Rectangle{
        anchors.fill: parent
        color: "red"
    }
}
""")

sys.exit(app.exec())