from backend.camera.camera_manager import CameraManager
from backend.camera.detection_thread import DetectionThread

from yolo.yolo import YOLODetector


class ApplicationController:

    def __init__(self, backend):

        self.backend = backend

        # self.robot = RobotController()

        self.camera = CameraManager()

        # o modelo e carregado uma unica vez, na inicializacao,
        # para nao pagar o custo de carregar os pesos a cada clique
        self.detector = YOLODetector()

        self.detection_thread = None

        # self.calibration = Calibration()

    def home(self):

        print("HOME")

        self.backend.updateStatus("Movendo para HOME")

        self.backend.addLog("HOME acionado")

    def detect(self):

        if self.detection_thread and self.detection_thread.isRunning():
            print("Deteccao ja em andamento, ignorando novo clique")
            self.backend.addLog("Deteccao ja em andamento")
            return

        print("1 - Entrou em detect()")

        self.backend.statusChanged.emit("Capturando frame...")

        self.detection_thread = DetectionThread(self.camera, self.detector)

        self.detection_thread.frameCaptured.connect(self.backend.updateFrame)
        self.detection_thread.detectionsReady.connect(self._on_detections)
        self.detection_thread.errorOccurred.connect(self._on_error)
        self.detection_thread.finished.connect(self._on_finished)

        self.detection_thread.start()

        print("2 - DetectionThread iniciada")

    def _on_detections(self, detections):

        print("Deteccoes:", detections)

        self.backend.updateStatus(f"{len(detections)} objeto(s) detectado(s)")

        if not detections:
            self.backend.addLog("Nenhum objeto detectado")
            return

        for d in detections:
            self.backend.objectDetected.emit(d["class"])
            self.backend.addLog(
                f"Detectado: {d['class']} ({d['confidence']:.2f})"
            )

    def _on_error(self, message):

        print("Erro na deteccao:", message)

        self.backend.updateStatus("Erro na deteccao")
        self.backend.addLog(message)

    def _on_finished(self):

        self.backend.addLog("Deteccao finalizada")

    def manipulate(self):

        print("Manipulando objeto")

    def manualMove(self, x, y, z):

        print(f"Movimento manual solicitado: x={x}, y={y}, z={z}")

        self.backend.updateStatus(
            f"Movendo para X={x:.2f} Y={y:.2f} Z={z:.2f}"
        )
        self.backend.addLog(
            f"Movimento manual: ({x:.2f}, {y:.2f}, {z:.2f})"
        )

        # TODO: chamar aqui o algoritmo real de movimentacao do manipulador
        # self.robot.move_to(x, y, z)

    def calibrate(self):

        print("Calibrando")
