from PySide6.QtCore import QObject, Signal, Slot

from backend.app_controller import ApplicationController
from PySide6.QtGui import QImage


class Backend(QObject):

    #========================================
    # Sinais enviados ao QML
    #========================================

    positionChanged = Signal(float, float, float)

    angleChanged = Signal(float, float, float)

    statusChanged = Signal(str)

    logMessage = Signal(str)

    objectDetected = Signal(str)

    cameraFrameChanged = Signal(QImage)
    #========================================

    def __init__(self):
    
            super().__init__()
    
            self.controller = ApplicationController(self)
            self.provider = None

    
    @Slot()
    def home(self):

        self.controller.home()


    @Slot()
    def detect(self):

        self.controller.detect()


    @Slot()
    def calibrate(self):

        self.controller.calibrate()


    @Slot()
    def manipulate(self):

        self.controller.manipulate()


    @Slot(float, float, float)
    def manualMove(self, x, y, z):

        self.controller.manualMove(x, y, z)


    def updateFrame(self, image):

        print("Backend recebeu frame")
        
        if self.provider:
             self.provider.updateImage(image)

        self.cameraFrameChanged.emit(image)

    def updateStatus(self, texto):
         self.statusChanged.emit(texto)
    def addLog(self, texto):
         self.logMessage.emit(texto)

    def setImageProvider(self, provider):
        self.provider = provider
