import sys
import os

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from backend.image_provider.camera_provider import CameraProvider

from backend.backend import Backend


def main():

    app = QGuiApplication(sys.argv)

    engine = QQmlApplicationEngine()

    backend = Backend()

    provider = CameraProvider()

    backend.setImageProvider(provider)

    engine.rootContext().setContextProperty(
            "backend",
            backend
        )
    
    engine.addImageProvider(
        'camera',
        provider
    )

    print("Provider registrado")

    project_path = os.path.dirname(os.path.abspath(__file__))

    engine.addImportPath(project_path)

    print(engine.importPathList())
    qml_file = os.path.join(project_path, "qml_F", "main.qml")
    # engine.load("qml_E/Manipulador_IAContent/main.qml")

    print("Carregando QML")

    engine.load(qml_file)

    if not engine.rootObjects():
        print('Erro: nenhum objeto QML carregado')
        sys.exit(-1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()