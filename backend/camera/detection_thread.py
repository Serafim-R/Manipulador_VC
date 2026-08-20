import cv2

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class DetectionThread(QThread):
    """
    Thread de execucao unica (nao fica em loop): abre a camera, captura
    UM frame, roda a deteccao do YOLO nesse frame e emite o resultado.
    """

    frameCaptured = Signal(QImage)
    detectionsReady = Signal(list)
    errorOccurred = Signal(str)

    # quantos frames "descartar" antes de capturar o frame valido,
    # para dar tempo da auto-exposicao/foco da camera estabilizar
    WARMUP_FRAMES = 5

    def __init__(self, camera, detector):
        super().__init__()

        self.camera = camera
        self.detector = detector

    def run(self):

        if not self.camera.open():
            self.errorOccurred.emit("Nao foi possivel abrir a camera")
            return

        frame = None

        try:
            for _ in range(self.WARMUP_FRAMES):
                frame = self.camera.read()

        finally:
            self.camera.close()

        if frame is None:
            self.errorOccurred.emit("Nao foi possivel capturar um frame da camera")
            return

        print("Frame capturado, rodando YOLO...")

        try:
            annotated, detections = self.detector.detect(frame)
        except Exception as e:
            self.errorOccurred.emit(f"Erro na deteccao YOLO: {e}")
            return

        rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

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
        self.detectionsReady.emit(detections)
