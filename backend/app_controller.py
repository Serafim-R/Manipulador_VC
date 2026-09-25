import os
import time

from backend.camera.camera_manager import CameraManager
from backend.camera.camera_thread import CamThread
from backend.camera.detection_thread import DetectionThread
from backend.robot.robot_thread import RobotActionThread
from backend.calibration.vision_to_robot import VisionToRobot

from backend.calibration.calibracao_intrinseca import calibrate_1
from backend.calibration.calibracao_mao_olho import calibrate_2
from ferramentas.limpar_fotos import limpar_imagens

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

# Altura da superficie onde os objetos estao apoiados, no frame de MUNDO
# (o mesmo frame que robot_control.mover_para() recebe). A mesa e z = 0 se o
# tabuleiro da calibracao estava apoiado nela.
#
# Nao e mais preciso "chutar" a distancia da camera ate o objeto: a conversao
# usa intersecao raio-plano, entao o unico dado fisico necessario e a ALTURA
# DA MESA. Meca com regua e ajuste aqui.
# (a calibracao mao-olho atual estima o tabuleiro em z ~ +21 mm neste frame)
Z_MESA_MUNDO = 0.0

# Altura de cada objeto, em mm, por classe da CNN. Serve para corrigir o
# paralaxe: o centro da bbox e o centroide visual do objeto (a ~meia altura),
# nao o ponto onde ele encosta na mesa. Sem isso o alvo sai deslocado para
# longe do eixo da camera — ~15 mm para um objeto de 50 mm na borda da imagem.
#
# MEDIR com paquimetro e preencher. Classe ausente usa ALTURA_PADRAO_MM.
ALTURA_OBJETOS_MM = {
    "Tampa-porca": 0.0,
    "base": 0.0,
    "sensor": 0.0,
}
ALTURA_PADRAO_MM = 0.0

