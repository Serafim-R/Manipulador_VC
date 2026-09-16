import sys
import os

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from backend.image_provider.camera_item import CameraItem

from backend.backend import Backend


def main():

    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()

    backend = Backend()

    # registra o CameraItem como um tipo QML disponivel via
    # "import CameraModule 1.0"
    qmlRegisterType(CameraItem, "CameraModule", 1, 0, "CameraItem")

    engine.rootContext().setContextProperty(
            "backend",
            backend
        )

    project_path = os.path.dirname(os.path.abspath(__file__))

    engine.addImportPath(project_path)

    print(engine.importPathList())
    qml_file = os.path.join(project_path, "qml_F", "main.qml")

    print("Carregando QML")

    engine.load(qml_file)

    if not engine.rootObjects():
        print('Erro: nenhum objeto QML carregado')
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
