from backend.camera.camera_manager import CameraManager

class ApplicationController:

    def __init__(self, backend):

        self.backend = backend

        # self.robot = RobotController()

        self.camera = CameraManager()

        self.thread = None

        # self.detector = YOLODetector()

        # self.calibration = Calibration()

    def home(self):

        print("HOME")

        self.backend.updateStatus("Movendo para HOME")

        self.backend.addLog("HOME acionado")

    def detect(self):

        # print("Executando YOLO")
        print('1 - Entrou em detect()')

        self.backend.statusChanged.emit('Iniciando câmera...')

        print('2 - Criando Thread')

        self.thread = self.camera.start()

        print('3 - Thread =', self.thread)

        if self.thread:
            print('4 - Conectanto sinal')

            self.thread.frameCaptured.connect(self.backend.updateFrame)

            print('5 - Iniciando Thread')

            self.thread.start()

            print('6 - Thread Iniciada')
        else:
            print("Erro: CameraManager.start() retornou None")

        self.backend.updateStatus("Detectando objetos...")
        self.backend.addLog("Reconhecimento acionado")

    def manipulate(self):

        print("Manipulando objeto")

    def calibrate(self):

        print("Calibrando")

    