from PySide6.QtCore import QThread, Signal


class RobotActionThread(QThread):
    """
    Executa uma acao do RobotController (home, mover_para, rotina_lapis_suporte,
    etc.) em background. Necessario porque SerialDriver.send() bloqueia
    esperando o 'ok' do GRBL: se chamado direto na GUI thread, a interface
    trava ate o robo terminar de se mover.
    """

    finishedOk = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, action, *args, **kwargs):
        super().__init__()

        self.action = action
        self.args = args
        self.kwargs = kwargs

    def run(self):

        try:
            self.action(*self.args, **self.kwargs)
            self.finishedOk.emit("Movimento concluido")

        except Exception as e:
            self.errorOccurred.emit(f"Erro no movimento: {e}")
