import cv2


class CameraManager:
    """
    Dono do dispositivo de video. Nao abre nem fecha nada sozinho:
    quem controla o ciclo de vida e a CamThread, que e a unica a
    chamar open()/read()/close() enquanto o stream esta ativo.
    """

    DEVICE_INDEX = 0

    # MJPG e o unico formato que entrega 640x480 @30 nesta webcam sem
    # saturar o barramento USB (v4l2-ctl --list-formats-ext confirma
    # YUYV e MJPG; em YUYV o driver derruba a taxa)
    FOURCC = "MJPG"

    # resolucao/fps modestos: o Raspberry Pi precisa converter cada frame
    # BGR -> RGB -> QImage e redesenhar no QQuickPaintedItem via CPU
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480
    FPS = 30

    def __init__(self):

        self.cap = None

    def open(self):

        # backend explicito: sem isso o OpenCV pode escolher GStreamer
        self.cap = cv2.VideoCapture(self.DEVICE_INDEX, cv2.CAP_V4L2)

        if not self.cap.isOpened():
            print("Camera aberta: False")
            return False

        # buffer de 1 frame: sem isso o V4L2 mantem uma fila FIFO de 4-5
        # frames e cada read() devolve um frame atrasado
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # o fourcc precisa ser definido antes da resolucao
        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*self.FOURCC)
        )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, self.FPS)

        print(
            "Camera aberta: {:.0f}x{:.0f} @ {:.0f} fps".format(
                self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                self.cap.get(cv2.CAP_PROP_FPS),
            )
        )

        return True

    def read(self):
        """Devolve o frame BGR mais recente, ou None. Nunca reabre o device."""

        if self.cap is None:
            return None

        ok, frame = self.cap.read()

        if ok:
            return frame

        return None

    def close(self):

        if self.cap is not None:

            self.cap.release()
            self.cap = None

    def capture_frame(self, warmup_frames=5):
        """
        Ciclo pontual abre -> descarta warmup -> captura -> fecha.

        Usado apenas quando nao ha stream rodando (ex.: robot_control.py
        executado de forma avulsa, fora do app Qt). Dentro do app quem
        atende essa chamada e CamThread.capture_frame, que devolve um
        frame fresco sem fechar o dispositivo.
        """

        if not self.open():
            print("Erro: Nao foi possivel abrir a camera.")
            return None

        frame = None
        try:
            for _ in range(warmup_frames):
                frame = self.read()
            return frame
        finally:
            self.close()
