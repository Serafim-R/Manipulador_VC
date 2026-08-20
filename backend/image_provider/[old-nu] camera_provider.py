from PySide6.QtCore import QMutex
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtGui import QImage


class CameraProvider(QQuickImageProvider):

    def __init__(self):
        super().__init__(QQuickImageProvider.Image)

        self._mutex = QMutex()
        self._image = QImage()

    def updateImage(self, image):

        print("Provider recebeu imagem:",
            image.width(),
            image.height())
        # self.image = image
        self._mutex.lock()
        self._image = image.copy()
        self._mutex.unlock()

    def requestImage(self, image_id, size, requestedSize):

        self._mutex.lock()
        img = self._image.copy()
        self._mutex.unlock()

        print("\n============QML pediu imagem============\n")

        # return img, img.size()
        return img