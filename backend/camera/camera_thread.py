import cv2

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class CameraThread(QThread):

    frameCaptured = Signal(QImage)

    def __init__(self, camera):
        super().__init__()

        self.camera = camera
        self.running = False

    def run(self):

        self.running = True

        while self.running:

            frame = self.camera.read()

            if frame is None:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            h, w, ch = rgb.shape

            bytes_per_line = ch * w

            image = QImage(
                rgb.data,
                w,
                h,
                bytes_per_line,
                QImage.Format_RGB888
            ).copy()

            self.frameCaptured.emit(image)

    def stop(self):

        self.running = False
        self.wait()