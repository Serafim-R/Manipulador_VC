import time

import cv2

from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition
from PySide6.QtGui import QImage


class CamThread(QThread):
    """
    Thread de captura continua. E a UNICA a ler o dispositivo de video.

    Alem de empurrar frames para a GUI (frameCaptured), guarda sempre o
    ultimo frame BGR para quem precisa de uma imagem pontual (calibracao,
    YOLO) sem disputar /dev/video0 com o stream.
    """

    frameCaptured = Signal(QImage)
    errorOccurred = Signal(str)

    # (camera ativa?, fps medido)
    cameraStats = Signal(bool, float)

    # a leitura roda no ritmo do sensor; o limite vale so para a emissao
    # a GUI, que custa uma conversao de cor + repintura no Pi
    UI_FPS_LIMIT = 15

    # leituras falhas consecutivas toleradas antes de desistir
    MAX_FALHAS = 30

    def __init__(self, camera, vision_to_robot=None):
        super().__init__()

        self.camera = camera

        # opcional: se fornecido, o frame e desdistorcido (calibracao
        # intrinseca da etapa 1) antes de ser publicado
        self.vision_to_robot = vision_to_robot

        self._running = False

        self._mutex = QMutex()
        self._cond = QWaitCondition()

        self._last_frame = None
        self._seq = 0

    # ------------------------------------------------------------------
    # Loop de captura
    # ------------------------------------------------------------------

    def run(self):

        if not self.camera.open():
            self.errorOccurred.emit("Nao foi possivel abrir a camera")
            self.cameraStats.emit(False, 0.0)
            return

        self._running = True

        # a margem de 10% evita perder um frame por arredondamento: a 30 FPS
        # o intervalo medido cai em 0.0666s contra um alvo de 0.0667s, e sem
        # a folga o throttle entregaria 10 FPS em vez de 15
        intervalo_min = (1.0 / self.UI_FPS_LIMIT) * 0.9

        ultimo_emit = 0.0
        stats_t0 = time.monotonic()
        stats_frames = 0
        falhas = 0

        print("Stream da camera iniciado")

        try:
            while self._running:

                frame = self.camera.read()

                if frame is None:

                    falhas += 1

                    if falhas >= self.MAX_FALHAS:
                        self.errorOccurred.emit(
                            "Falha ao capturar quadro da camera"
                        )
                        break

                    self.msleep(10)
                    continue

                falhas = 0

                if self.vision_to_robot is not None:
                    frame = self.vision_to_robot.undistort_frame(frame)

                # publica para os consumidores sincronos e acorda quem
                # estiver esperando por um frame fresco
                self._mutex.lock()
                self._last_frame = frame
                self._seq += 1
                self._cond.wakeAll()
                self._mutex.unlock()

                agora = time.monotonic()
                stats_frames += 1

                if agora - ultimo_emit >= intervalo_min:
                    ultimo_emit = agora
                    self.frameCaptured.emit(self._to_qimage(frame))

                decorrido = agora - stats_t0

                if decorrido >= 1.0:
                    self.cameraStats.emit(True, stats_frames / decorrido)
                    stats_t0 = agora
                    stats_frames = 0

        finally:

            self._mutex.lock()
            self._running = False
            self._cond.wakeAll()
            self._mutex.unlock()

            self.camera.close()

            self.cameraStats.emit(False, 0.0)

            print("Stream da camera encerrado")

    def stop(self):
        """Encerra o loop e libera o dispositivo. Chamado da thread da GUI."""

        self._mutex.lock()
        self._running = False
        self._cond.wakeAll()
        self._mutex.unlock()

        self.wait(5000)

    # ------------------------------------------------------------------
    # Acesso ao frame para consumidores sincronos
    # ------------------------------------------------------------------

    def latest_frame(self):
        """Devolve (copia do ultimo frame BGR, numero de sequencia)."""

        self._mutex.lock()
        try:
            if self._last_frame is None:
                return None, 0

            return self._last_frame.copy(), self._seq
        finally:
            self._mutex.unlock()

    def capture_frame(self, warmup_frames=5, timeout_ms=4000):
        """
        Descarta os proximos `warmup_frames` quadros e devolve o seguinte.

        Mesma assinatura e semantica de CameraManager.capture_frame, mas
        sem abrir nem fechar o dispositivo: como o loop drena o buffer do
        V4L2 continuamente, o quadro devolvido e do instante presente.

        Se o stream nao estiver rodando, cai no ciclo pontual do
        CameraManager (uso avulso, fora do app).
        """

        if not self.isRunning():
            return self.camera.capture_frame(warmup_frames)

        restante = timeout_ms

        self._mutex.lock()
        try:
            alvo = self._seq + warmup_frames + 1

            while self._seq < alvo:

                if not self._running:
                    return None

                t0 = time.monotonic()

                if not self._cond.wait(self._mutex, restante):
                    return None

                restante -= int((time.monotonic() - t0) * 1000)

                if restante <= 0:
                    return None

            if self._last_frame is None:
                return None

            return self._last_frame.copy()
        finally:
            self._mutex.unlock()

    # ------------------------------------------------------------------

    @staticmethod
    def _to_qimage(frame_bgr):

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        h, w, ch = rgb.shape

        # o .copy() e obrigatorio: o QImage compartilha o buffer do array
        # numpy, que e descartado/sobrescrito na proxima iteracao
        return QImage(
            rgb.data,
            w,
            h,
            ch * w,
            QImage.Format_RGB888
        ).copy()
