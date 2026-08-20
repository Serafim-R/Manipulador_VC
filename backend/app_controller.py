from backend.camera.camera_manager import CameraManager
from backend.camera.detection_thread import DetectionThread
from backend.robot.robot_thread import RobotActionThread

from yolo.yolo import YOLODetector

# arquivos do projeto do gemeo digital (colocados na raiz do projeto)
from serial_driver import SerialDriver
from unity_client import UnityClient
from robot_control import RobotController


class ApplicationController:

    def __init__(self, backend):

        self.backend = backend

        # --- Camera / deteccao ---

        self.camera = CameraManager()

        # o modelo e carregado uma unica vez, na inicializacao,
        # para nao pagar o custo de carregar os pesos a cada clique
        self.detector = YOLODetector()

        self.detection_thread = None

        # --- Manipulador / gemeo digital ---

        # ajuste a porta em serial_driver.py (Raspberry Pi usa algo como
        # '/dev/ttyUSB0', nao 'COM3') e o host/porta em unity_client.py
        self.serial = SerialDriver()
        self.unity = UnityClient()
        self.robot = RobotController(self.serial, self.unity)

        # configuracao inicial do GRBL, igual ao main.py do projeto do gemeo digital
        self.serial.send_settings()
        self.serial.send("G90")
        self.serial.send("F800")
        self.robot.recuperar_do_log()
        self.serial.reset_log()

        self.robot_thread = None

    # ------------------------------------------------------------------
    # Camera / YOLO
    # ------------------------------------------------------------------

    def detect(self):

        if self.detection_thread and self.detection_thread.isRunning():
            print("Deteccao ja em andamento, ignorando novo clique")
            self.backend.addLog("Deteccao ja em andamento")
            return

        if self.robot_thread and self.robot_thread.isRunning():
            print("Manipulador ocupado, ignorando novo clique")
            self.backend.addLog("Ja existe um movimento em andamento")
            return

        print("1 - Posicionando o manipulador para deteccao")

        self.backend.statusChanged.emit("Posicionando para deteccao...")

        # primeiro move o braco ate o ponto de onde a camera enxerga a mesa;
        # so quando o movimento terminar (rotina_deteccao) e que a captura
        # + deteccao YOLO sao disparadas, em _on_posicionamento_ok
        self.robot_thread = RobotActionThread(self.robot.rotina_deteccao)

        self.robot_thread.finishedOk.connect(self._on_posicionamento_ok)
        self.robot_thread.errorOccurred.connect(self._on_posicionamento_error)

        self.robot_thread.start()

    def _on_posicionamento_ok(self, message):

        print("2 - Posicionamento concluido, iniciando captura")

        self.backend.addLog("Posicionamento concluido")

        self._iniciar_captura_deteccao()

    def _on_posicionamento_error(self, message):

        print("Erro no posicionamento:", message)

        self.backend.updateStatus("Erro no posicionamento")
        self.backend.addLog(message)

    def _iniciar_captura_deteccao(self):

        self.backend.statusChanged.emit("Capturando frame...")

        self.detection_thread = DetectionThread(self.camera, self.detector)

        self.detection_thread.frameCaptured.connect(self.backend.updateFrame)
        self.detection_thread.detectionsReady.connect(self._on_detections)
        self.detection_thread.errorOccurred.connect(self._on_detection_error)
        self.detection_thread.finished.connect(self._on_detection_finished)

        self.detection_thread.start()

        print("3 - DetectionThread iniciada")

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

    def _on_detection_error(self, message):

        print("Erro na deteccao:", message)

        self.backend.updateStatus("Erro na deteccao")
        self.backend.addLog(message)

    def _on_detection_finished(self):

        self.backend.addLog("Deteccao finalizada")

    # ------------------------------------------------------------------
    # Manipulador
    # ------------------------------------------------------------------

    def home(self):

        print("HOME")

        if self.robot_thread and self.robot_thread.isRunning():
            self.backend.addLog("Ja existe um movimento em andamento")
            return

        self.backend.updateStatus("Movendo para HOME")
        self.backend.addLog("HOME acionado")

        self._executar_no_robo(self.robot.home)

    def manipulate(self):

        print("Manipulando objeto")

        if self.robot_thread and self.robot_thread.isRunning():
            self.backend.addLog("Ja existe um movimento em andamento")
            return

        self.backend.updateStatus("Executando rotina: lapis / suporte")
        self.backend.addLog("Rotina lapis/suporte iniciada")

        self._executar_no_robo(self.robot.rotina_lapis_suporte)

    def manualMove(self, x, y, z):

        print(f"Movimento manual solicitado: x={x}, y={y}, z={z}")

        if self.robot_thread and self.robot_thread.isRunning():
            self.backend.addLog("Ja existe um movimento em andamento")
            return

        self.backend.updateStatus(
            f"Movendo para X={x:.2f} Y={y:.2f} Z={z:.2f}"
        )
        self.backend.addLog(
            f"Movimento manual: ({x:.2f}, {y:.2f}, {z:.2f})"
        )

        self._executar_no_robo(self.robot.mover_para, x, y, z)

    def calibrate(self):

        print("Calibrando")

    def _executar_no_robo(self, action, *args):

        self.robot_thread = RobotActionThread(action, *args)

        self.robot_thread.finishedOk.connect(self._on_robot_ok)
        self.robot_thread.errorOccurred.connect(self._on_robot_error)

        self.robot_thread.start()

    def _on_robot_ok(self, message):

        self.backend.updateStatus("Pronto")
        self.backend.addLog(message)

    def _on_robot_error(self, message):

        print("Erro no robo:", message)

        self.backend.updateStatus("Erro no movimento")
        self.backend.addLog(message)
