import time
from gpiozero import OutputDevice


class VentosaController:
    """Controla a bomba de vacuo e a valvula do efetuador tipo ventosa (24V DC)
    via GPIO da Raspberry Pi. Injetada no RobotController como self.ventosa,
    seguindo o mesmo padrao de self.serial e self.unity em ApplicationController.

    Deve ser instanciada uma unica vez (em ApplicationController.__init__),
    nunca dentro de uma rotina ou por chamada — reinstanciar o OutputDevice
    repetidamente pode gerar conflito de pino no gpiozero.
    """

    def __init__(self, pino_valvula=37, pino_bomba=27, tempo_vacuo=0.5):
        self.valvula = OutputDevice(pino_valvula, active_high=True, initial_value=False)
        # self.bomba = OutputDevice(pino_bomba, active_high=True, initial_value=False)
        self.tempo_vacuo = tempo_vacuo

    def pegar(self):
        """Liga a bomba e abre a valvula para gerar vacuo na ventosa."""
        # self.bomba.on()
        self.valvula.on()
        time.sleep(self.tempo_vacuo)

    def soltar(self):
        """Fecha a valvula (quebra o vacuo) e desliga a bomba."""
        self.valvula.off()
        # self.bomba.off()

    def desligar_tudo(self):
        """Desliga bomba e valvula imediatamente. Chamar em erros/paradas
        de emergencia, e sempre num bloco finally ao redor de uma rotina."""
        self.valvula.off()
        # self.bomba.off()
