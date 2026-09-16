import os

from backend.camera.camera_manager import CameraManager
from backend.camera.detection_thread import DetectionThread
from backend.robot.robot_thread import RobotActionThread
from backend.calibration.vision_to_robot import VisionToRobot

from yolo.yolo import YOLODetector

# arquivos do projeto do gemeo digital (colocados na raiz do projeto)
from serial_driver import SerialDriver
from unity_client import UnityClient
from robot_control import RobotController
from ventosa_control import VentosaController

CALIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "backend", "calibration", "dados"
)

INTRINSIC_PATH = os.path.join(CALIB_DIR, "calibracao_intrinseca.npz")
HANDEYE_PATH = os.path.join(CALIB_DIR, "calibracao_mao_olho.npz")

Z_CAMERA_MM = 350.0 #< --- aqui eu preciso da informação da altura em mm


class ApplicationController:

    def __init__(self, backend):

        self.backend = backend

        # --- Camera / deteccao ---

        self.camera = CameraManager()

        # o modelo e carregado uma unica vez, na inicializacao,
        # para nao pagar o custo de carregar os pesos a cada clique
        self.detector = YOLODetector()

        self.detection_thread = None

        self.vision_to_robot = None

        try:
            self.vision_to_robot = VisionToRobot(INTRINSIC_PATH, HANDEYE_PATH)
            print("Calibração pixel -> mm carregada com sucesso")

        except FileNotFoundError as e:
            print("Calibração pixel -> mm ainda não disponível:", e)



        # --- Manipulador / gemeo digital ---

        # ajuste a porta em serial_driver.py (Raspberry Pi usa algo como
        # '/dev/ttyUSB0', nao 'COM3') e o host/porta em unity_client.py
        self.serial = SerialDriver()
        self.unity = UnityClient()

        # efetuador tipo ventosa (bomba + valvula 24V DC via GPIO).
        # ajuste os pinos e o tempo de vacuo em ventosa_control.py
        self.ventosa = VentosaController()

        self.robot = RobotController(self.serial, self.unity, self.ventosa)

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

        self._pose_na_captura = (self.robot.Ri.copy(), self.robot.P0.copy())

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

        R_flange_base, t_flange_base = self._pose_na_captura

        for d in detections:

            self.backend.objectDetected.emit(d["class"])
 
            log = f"Detectado: {d['class']} ({d['confidence']:.2f})"
 
            if self.vision_to_robot is not None:
 
                x1, y1, x2, y2 = d["bbox"]
                u = (x1 + x2) / 2.0
                v = (y1 + y2) / 2.0
 
                vetor_mm = self.vision_to_robot.vetor_para_deteccao(
                    u, v, Z_CAMERA_MM, R_flange_base, t_flange_base
                )
 
                d["vetor_mm"] = vetor_mm.tolist()
 
                log += (
                    f" -> X={vetor_mm[0]:.1f} Y={vetor_mm[1]:.1f} "
                    f"Z={vetor_mm[2]:.1f} mm"
                )
            else:
                log += " (calibracao pixel->mm nao disponivel)"
 
            self.backend.addLog(log)

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

    def manipulate_ventosa(self):

        print("Manipulando objeto com a ventosa")

        if self.robot_thread and self.robot_thread.isRunning():
            self.backend.addLog("Ja existe um movimento em andamento")
            return

        self.backend.updateStatus("Executando rotina: ventosa")
        self.backend.addLog("Rotina ventosa iniciada")

        self._executar_no_robo(self.robot.rotina_ventosa)

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
        
        print("Calibração solicitada")

        if self.robot_thread and self.robot_thread.isRunning():
            self.backend.addLog("Já existe um movimento em andamento")
            return

        self.backend.updateStatus("Iniciando calibração")
        self.backend.addLog("Iniciando rotina de calibração")

        self._executar_no_robo(self._rodar_captura_calibracao)

    def _rodar_captura_calibracao(self):
        """Abre a camera, roda a rotina do seu parceiro (que espera um
        cv2.VideoCapture ja aberto) e garante o fechamento no final,
        mesmo se a rotina lancar uma excecao no meio do caminho."""
 
        if not self.camera.open():
            raise RuntimeError("Nao foi possivel abrir a camera")
 
        try:
            self.robot.rotina_captura_calibracao(self.camera.cap)
        finally:
            self.camera.close()
        

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

        # a rotina pode ter sido interrompida no meio da sucao —
        # garante que a bomba/valvula nao fiquem ligadas indefinidamente
        self.ventosa.desligar_tudo()
