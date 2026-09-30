"""
ETAPA 4 - Correcao residual da conversao pixel -> mm
=====================================================
Mesmo com as calibracoes intrinseca e mao-olho boas, sobra um erro
SISTEMATICO no ponto final: T_cam_flange imperfeito, cinematica nominal do
braco (sem encoder), altura da mesa... Tudo isso vira um deslocamento, uma
escala e/ou uma pequena rotacao no plano da mesa, e quase sempre o mesmo de
uma deteccao para outra - porque a pose de observacao e sempre a mesma.

Em vez de caçar cada fonte, medimos o erro direto: pares

    previsto = onde a visao disse que o objeto esta (X, Y, mundo)
    real     = onde a PONTA do robo precisa ir para acertar o objeto

e ajustamos uma transformacao 2D previsto -> real. "Real" e sempre em
coordenadas do ROBO (o ponto que se manda para mover_para), nao medido com
regua: e isso que faz a correcao absorver tambem os erros da cinematica.

Modelos:
  - translacao  (2 parametros): basta 1 ponto. Corrige offset constante.
  - similaridade (4 parametros): a partir de 3 pontos. Corrige tambem uma
    escala uniforme e uma rotacao - o tipico de altura da mesa / focal
    errada (escala) e de erro de orientacao na mao-olho (rotacao).
  - afim        (6 parametros): a partir de 4 pontos. Escalas diferentes
    em X e Y e cisalhamento.
Todos os modelos possiveis sao ajustados e fica o de menor erro de
validacao cruzada (leave-one-out): um modelo mais complexo so e usado
quando de fato preve melhor pontos que nao viu, e nao so porque tem mais
parametros.

VALE SO PARA A POSE DE OBSERVACAO EM QUE OS PONTOS FORAM COLETADOS. Mudou a
pose de busca ou refez uma calibracao? Limpe os pontos e colete de novo.
"""

import json
import os

import numpy as np

# Pontos com a mesma posicao prevista (a mesma deteccao registrada de novo,
# por exemplo depois de reajustar a ponta) substituem o registro anterior.
TOLERANCIA_MESMO_PONTO_MM = 1.0

# Minimo de pontos para cada modelo ser tentado. Na validacao cruzada o
# modelo e ajustado com n-1 pontos, que precisam bastar para determina-lo.
MIN_PONTOS = {
    "translacao": 1,
    "similaridade": 3,
    "afim": 4,
}


