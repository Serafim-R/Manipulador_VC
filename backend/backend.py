import time

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from backend.app_controller import ApplicationController


class Backend(QObject):

    #========================================
    # Sinais enviados ao QML
    #========================================

    positionChanged = Signal(float, float, float)

    angleChanged = Signal(float, float, float)

    jointsChanged = Signal(float, float, float, float, float, float)

    statusChanged = Signal(str)

    logMessage = Signal(str)

    objectDetected = Signal(str)

    cameraFrameChanged = Signal(QImage)

    # (camera ativa?, fps medido)
    cameraStatusChanged = Signal(bool, float)
    #========================================

    # por quantos segundos o frame anotado pelo YOLO segura o preview,
    # senao ele seria sobrescrito pelo proximo frame do stream
    HOLD_ANOTACAO_S = 3.0

    def __init__(self):

            super().__init__()

            # o Backend nao possui camera: quem cria e opera a CamThread e o
            # ApplicationController, que e o unico dono do dispositivo
            self.controller = ApplicationController(self)

            self._segurar_ate = 0.0


    #========================================
    # Camera
    #========================================

    @Slot()
    def startCamera(self):

        self.controller.start_camera()
        self.controller.publicar_estado_robo()


    @Slot()
    def stopCamera(self):

        self.controller.stop_camera()


    @Slot(QImage)
    def updateFrame(self, image):

        if time.monotonic() < self._segurar_ate:
            return

        self.cameraFrameChanged.emit(image)


    def showAnnotated(self, image):
        """Exibe o frame anotado do YOLO e o segura por alguns segundos."""

        self._segurar_ate = 0.0

        self.cameraFrameChanged.emit(image)

        self._segurar_ate = time.monotonic() + self.HOLD_ANOTACAO_S


    def updateCameraStatus(self, ativa, fps):

        self.cameraStatusChanged.emit(ativa, fps)


    #========================================
    # Manipulador
    #========================================

    @Slot()
    def home(self):

        self.controller.home()


    @Slot()
    def detect(self):

        self.controller.reconhecer()


    @Slot()
    def calibrate(self):

        self.controller.calibrate()


    @Slot()
    def manipulate(self):

        self.controller.manipulate()


    @Slot(float, float, float)
    def manualMove(self, x, y, z):

        self.controller.manualMove(x, y, z)


    def updateStatus(self, texto):
         self.statusChanged.emit(texto)

    def addLog(self, texto):
         self.logMessage.emit(texto)

    def updatePosition(self, x, y, z):
         self.positionChanged.emit(float(x), float(y), float(z))

    def updateJoints(self, j1, j2, j3, j4, j5, j6):
         self.jointsChanged.emit(float(j1), float(j2), float(j3), float(j4), float(j5), float(j6))
         # Mantém compatibilidade com angleChanged para os 3 ângulos finais do punho (j4, j5, j6)
         self.angleChanged.emit(float(j4), float(j5), float(j6))

    @Slot()
    def syncRobotState(self):
         self.controller.publicar_estado_robo()