# Pose fixa de observacao ("posicao de buscar"), no frame de MUNDO e em
# coordenadas da PONTA da ferramenta — e o que mover_para() espera.
# Daqui a camera precisa enxergar toda a regiao da mesa onde os objetos ficam.
# Ajuste para a sua bancada e confira com ferramentas/checar_pose_busca.py.
POSICAO_BUSCA = (-300.0, 210.0, 400.0)


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

        # thread unica de captura: nenhum outro ponto do projeto abre o
        # dispositivo enquanto ela estiver rodando. Recebe o frame BRUTO
        # (sem undistort), porque as fotos de calibracao precisam da
        # imagem original e o undistort e aplicado depois, por consumidor.
        self.camera_thread = CamThread(self.camera)

        self.camera_thread.frameCaptured.connect(self.backend.updateFrame)
        self.camera_thread.errorOccurred.connect(self._on_camera_error)
        self.camera_thread.cameraStats.connect(self.backend.updateCameraStatus)

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
        self.robot.callback_posicao = self._on_robot_step

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

    def start_camera(self):

        if not self.camera_thread.isRunning():
            self.camera_thread.start()

    def stop_camera(self):

        if self.camera_thread.isRunning():
            self.camera_thread.stop()

    def _on_camera_error(self, message):

        print("Erro na camera:", message)

        self.backend.updateStatus("Erro na câmera")
        self.backend.addLog(message)

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

        # Pose REAL do flange (cinematica direta dos angulos enviados). Ri/P0
        # nao servem aqui: guardam a pose pedida da PONTA, no frame de mundo,
        # enquanto a mao-olho trabalha com o FLANGE no frame da base.
        self._pose_na_captura = self.robot.pose_flange_atual()

        # consome o frame do stream em vez de disputar /dev/video0
        self.detection_thread = DetectionThread(self.camera_thread, self.detector)

        self.detection_thread.frameCaptured.connect(self.backend.showAnnotated)
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

        T_flange_base = self._pose_na_captura

        for d in detections:

            self.backend.objectDetected.emit(d["class"])

            log = f"Detectado: {d['class']} ({d['confidence']:.2f})"

            if self.vision_to_robot is None:
                log += " (calibracao pixel->mm nao disponivel)"

            elif T_flange_base is None:
                log += " (pose do robo desconhecida: mova para a posicao de busca antes)"

            else:
                try:
                    # (X, Y, Z) em mm no frame de MUNDO, ja pronto para
                    # entrar em robot_control.mover_para().
                    altura = ALTURA_OBJETOS_MM.get(d["class"], ALTURA_PADRAO_MM)

                    vetor_mm = self.vision_to_robot.deteccao_para_mundo(
                        d["bbox"],
                        T_flange_base,
                        z_plano_mundo=Z_MESA_MUNDO,
                        altura_objeto_mm=altura,
                    )

                    d["vetor_mm"] = vetor_mm.tolist()

                    # A camera enxerga mais mesa do que o braco alcanca, entao
                    # nem todo objeto detectado da para pegar. Marcar aqui
                    # evita mandar um alvo impossivel para a rotina de pega.
                    d["alcancavel"] = self.robot.alvo_alcancavel(*vetor_mm)

                    log += (
                        f" -> X={vetor_mm[0]:.1f} Y={vetor_mm[1]:.1f} "
                        f"Z={vetor_mm[2]:.1f} mm"
                    )

                    if not d["alcancavel"]:
                        log += " [FORA DE ALCANCE]"

                except ValueError as erro:
                    log += f" (conversao pixel->mm falhou: {erro})"

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

        # Se houver imagens na pasta, devem ser excluídas
        limpar_imagens()

        # a câmera continua transmitindo: a rotina pede à CamThread um frame
        # fresco em cada pose, sem fechar o dispositivo e sem congelar o
        # preview. CamThread.capture_frame tem a mesma assinatura que
        # CameraManager.capture_frame, então robot_control não muda.

        self.robot.rotina_captura_calibracao(1, camera=self.camera_thread)
        time.sleep(15)
        self.robot.rotina_captura_calibracao(2, camera=self.camera_thread)
        time.sleep(15)
        self.backend.addLog("Iniciando processamento das imagens")

        # Etapa 1: intrínseca (K, dist) a partir das fotos recém-capturadas.
        # Precisa rodar sempre, porque um .npz de outra resolução de câmera
        # estraga silenciosamente a etapa 2.
        calibrate_1()
        self.backend.addLog("Calibração intrínseca concluída")

        # Etapa 2: mão-olho (T_cam_flange). Usa as fotos de capturas/ junto
        # com o poses_calibracao.json que a rotina de captura acabou de gravar.
        calibrate_2()
        self.backend.addLog("Calibração mão-olho concluída")

        # Recarrega o pipeline pixel -> mm com a calibração nova; senão ele
        # continuaria usando a que foi lida na inicialização do app.
        try:
            self.vision_to_robot = VisionToRobot(INTRINSIC_PATH, HANDEYE_PATH)
            self.backend.addLog("Calibração pixel -> mm recarregada")
        except FileNotFoundError as e:
            self.backend.addLog(f"Falha ao recarregar calibração: {e}")

        self.backend.addLog("Etapa de processamento concluída")

    def reconhecer(self):
    
            if self.detection_thread and self.detection_thread.isRunning():
                self.set_status("Deteccao ja em andamento")
                return
            if not self.camera._cap or not self.camera._cap.isOpened():
                self.set_status("Camera indisponivel")
                return
    
            self.controller.enviar_juntas(-110, 0, -20, 0, -105, 0)
    
            time.sleep(15)
    
            self.camera._timer.stop()
            self.set_status("Detectando objetos...")
            self.log_text.append("Iniciando deteccao YOLO...")
    
            self.detection_thread = DetectionThread(self.camera._cap, self.detector)
            self.detection_thread.frame_ready.connect(self._on_frame_ready)
            self.detection_thread.detections_ready.connect(self._on_detections_ready)
            self.detection_thread.error_occurred.connect(self._on_detection_error)
            self.detection_thread.finished.connect(self._on_detection_finished)
            self.detection_thread.start()        

    def _executar_no_robo(self, action, *args):

        self.robot_thread = RobotActionThread(action, *args)

        self.robot_thread.finishedOk.connect(self._on_robot_ok)
        self.robot_thread.errorOccurred.connect(self._on_robot_error)

        self.robot_thread.start()

    def _on_robot_step(self, x, y, z, j1, j2, j3, j4, j5, j6):
        self.backend.updatePosition(x, y, z)
        self.backend.updateJoints(j1, j2, j3, j4, j5, j6)

    def publicar_estado_robo(self):
        if hasattr(self, 'robot') and self.robot:
            x, y, z = self.robot.posicao_mundo()
            self.backend.updatePosition(x, y, z)
            if self.robot.ultimos_angulos:
                self.backend.updateJoints(*self.robot.ultimos_angulos)

    def _on_robot_ok(self, message):

        self.backend.updateStatus("Pronto")
        self.backend.addLog(message)
        self.publicar_estado_robo()

    def _on_robot_error(self, message):

        print("Erro no robo:", message)

        self.backend.updateStatus("Erro no movimento")
        self.backend.addLog(message)
        self.publicar_estado_robo()

        # a rotina pode ter sido interrompida no meio da sucao —
        # garante que a bomba/valvula nao fiquem ligadas indefinidamente
        self.ventosa.desligar_tudo()