class CorrecaoResidual:

    def __init__(self, caminho):

        self.caminho = caminho
        self.pontos = []            # [{"classe", "previsto": [x, y], "real": [x, y]}]
        self.modelo = "nenhum"
        self.M = np.hstack([np.eye(2), np.zeros((2, 1))])   # 2x3: real = M @ [x, y, 1]
        self.erro_antes = None      # erro medio sem correcao (mm)
        self.erro_depois = None     # erro medio de validacao cruzada (mm)

        self._carregar()

    # ------------------------------------------------------------------
    # Uso
    # ------------------------------------------------------------------

    def aplicar(self, ponto):
        """(X, Y, Z) previsto -> (X, Y, Z) corrigido. Z passa direto."""

        p = np.asarray(ponto, dtype=float).copy()
        p[:2] = self.M @ np.array([p[0], p[1], 1.0])

        return p

    def registrar(self, previsto, real, classe=""):
        """Adiciona um par (so X, Y importam) e reajusta a correcao."""

        previsto = [float(previsto[0]), float(previsto[1])]
        real = [float(real[0]), float(real[1])]

        self.pontos = [
            p for p in self.pontos
            if np.linalg.norm(np.subtract(p["previsto"], previsto))
            > TOLERANCIA_MESMO_PONTO_MM
        ]
        self.pontos.append({"classe": classe, "previsto": previsto, "real": real})

        self._ajustar()
        self._salvar()

    def limpar(self):

        self.pontos = []
        self._ajustar()
        self._salvar()

    def resumo(self):

        n = len(self.pontos)

        if n == 0:
            return "Sem pontos de correcao"

        texto = f"{n} ponto(s), modelo {self.modelo}"

        if self.modelo == "translacao":
            dx, dy = self.M[:, 2]
            texto += f" (dX={dx:+.1f}, dY={dy:+.1f} mm)"
        elif self.modelo == "similaridade":
            escala = np.hypot(self.M[0, 0], self.M[1, 0])
            rotacao = np.degrees(np.arctan2(self.M[1, 0], self.M[0, 0]))
            texto += f" (escala {escala:.3f}, rotacao {rotacao:+.1f} graus)"

        texto += f". Erro sem correcao: {self.erro_antes:.1f} mm"

        if self.erro_depois is not None:
            texto += f", com correcao (validacao): {self.erro_depois:.1f} mm"
        else:
            texto += ". Registre mais pontos para validar"

        return texto

    # ------------------------------------------------------------------
    # Ajuste
    # ------------------------------------------------------------------

    @staticmethod
    def _ajustar_translacao(prev, real):

        M = np.hstack([np.eye(2), (real - prev).mean(axis=0).reshape(2, 1)])
        return M

    @staticmethod
    def _ajustar_similaridade(prev, real):

        # real = [[a, -b], [b, a]] @ prev + t   (escala s = |(a, b)|)
        A = np.zeros((2 * len(prev), 4))
        A[0::2] = np.column_stack([prev[:, 0], -prev[:, 1],
                                   np.ones(len(prev)), np.zeros(len(prev))])
        A[1::2] = np.column_stack([prev[:, 1], prev[:, 0],
                                   np.zeros(len(prev)), np.ones(len(prev))])

        (a, b, tx, ty), _, posto, _ = np.linalg.lstsq(
            A, real.reshape(-1), rcond=None
        )

        if posto < 4:
            return None

        return np.array([[a, -b, tx], [b, a, ty]])

    @staticmethod
    def _ajustar_afim(prev, real):

        X = np.hstack([prev, np.ones((len(prev), 1))])      # n x 3
        sol, _, posto, _ = np.linalg.lstsq(X, real, rcond=None)

        # pontos (quase) colineares: o afim fica indeterminado na direcao
        # perpendicular e extrapola qualquer coisa
        if posto < 3:
            return None

        return sol.T                                        # 2 x 3

    @staticmethod
    def _erro_medio(M, prev, real):

        X = np.hstack([prev, np.ones((len(prev), 1))])
        return float(np.mean(np.linalg.norm(X @ M.T - real, axis=1)))

    def _validacao_cruzada(self, ajustador, prev, real):
        """Erro medio prevendo cada ponto com o modelo ajustado sem ele."""

        erros = []

        for i in range(len(prev)):
            fora = np.arange(len(prev)) != i
            M = ajustador(prev[fora], real[fora])

            if M is None:
                return None

            erros.append(self._erro_medio(M, prev[i:i + 1], real[i:i + 1]))

        return float(np.mean(erros))

    def _ajustar(self):

        n = len(self.pontos)

        self.M = np.hstack([np.eye(2), np.zeros((2, 1))])
        self.modelo = "nenhum"
        self.erro_antes = None
        self.erro_depois = None

        if n == 0:
            return

        prev = np.array([p["previsto"] for p in self.pontos])
        real = np.array([p["real"] for p in self.pontos])

        self.erro_antes = float(np.mean(np.linalg.norm(real - prev, axis=1)))

        # com 1 ponto so a translacao existe e nao ha como validar
        self.M = self._ajustar_translacao(prev, real)
        self.modelo = "translacao"

        if n < 2:
            return

        ajustadores = {
            "translacao": self._ajustar_translacao,
            "similaridade": self._ajustar_similaridade,
            "afim": self._ajustar_afim,
        }

        for nome, ajustador in ajustadores.items():
            if n < MIN_PONTOS[nome]:
                continue

            M = ajustador(prev, real)
            erro = self._validacao_cruzada(ajustador, prev, real)

            if M is None or erro is None:
                continue

            if self.erro_depois is None or erro < self.erro_depois:
                self.M = M
                self.modelo = nome
                self.erro_depois = erro

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _carregar(self):

        if not os.path.exists(self.caminho):
            return

        try:
            with open(self.caminho, "r", encoding="utf-8") as f:
                self.pontos = json.load(f).get("pontos", [])
        except (json.JSONDecodeError, OSError) as erro:
            print(f"[AVISO] {self.caminho} ilegivel ({erro}); correcao desligada.")
            self.pontos = []

        self._ajustar()

    def _salvar(self):

        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)

        with open(self.caminho, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "pontos": self.pontos,
                    # so para consulta: o que vale e recalculado dos pontos
                    "modelo": self.modelo,
                    "M": self.M.tolist(),
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
