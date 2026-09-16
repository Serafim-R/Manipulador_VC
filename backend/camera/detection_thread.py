import cv2

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


class DetectionThread(QThread):
    """
    Thread de execucao unica (nao fica em loop): abre a camera, captura
    UM frame, opcionalmente desdistorce (calibracao da etapa 1), roda a
    deteccao do YOLO nesse frame e emite o resultado.
    """

    frameCaptured = Signal(QImage)
    detectionsReady = Signal(list)
    errorOccurred = Signal(str)

    # quantos frames "descartar" antes de capturar o frame valido,
    # para dar tempo da auto-exposicao/foco da camera estabilizar
    WARMUP_FRAMES = 5

    def __init__(self, camera, detector, vision_to_robot=None):
        super().__init__()

        self.camera = camera
        self.detector = detector

        # opcional: se fornecido, o frame e desdistorcido antes da YOLO
        # (usa a calibracao intrinseca da etapa 1) e o frame ja
        # desdistorcido fica acessivel em self.last_frame_bgr, para o
        # app_controller converter pixel -> mm depois
        self.vision_to_robot = vision_to_robot
        self.last_frame_bgr = None

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

        if self.vision_to_robot is not None:
            frame = self.vision_to_robot.undistort_frame(frame)

        self.last_frame_bgr = frame

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
