import re
import time
import os
import numpy as np
import bezier as bz
import ik_craig as ik
from ik_craig import de as de_ferramenta
from config import GCODE_LOG
from ventosa_control import VentosaController
import backend.calibration.semi_circ as sc
import json
import cv2

class RobotController:
    def __init__(self, serial_driver, unity_client, ventosa=None):
        """Guarda as referências de comunicação e o estado inicial de posição e orientação do robô."""
        self.serial = serial_driver
        self.unity = unity_client
        self.ventosa = ventosa
        
        # Estado inicial do manipulador
        self.P0 = np.array([403.3643, 0, 570.3432])
        self.Ri = np.array([[0, 0, 1], 
                            [0, -1, 0], 
                            [1, 0, 0]])
        self.base_offset = np.array([-137, 645, 25])
        self.modo_juntas = False

        # Ultimos angulos de junta REALMENTE enviados ao GRBL, na convencao
        # do robo (j1..j6). E a partir deles que pose_flange_atual() calcula
        # a pose do flange — Ri/P0 sao a pose NOMINAL pedida, que nem sempre
        # e a que o robo assumiu.
        self.ultimos_angulos = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        # Callback opcional chamado a cada passo do movimento:
        # callback(x_mundo, y_mundo, z_mundo, j1, j2, j3, j4, j5, j6)
        self.callback_posicao = None

    def posicao_mundo(self):
        """Retorna a posição atual (X, Y, Z) no frame de mundo."""
        if self.P0 is not None:
            p = self.P0 + self.base_offset
            return (float(p[0]), float(p[1]), float(p[2]))
        return (0.0, 0.0, 0.0)

    def interpolar_abc(self, R_ini, P_ini, R_fim, P_fim, n=21):
        """Interpola linearmente os ângulos do pulso (A, B, C) entre a pose inicial e a final."""
        A0, B0, C0 = ik.calculo_angulos_abc(R_ini, P_ini)
        Af, Bf, Cf = ik.calculo_angulos_abc(R_fim, P_fim)
        return (np.round(np.linspace(A0, Af, n), 2),
                np.round(np.linspace(B0, Bf, n), 2),
                np.round(np.linspace(C0, Cf, n), 2))

    def executar_movimento(self, x, y, z, A, B, C, feedrate=800):
        """Calcula os ângulos das juntas para cada ponto, envia ao GRBL (G1) e espelha no
        Unity com a duração de cada segmento (feedrate linear, F em unidades/min)."""
        angulos = []
        for i in range(len(x)):
            theta1, theta2, theta3 = ik.calculo_angulos(x[i], y[i], z[i])
            angulos.append([theta1, theta2, theta3, A[i], -C[i], B[i]])

        angulos = np.array(angulos)
        for i in range(len(angulos)):
            theta1, theta2, theta3, A_grbl, B_grbl, C_grbl = angulos[i]
            self.unity.send_angles(theta1, theta2, -theta3, A[i], B[i], -C[i], feedrate)
            self.serial.send(f"G1 X{theta1} Y{theta2} Z{theta3} A{A_grbl} B{B_grbl} C{C_grbl} F{feedrate}")

            # As letras do GRBL nao seguem a ordem das juntas: A=j4, B=j6, C=j5.
            self.ultimos_angulos = (theta1, theta2, theta3,
                                    A_grbl, C_grbl, B_grbl)

            if self.callback_posicao:
                xw = float(x[i] + self.base_offset[0])
                yw = float(y[i] + self.base_offset[1])
                zw = float(z[i] + self.base_offset[2])
                self.callback_posicao(xw, yw, zw, *self.ultimos_angulos)

    def enviar_juntas(self, j1, j2, j3, j4, j5, j6):
        """Envia um G1 direto com os 6 ângulos das juntas (valores GRBL) e espelha no Unity.
        Ativa o modo juntas: bloqueia trajetórias/rotina até o Home ser usado."""
        self.modo_juntas = True
        self.serial.send(f"G1 X{j1} Y{j2} Z{j3} A{j4} B{j6} C{j5} F800")
        self.unity.send_angles(j1, j2, -j3, j4, j5, j6)
        self.ultimos_angulos = (j1, j2, j3, j4, j5, j6)

        if self.callback_posicao:
            pw = self.posicao_mundo()
            self.callback_posicao(pw[0], pw[1], pw[2], j1, j2, j3, j4, j5, j6)

    def pose_flange_atual(self):
        """Pose do flange em relacao a BASE (4x4), por cinematica direta dos
        ultimos angulos enviados ao GRBL.

        E esta a pose que a etapa 3 precisa: T_cam_flange (da calibracao
        mao-olho) tambem esta no frame do flange/base, entao os dois se
        encaixam direto. Usar Ri/P0 no lugar disso da erro, porque eles
        guardam a pose PEDIDA (e P0 esta no frame de mundo, nao da base).

        Devolve None se nenhum movimento foi executado ainda.
        """
        if self.ultimos_angulos is None:
            return None

        return ik.cinematica_direta(*self.ultimos_angulos)

    def calcular_tempo_trajetoria(self, x, y, z, theta4, theta5, theta6, feedrate=800, fator_seg=1.2):
        """Estima o tempo (s) da trajetória pela distância percorrida em cada segmento dividida pelo feedrate."""
        angulos = []
        for i in range(21):
            t1, t2, t3 = ik.calculo_angulos(x[i], y[i], z[i])
            angulos.append([t1, t2, t3, theta4[i], theta5[i], theta6[i]])

        angulos = np.array(angulos)
        deltas = np.diff(angulos, axis=0)                              # (20, 6)
        distancia_total = np.sum(np.sqrt(np.sum(deltas**2, axis=1)))   # norma euclidiana por segmento, somada

        tempo_min = distancia_total / feedrate     # F do GRBL é sempre unidades/min
        tempo_s = tempo_min * 60 * fator_seg

        print(f"[TRAJETÓRIA] Tempo estimado: {tempo_s:.1f} s")
        return tempo_s

    def home(self):
        """Retorna o robô à posição inicial (Home) com trajetória Bézier e atualiza o estado."""
        if self.modo_juntas:
            print("Modo juntas ativo — desfazendo último movimento via log (Home).")
            self.recuperar_do_log()
            self.P0 = np.array([403.3643, 0, 570.3432])
            self.Ri = np.array([[0, 0, 1], 
                                [0, -1, 0], 
                                [1, 0, 0]])
            self.modo_juntas = False
            return None, None, None

        P3 = np.array([403.3643, 0, 570.3432])
        Rf = np.array([[0, 0, 1], 
                       [0, -1, 0], 
                       [1, 0, 0]])
        
        x1, y1, z1 = bz.calculo_pontos(self.P0, P3, self.Ri, Rf)
        A1, B1, C1 = self.interpolar_abc(self.Ri, self.P0, Rf, P3, 21)
        
        self.executar_movimento(x1, y1, z1, A1, B1, C1)
        self.Ri = Rf
        self.P0 = P3

        return x1, y1, z1
    
    # Orientacao final usada por mover_para(): ferramenta apontando para baixo
    R_FERRAMENTA_PARA_BAIXO = np.array([[0, -1, 0],
                                        [-1, 0, 0],
                                        [0, 0, -1]])

    def alvo_alcancavel(self, x, y, z):
        """(x, y, z) esta dentro do envelope de trabalho?

        Recebe as MESMAS coordenadas que mover_para(): frame de MUNDO e
        ponta da ferramenta. Faz a mesma conversao que mover_para faz
        (mundo -> base, ponta -> punho) antes de checar.

        Use isto para filtrar as deteccoes da CNN: a camera enxerga uma area
        maior que a que o braco alcanca, entao nem todo objeto detectado da
        para pegar.
        """
        P = np.array([float(x), float(y), float(z)]) - self.base_offset
        punho = P - de_ferramenta * self.R_FERRAMENTA_PARA_BAIXO[:, -1]

        return ik.ponto_alcancavel(*punho)

    def mover_para(self, x, y, z, feedrate=800):
        """Move o efetuador ate o ponto (x, y, z), mantendo a orientacao
        atual (Ri), via trajetoria Bezier. Usado para movimentacao manual
        (coordenadas cartesianas)."""

        if self.modo_juntas:
            print("Modo juntas ativo — use o Home antes de um movimento cartesiano.")
            return None, None, None
        if not self.alvo_alcancavel(x, y, z):
            # Sem isto a cinematica inversa devolveria NaN em silencio e o
            # G-code sairia como "G1 Ynan Znan".
            print(f"Ponto ({x:.1f}, {y:.1f}, {z:.1f}) fora do alcance do braco.")
            return None, None, None

        b = np.array([-137, 645, 25])
        P3 = np.array([x, y, z])
        P3 -= b
        Rf = np.array([[ 0,  -1,  0], 
                        [ -1, 0,  0], 
                        [ 0,  0, -1]]) 

        x1, y1, z1 = bz.calculo_pontos(self.P0, P3, self.Ri, Rf)
        A1, B1, C1 = self.interpolar_abc(self.Ri, self.P0, Rf, P3, 21)
        self.executar_movimento(x1, y1, z1, A1, B1, C1, feedrate)

        self.Ri = Rf
        self.P0 = P3

        return x1, y1, z1

    def rotina_pegar_objeto(self, alvo, altura_aproximacao=100):
        """Pega o objeto em `alvo` (X, Y, Z da PONTA, frame de MUNDO, o mesmo
        de mover_para), com a ferramenta apontando para baixo, e volta ao Home.
        Usada com as coordenadas vindas da deteccao (vetor_mm)."""

        if self.modo_juntas:
            # a deteccao usa enviar_juntas(), que liga o modo juntas e
            # bloqueia movimentos cartesianos; volta ao Home antes
            self.home()
            time.sleep(15)

        if not self.alvo_alcancavel(*alvo):
            raise ValueError(f"Alvo {alvo} fora do alcance do braco")

        R = self.R_FERRAMENTA_PARA_BAIXO
        P_obj = np.array(alvo, dtype=float) - self.base_offset
        P_apr = P_obj + np.array([0, 0, altura_aproximacao])

        self.serial.send("M97 B60 T0.2") # Abre a garra

        # Estado 1: posicao atual -> acima do objeto (Bezier)
        x, y, z = bz.calculo_pontos(self.P0, P_apr, self.Ri, R)
        A, B, C = self.interpolar_abc(self.Ri, self.P0, R, P_apr, 21)
        self.executar_movimento(x, y, z, A, B, C)
        self.Ri = R
        self.P0 = P_apr
        time.sleep(self.calcular_tempo_trajetoria(x, y, z, A, B, C) + 1)

        A = np.full(21, A[-1])
        B = np.full(21, B[-1])
        C = np.full(21, C[-1])

        # Estado 2: descer e fechar a garra (Linear)
        x, y, z = bz.calculo_linear(P_apr, P_obj, R)
        self.executar_movimento(x, y, z, A, B, C)
        time.sleep(self.calcular_tempo_trajetoria(x, y, z, A, B, C) + 1)
        self.serial.send("M97 B0 T0.2") # Fecha a garra
        time.sleep(1)

        # Estado 3: subir com o objeto (Linear)
        x, y, z = bz.calculo_linear(P_obj, P_apr, R)
        self.executar_movimento(x, y, z, A, B, C)
        self.P0 = P_apr
        time.sleep(self.calcular_tempo_trajetoria(x, y, z, A, B, C) + 1)

        # (aqui entra o transporte ate o destino, se houver)

        # Estado 4: voltar para Home (Bezier)
        self.home()


    def recuperar_do_log(self):
        """Se o último G1 do log não for tudo zero, envia o inverso para
        desfazer o deslocamento e reancora o zero (G92)."""
        try:
            with open(GCODE_LOG) as f:
                linhas = f.read().splitlines()
        except (FileNotFoundError, OSError):
            return

        padrao = re.compile(r'G1\s+X(-?[\d.]+)\s+Y(-?[\d.]+)\s+Z(-?[\d.]+)\s+A(-?[\d.]+)\s+B(-?[\d.]+)\s+C(-?[\d.]+)')
        ultimo = None
        for linha in reversed(linhas):
            m = padrao.search(linha)
            if m:
                ultimo = m
                break
        if not ultimo:
            return

        vals = [float(v) for v in ultimo.groups()]
        if all(v == 0 for v in vals):
            return

        neg = [0.0 if v == 0 else round(-v, 2) for v in vals]
        self.serial.send(f"G1 X{neg[0]:g} Y{neg[1]:g} Z{neg[2]:g} A{neg[3]:g} B{neg[4]:g} C{neg[5]:g} F800")
        self.serial.send("G92 X0 Y0 Z0 A0 B0 C0")
        self.serial.send("G1 X0 Y0 Z0 A0 B0 C0 F800")

        # O braco terminou com todas as juntas em zero. Sem atualizar isto,
        # pose_flange_atual() continuaria devolvendo a pose ANTERIOR, e a
        # conversao pixel -> mm sairia errada em silencio.
        self.ultimos_angulos = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def rotina_lapis_suporte(self, plot_callback=None):
        """Máquina de estados que pega o lápis da mesa e o encaixa no suporte, desenhando no gráfico quando há callback."""
        import time

        self.serial.send("M97 B60 T0.2") # Abre a garra

        if self.modo_juntas:
            print("Modo juntas ativo — use o Home para retornar antes de executar a rotina.")
            return

        b = np.array([-137, 645, 25])
        # ---------------------------------------------------------
        # 1. DEFINIÇÃO DOS PONTOS E MATRIZES
        # ---------------------------------------------------------
        P_lapis = np.array([-300, 210, 0])        # Lápis na mesa
        P_apr_lapis = P_lapis + np.array([0, 0, 100]) # 10cm acima do lápis
        
        P_suporte = np.array([10, 120, 240])     # Ponto de encaixe no suporte
        P_apr_suporte = P_suporte + np.array([0, 0, 100]) # 10cm acima do suporte

        # Rotações
        # R1: Garra para baixo (para pegar o lápis deitado)
        R_baixo = np.array([[ 0,  -1,  0], 
                            [ -1, 0,  0], 
                            [ 0,  0, -1]]) 
        
        # R2: Garra virada 90 graus (Pitch/Roll) para o lápis ficar na vertical
        gama = 0
        alpha = np.rad2deg(np.arctan2(abs(P_suporte[1] - b[1]), abs(P_suporte[0] - b[0])))
        if b[0] > P_suporte[0]:
            gama = -(180-alpha)
        else:
            gama = -alpha

        print(f"Alpha = {alpha}")
        print(f"gama = {gama}")
        gama_rad = np.deg2rad(gama)


        R_vertical = np.array([[-np.sin(gama_rad), 0, np.cos(gama_rad)],
                    [np.cos(gama_rad), 0, np.sin(gama_rad)],
                    [0,                1, 0]], dtype=float)

        # ---------------------------------------------------------
        # 2. EXECUÇÃO DA MÁQUINA DE ESTADOS
        # ---------------------------------------------------------
        P_lapis -= b
        P_apr_lapis -= b
        P_suporte -= b
        P_apr_suporte -= b
        # Estado 1: Sair do Home para cima do Lápis (Bézier)
        x, y, z = bz.calculo_pontos(self.P0, P_apr_lapis, self.Ri, R_baixo)
        if plot_callback: plot_callback(list(x), list(y), list(z), True)
        A, B, C = self.interpolar_abc(self.Ri, self.P0, R_baixo, P_lapis, 21)
        self.executar_movimento(x, y, z, A, B, C)
        self.Ri = R_baixo
        self.P0 = P_apr_lapis

        pausa = self.calcular_tempo_trajetoria(x, y, z, A, B, C)
        time.sleep(pausa+1)
        # Estado 2: Descer, pegar o lápis e Recuar (Linear)
        x, y, z = bz.calculo_linear(P_apr_lapis, P_lapis, R_baixo)
        if plot_callback: plot_callback(list(x), list(y), list(z), False)
        A = np.full(21, A[-1])
        B = np.full(21, B[-1])
        C = np.full(21, C[-1])
        self.executar_movimento(x, y, z, A, B, C)
        pausa = self.calcular_tempo_trajetoria(x,y,z,A,B,C)
        time.sleep(pausa+1)
        self.serial.send("M97 B0 T0.2") # Fecha a garra
        time.sleep(1) # Aguarda fechamento
        
        x, y, z = bz.calculo_linear(P_lapis, P_apr_lapis, R_baixo)
        if plot_callback: plot_callback(list(x), list(y), list(z), False)
        self.executar_movimento(x, y, z, A, B, C)
        self.P0 = P_apr_lapis

        pausa = self.calcular_tempo_trajetoria(x, y, z, A, B, C)
        time.sleep(pausa+1)

        # Estado 3: Ir para cima do suporte girando a garra (Bézier)
        x, y, z = bz.calculo_pontos(self.P0, P_apr_suporte, self.Ri, R_vertical)
        if plot_callback: plot_callback(list(x), list(y), list(z), False)
        A, B, C = self.interpolar_abc(self.Ri, self.P0, R_vertical, P_suporte, 21)
        self.executar_movimento(x, y, z, A, B, C)
        self.Ri = R_vertical
        self.P0 = P_apr_suporte
        pausa = self.calcular_tempo_trajetoria(x, y, z, A, B, C)
        time.sleep(pausa+1)

        # Estado 4: Descer no suporte, soltar e Recuar (Linear)
        x, y, z = bz.calculo_linear(P_apr_suporte, P_suporte, R_vertical)
        if plot_callback: plot_callback(list(x), list(y), list(z), False)
        A = np.full(21, A[-1])
        B = np.full(21, B[-1])
        C = np.full(21, C[-1])
        self.executar_movimento(x, y, z, A, B, C)
        pausa = self.calcular_tempo_trajetoria(x, y, z, A, B, C)
        time.sleep(pausa+1)
        self.serial.send("M97 B60 T0.2") # Abre a garra
        time.sleep(1)
        
        x, y, z = bz.calculo_linear(P_suporte, P_apr_suporte, R_vertical)
        if plot_callback: plot_callback(list(x), list(y), list(z), False)
        self.executar_movimento(x, y, z, A, B, C)
        self.P0 = P_apr_suporte
        pausa = self.calcular_tempo_trajetoria(x, y, z, A, B, C)
        time.sleep(pausa+1)

        # Estado 5: Voltar para Home (Bézier)
        x, y, z = self.home()
        if plot_callback: plot_callback(list(x), list(y), list(z), False)

    ARQUIVO_POSES_CALIBRACAO = "poses_calibracao.json"

    def _registrar_pose_calibracao(self, pasta, nome_imagem, j1, j2, j3, A, B, C, rota):
        """Anexa a pose do flange de uma foto ao poses_calibracao.json.

        O arquivo é um dicionário {nome_da_imagem: {...}} e vai sendo
        atualizado foto a foto, então as duas rotas (que são duas chamadas
        separadas desta rotina) acabam no mesmo arquivo. Reexecutar a rotina
        sobrescreve as mesmas chaves, sem duplicar nada.
        """
        caminho = os.path.join(pasta, self.ARQUIVO_POSES_CALIBRACAO)

        poses = {}
        if os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    poses = json.load(f)
            except (json.JSONDecodeError, OSError) as erro:
                print(f"Aviso: {caminho} ilegível ({erro}); recriando do zero.")
                poses = {}

        T_flange_base = ik.cinematica_direta(j1, j2, j3, A, B, C)

        poses[nome_imagem] = {
            "juntas": [float(j1), float(j2), float(j3), float(A), float(B), float(C)],
            "T_flange_base": T_flange_base.tolist(),
            "rota": int(rota),
        }

        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(poses, f, indent=2)

    def rotina_captura_calibracao(self, rota=1, camera=None):

            u1 = np.array([1, 0, 0]) ## Normal à mesa e paralelo à parede usar até 11
            l1 = 11
            u2 = np.array([2, 1, 0]) ## Normal à mesa e com inclinaçao com a parede eu tenho que usar ate 10
            l2 = 10
            u, l = np.array([0, 0, 0]), int() # Inicializa as variáveis u e l como o tipo np.array e inteiro, respectivamente
            if rota == 1:
                u = u1
                l = l1
            else: u, l = u2, l2
            v = np.array([0, 0, 1])

            b = np.array([-137, 645, 25])
            c = np.array([-300, 210, 0])  
            c -= b

            px, py, pz = sc.calc_semi_circ(c, u, v)

            """Usar range(4,11) para paralelo à parede e range(4,10) com inclinaçao com a parede"""
            for i in range(4,l):
                P_atual = np.array([px[i], py[i], pz[i]])
                P_proximo = np.array([px[i+1], py[i+1], pz[i+1]])
                x, y, z = ik.calculo_angulos(px[i], py[i], pz[i])
                # 1. Eixo Z: Aponta para o centro
                Z_e = c - P_atual
                Z_hat = Z_e / np.linalg.norm(Z_e)
                
                # 2. Eixo Y: Tangente com ortogonalização de Gram-Schmidt
                v_e = P_proximo - P_atual
                Y_e = v_e - np.dot(v, Z_hat) * Z_hat
                Y_hat = Y_e / np.linalg.norm(Y_e)
                
                # 3. Eixo X: Produto vetorial (Y x Z)
                X_hat = np.cross(Y_hat, Z_hat)
                X_hat = X_hat / np.linalg.norm(X_hat) # Garantia extra de normalização
                
                # 4. Construir Matriz de Rotação (3x3)
                R_matrix = np.column_stack((X_hat, Y_hat, Z_hat))
                A, B, C = ik.calculo_angulos_abc_semi_circ(R_matrix, P_atual)
                C = 0
                self.enviar_juntas(x, y, z, A, B, C)
                if i == 4:
                    time.sleep(15)
                else:
                    time.sleep(5)

                # Captura pontual: abre a câmera, descarta warmup e fecha logo em seguida
                print(f"Realizando a captura de imagem da calibração (posição {i})...")
                if camera is not None:
                    frame = camera.capture_frame(warmup_frames=5)
                else:
                    cap = cv2.VideoCapture(0)
                    frame = None
                    if cap.isOpened():
                        for _ in range(5):
                            ret, f = cap.read()
                            if ret:
                                frame = f
                        cap.release()

                if frame is not None:
                    pasta_capturas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas")
                    os.makedirs(pasta_capturas, exist_ok=True)
                    nome_arquivo = f"pos(x={px[i]:.2f}__y={py[i]:.2f}__z={pz[i]:.2f}).jpg"
                    caminho_arquivo = os.path.join(pasta_capturas, nome_arquivo)
                    sucesso = cv2.imwrite(caminho_arquivo, frame)
                    if sucesso:
                        print(f"Imagem salva com sucesso como {caminho_arquivo}")
                        # Registra a pose REAL do flange junto com a foto. O nome
                        # do arquivo só guarda x/y/z; a calibração mão-olho também
                        # precisa da orientação, e ela não dá para ser deduzida do
                        # nome — ainda mais porque o C é zerado logo acima. Por
                        # isso gravamos a cinemática direta dos ângulos que foram
                        # de fato enviados ao GRBL.
                        self._registrar_pose_calibracao(
                            pasta_capturas, nome_arquivo, x, y, z, A, B, C, rota
                        )
                    else:
                        print(f"Erro: OpenCV falhou ao salvar {caminho_arquivo}")
                else:
                    print("Erro: Falha ao capturar frame da câmera.")
                time.sleep(1)

            self.enviar_juntas(0, 0, 0, 0, 0, 0)