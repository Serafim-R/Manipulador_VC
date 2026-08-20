from PySide6.QtQuick import QQuickPaintedItem
from PySide6.QtGui import QImage
from PySide6.QtCore import Slot, QMutex


class CameraItem(QQuickPaintedItem):
    """
    Item QML customizado que desenha o frame mais recente da camera
    diretamente via QPainter, sem passar por QQuickImageProvider.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._image = QImage()
        self._mutex = QMutex()

    def paint(self, painter):

        self._mutex.lock()
        img = self._image
        self._mutex.unlock()

        if not img.isNull():
            painter.drawImage(self.boundingRect(), img)

    @Slot(QImage)
    def updateImage(self, image):

        print("CameraItem recebeu frame para desenhar")

        self._mutex.lock()
        self._image = image
        self._mutex.unlock()

        # agenda um novo paint() na thread da GUI - seguro chamar
        # de dentro de um slot conectado a um sinal cross-thread,
        # pois o Qt ja entrega essa chamada na thread da GUI
        self.update()
