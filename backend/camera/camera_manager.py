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

    # Foco FIXO. A Logitech sai de fabrica com autofoco continuo, e cada
    # refoco muda a distancia focal da lente - ou seja, invalida o K da
    # calibracao intrinseca e, por tabela, a mao-olho e a conversao
    # pixel -> mm. O foco precisa ser o MESMO nas fotos de calibracao e
    # na deteccao; se mudar este valor, refaca as duas calibracoes.
    #
    # Escala do driver: 0-250, passo 5; valores maiores focam mais perto.
    # Para achar o valor: robo na POSICAO_BUSCA e teste com
    #   v4l2-ctl -d /dev/video0 -c focus_automatic_continuous=0 -c focus_absolute=30
    # ate a mesa ficar nitida.
    FOCO_FIXO = 5

    def __init__(self):

        self.cap = None

        # foco em uso. Comeca em FOCO_FIXO e so muda pelo ajuste manual
        # (popup de movimento manual), que serve para achar o valor certo.
        # Reiniciar o app volta para FOCO_FIXO.
        self.foco = self.FOCO_FIXO

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

        self._aplicar_foco()

        print(
            "Camera aberta: {:.0f}x{:.0f} @ {:.0f} fps, "
            "autofoco={:.0f}, foco={:.0f}".format(
                self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                self.cap.get(cv2.CAP_PROP_FPS),
                self.cap.get(cv2.CAP_PROP_AUTOFOCUS),
                self.cap.get(cv2.CAP_PROP_FOCUS),
            )
        )

        return True

    def _aplicar_foco(self):

        # o autofoco tem de ser desligado ANTES: com ele ligado o driver
        # marca focus_absolute como inativo e ignora o valor
        self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        self.cap.set(cv2.CAP_PROP_FOCUS, self.foco)

    def set_focus(self, valor):
        """Muda o foco. Com a camera aberta aplica na hora; fechada, vale
        para o proximo open(). Devolve o foco que o driver reporta.

        Chame da mesma thread que faz o read() (a CamThread cuida disso).
        """

        self.foco = int(valor)

        if self.cap is None:
            return self.foco

        self._aplicar_foco()

        return int(self.cap.get(cv2.CAP_PROP_FOCUS))

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
