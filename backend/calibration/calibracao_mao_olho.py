"""
ETAPA 2 - Calibração mão-olho (Hand-Eye, configuração eye-in-hand)
====================================================================
Objetivo: encontrar a transformação FIXA entre o frame da câmera e o
frame do efetuador (flange) do robô: T_cam_flange.

Configuração eye-in-hand: a câmera se move junto com o braço,
observando um padrão ChArUco FIXO no ambiente.

DE ONDE VÊM OS DADOS
--------------------
`robot_control.rotina_captura_calibracao()` percorre dois semicírculos e, em
cada parada, salva em `capturas/`:

  - a foto, com a posição no nome: `pos(x=110.47__y=-435.00__z=393.58).jpg`
  - a pose do flange, em `poses_calibracao.json`

A pose vai no JSON porque o nome do arquivo guarda APENAS a posição (x, y, z),
e o `calibrateHandEye` precisa também da ORIENTAÇÃO. Ela não dá para ser
deduzida do nome: a rotina de captura zera a junta 6 (`C = 0`) depois de
calcular os ângulos, então a orientação real do flange difere da nominal em
até ~56 graus. O JSON guarda a cinemática direta dos ângulos efetivamente
enviados ao GRBL, ou seja, a pose que o robô de fato assumiu.

Para capturas ANTIGAS, feitas antes de o JSON existir, há um fallback que
reconstrói as poses reproduzindo a geometria da rotina de captura (veja
`_poses_reconstruidas`).

Para cada pose montamos os dois dados que o `calibrateHandEye` precisa:
  (a) R/t_flange_base -> pose do flange em relação à base do robô
  (b) R/t_padrao_cam  -> pose do padrão em relação à câmera, via solvePnP
      sobre os cantos ChArUco detectados na imagem
"""

import glob
import json
import os

import cv2
import numpy as np

import ik_craig as ik
import backend.calibration.semi_circ as sc
from backend.calibration import handeye_fallback

# ---------- CAMINHOS ----------
# Todos absolutos, derivados da posição deste arquivo, para a calibração
# funcionar independentemente do diretório de onde o app foi iniciado.
RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_CAPTURAS = os.path.join(RAIZ_PROJETO, "capturas")
PASTA_DADOS = os.path.join(RAIZ_PROJETO, "backend", "calibration", "dados")

CAMINHO_IMAGENS = os.path.join(PASTA_CAPTURAS, "*.jpg")
CAMINHO_POSES = os.path.join(PASTA_CAPTURAS, "poses_calibracao.json")
CAMINHO_INTRINSECA = os.path.join(PASTA_DADOS, "calibracao_intrinseca.npz")
CAMINHO_SAIDA = os.path.join(PASTA_DADOS, "calibracao_mao_olho.npz")

# ---------- PADRÃO ----------
# Precisa ser IDÊNTICO ao usado na etapa 1 (calibracao_intrinseca.py)
TAMANHO_TABULEIRO = (10, 8)     # em número de QUADRADOS (colunas, linhas)
TAMANHO_QUADRADO_MM = 22.0
TAMANHO_MARCADOR_MM = 16.5
DICIONARIO_ARUCO = cv2.aruco.DICT_4X4_50

# Mínimo de cantos ChArUco para aceitar a pose de uma imagem. Com menos que
# isso o solvePnP fica instável (pontos quase colineares / concentrados).
MIN_CANTOS = 8

# ---------- GEOMETRIA DA ROTINA DE CAPTURA (só para o fallback) ----------
BASE_OFFSET = np.array([-137, 645, 25])
CENTRO_PADRAO = np.array([-300, 210, 0]) - BASE_OFFSET
EIXO_V = np.array([0, 0, 1])
ROTAS = [
    (np.array([1, 0, 0]), range(4, 11)),   # rota 1: paralelo à parede
    (np.array([2, 1, 0]), range(4, 10)),   # rota 2: inclinado
]

# O opencv-contrib-python 5.0.0.93 exporta as constantes CALIB_HAND_EYE_* mas
# NÃO exporta cv2.calibrateHandEye nos bindings Python. Quando a função existe
# usamos a implementação oficial (5 métodos); senão, o handeye_fallback.py.
USAR_OPENCV = hasattr(cv2, "calibrateHandEye")


# ---------- POSES DO ROBÔ ----------

def _poses_do_json():
    """Lê as poses gravadas pela rotina de captura. {nome_imagem: T_flange_base}."""
    if not os.path.exists(CAMINHO_POSES):
        return {}

    try:
        with open(CAMINHO_POSES, "r", encoding="utf-8") as f:
            bruto = json.load(f)
    except (json.JSONDecodeError, OSError) as erro:
        print(f"[AVISO] {CAMINHO_POSES} ilegível ({erro}); usando o fallback.")
        return {}

    return {
        nome: np.array(dados["T_flange_base"], dtype=float)
        for nome, dados in bruto.items()
    }


def _poses_reconstruidas():
    """Fallback para capturas antigas, feitas antes do poses_calibracao.json.

    Reproduz a geometria de `rotina_captura_calibracao` ponto a ponto e usa o
    nome do arquivo (que é determinístico) como chave.

    ATENÇÃO: a rotina de captura tem um bug de ortogonalização de
    Gram-Schmidt — usa `np.dot(v, Z_hat)` com o `v` global [0,0,1] em vez do
    próprio `v_e`, o que deixa R_matrix não-ortonormal (det ~= 0.9956). Como o
    robô fisicamente foi para a pose derivada dessa matriz torta, reproduzimos
    o bug aqui de propósito. Se o bug for corrigido em robot_control.py, este
    fallback deixa de valer para as capturas NOVAS — mas aí elas já terão o
    JSON, que é sempre a fonte preferida.
    """
    poses = {}

    for u, indices in ROTAS:
        px, py, pz = sc.calc_semi_circ(CENTRO_PADRAO, u, EIXO_V)

        for i in indices:
            P_atual = np.array([px[i], py[i], pz[i]])
            P_proximo = np.array([px[i + 1], py[i + 1], pz[i + 1]])

            Z_e = CENTRO_PADRAO - P_atual
            Z_hat = Z_e / np.linalg.norm(Z_e)

            v_e = P_proximo - P_atual
            Y_e = v_e - np.dot(EIXO_V, Z_hat) * Z_hat   # bug reproduzido
            Y_hat = Y_e / np.linalg.norm(Y_e)

            X_hat = np.cross(Y_hat, Z_hat)
            X_hat = X_hat / np.linalg.norm(X_hat)

            R_matrix = np.column_stack((X_hat, Y_hat, Z_hat))

            j1, j2, j3 = ik.calculo_angulos(px[i], py[i], pz[i])
            A, B, _ = ik.calculo_angulos_abc_semi_circ(R_matrix, P_atual)
            C = 0   # a rotina de captura zera a junta 6 antes de enviar

            nome = f"pos(x={px[i]:.2f}__y={py[i]:.2f}__z={pz[i]:.2f}).jpg"
            poses[nome] = ik.cinematica_direta(j1, j2, j3, A, B, C)

    return poses


def carregar_poses():
    """Poses do JSON quando existirem; senão, reconstruídas da geometria."""
    poses = _poses_do_json()

    if poses:
        print(f"Poses lidas de {os.path.basename(CAMINHO_POSES)}: {len(poses)}")
        return poses

    poses = _poses_reconstruidas()
    print(
        f"[AVISO] {os.path.basename(CAMINHO_POSES)} não encontrado — "
        f"reconstruindo {len(poses)} poses pela geometria da rotina de captura. "
        "Rode a calibração de novo para gerar o arquivo."
    )
    return poses


# ---------- POSE DO PADRÃO NA CÂMERA ----------

def pose_padrao_na_camera(imagem_cinza, detector, board, K, dist):
    """Detecta o ChArUco e devolve (R, t, n_cantos, rms) do padrão -> câmera."""
    cantos, ids, _, _ = detector.detectBoard(imagem_cinza)

    if cantos is None or ids is None or len(cantos) < MIN_CANTOS:
        return None, None, (0 if cantos is None else len(cantos)), None

    obj_p, img_p = board.matchImagePoints(cantos, ids)
    if obj_p is None or img_p is None or len(obj_p) < MIN_CANTOS:
        return None, None, len(cantos), None

    ok, rvec, tvec = cv2.solvePnP(obj_p, img_p, K, dist)
    if not ok:
        return None, None, len(cantos), None

    projetado, _ = cv2.projectPoints(obj_p, rvec, tvec, K, dist)
    rms = float(np.sqrt(np.mean(np.sum(
        (projetado.reshape(-1, 2) - img_p.reshape(-1, 2)) ** 2, axis=1
    ))))

    R, _ = cv2.Rodrigues(rvec)
    return R, tvec, len(cantos), rms


# ---------- VALIDAÇÃO ----------

def _alvos_estimados(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista):
    """T_padrao_base estimado a partir de cada pose (tem de dar sempre igual)."""
    return [
        T_fb @ T_cam_flange @ T_pc
        for T_fb, T_pc in zip(T_flange_base_lista, T_padrao_cam_lista)
    ]


def erro_do_alvo_fixo(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista):
    """Mede a consistência da calibração.

    O padrão é FIXO no ambiente, então T_padrao_base tem de dar a MESMA
    matriz em todas as poses. A dispersão é o erro residual da calibração.
    """
    alvos = _alvos_estimados(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista)

    posicoes = np.array([T[:3, 3] for T in alvos])
    pos_media = posicoes.mean(axis=0)
    erro_pos = float(np.mean(np.linalg.norm(posicoes - pos_media, axis=1)))

    R_ref = alvos[0][:3, :3]
    angulos = [
        np.rad2deg(np.arccos(np.clip(
            (np.trace(R_ref.T @ T[:3, :3]) - 1.0) / 2.0, -1.0, 1.0
        )))
        for T in alvos
    ]

    return erro_pos, float(np.mean(angulos)), pos_media


def residuos_por_pose(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista):
    """Distância de cada pose até a posição média do alvo (mm).

    Serve para achar poses ruins: se UMA destoa muito, a detecção do padrão
    nela provavelmente saiu torta e vale removê-la.
    """
    posicoes = np.array([
        T[:3, 3]
        for T in _alvos_estimados(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista)
    ])
    return list(np.linalg.norm(posicoes - posicoes.mean(axis=0), axis=1))


# ---------- ETAPA 2 ----------

def calibrate_2():
    """Roda a calibração mão-olho e salva T_cam_flange em dados/."""
    if not os.path.exists(CAMINHO_INTRINSECA):
        raise RuntimeError(
            f"Calibração intrínseca não encontrada: {CAMINHO_INTRINSECA}. "
            "Rode calibrate_1() primeiro."
        )

    dados = np.load(CAMINHO_INTRINSECA)
    K, dist = dados["K"], dados["dist"]

    board = cv2.aruco.CharucoBoard(
        TAMANHO_TABULEIRO,
        TAMANHO_QUADRADO_MM,
        TAMANHO_MARCADOR_MM,
        cv2.aruco.getPredefinedDictionary(DICIONARIO_ARUCO),
    )
    detector = cv2.aruco.CharucoDetector(board)

    poses = carregar_poses()
    imagens = sorted(glob.glob(CAMINHO_IMAGENS))
    if not imagens:
        raise RuntimeError(f"Nenhuma imagem encontrada em {CAMINHO_IMAGENS}")

    print(f"Encontradas {len(imagens)} imagens em {PASTA_CAPTURAS}\n")

    R_flange_base_lista, t_flange_base_lista = [], []
    R_padrao_cam_lista, t_padrao_cam_lista = [], []
    T_flange_base_lista, T_padrao_cam_lista = [], []
    nomes_usados = []

    for caminho in imagens:
        nome = os.path.basename(caminho)

        T_fb = poses.get(nome)
        if T_fb is None:
            print(f"[PULADO] {nome}: sem pose registrada")
            continue

        img = cv2.imread(caminho)
        if img is None:
            print(f"[PULADO] {nome}: falha ao ler a imagem")
            continue

        cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        R_pc, t_pc, n_cantos, rms = pose_padrao_na_camera(cinza, detector, board, K, dist)

        if R_pc is None:
            print(f"[PULADO] {nome}: padrão não detectado "
                  f"({n_cantos} cantos, mínimo {MIN_CANTOS})")
            continue

        T_pc = np.eye(4)
        T_pc[:3, :3] = R_pc
        T_pc[:3, 3] = t_pc.flatten()

        R_flange_base_lista.append(T_fb[:3, :3])
        t_flange_base_lista.append(T_fb[:3, 3].reshape(3, 1))
        R_padrao_cam_lista.append(R_pc)
        t_padrao_cam_lista.append(t_pc)
        T_flange_base_lista.append(T_fb)
        T_padrao_cam_lista.append(T_pc)
        nomes_usados.append(nome)

        print(f"[OK] {nome}: {n_cantos} cantos, reprojeção {rms:.2f} px")

    n = len(R_flange_base_lista)
    print(f"\n{n} poses válidas de {len(imagens)} imagens.")

    if n < 3:
        raise RuntimeError("São necessárias pelo menos 3 poses válidas para calibrar.")
    if n < 10:
        print("AVISO: menos de 10 poses válidas — o resultado pode ficar impreciso.")

    # ---------- CALIBRAÇÃO MÃO-OLHO ----------
    if USAR_OPENCV:
        metodos = {
            "TSAI": cv2.CALIB_HAND_EYE_TSAI,
            "PARK": cv2.CALIB_HAND_EYE_PARK,
            "HORAUD": cv2.CALIB_HAND_EYE_HORAUD,
            "ANDREFF": cv2.CALIB_HAND_EYE_ANDREFF,
            "DANIILIDIS": cv2.CALIB_HAND_EYE_DANIILIDIS,
        }
        print(f"\nUsando cv2.calibrateHandEye (OpenCV {cv2.__version__}).")
    else:
        metodos = {"TSAI": "TSAI", "PARK": "PARK"}
        print(
            f"\nAVISO: cv2.calibrateHandEye não existe nesta build do OpenCV "
            f"({cv2.__version__}); usando handeye_fallback.py (TSAI, PARK).\n"
            'Para usar a implementação oficial: pip install "opencv-contrib-python<5"'
        )

    print("\n=== COMPARAÇÃO DOS MÉTODOS ===")
    print(f"{'método':<12} {'erro pos (mm)':>14} {'erro rot (deg)':>15}")

    resultados = {}
    for nome_metodo, metodo in metodos.items():
        try:
            if USAR_OPENCV:
                R_cf, t_cf = cv2.calibrateHandEye(
                    R_gripper2base=R_flange_base_lista,
                    t_gripper2base=t_flange_base_lista,
                    R_target2cam=R_padrao_cam_lista,
                    t_target2cam=t_padrao_cam_lista,
                    method=metodo,
                )
            else:
                R_cf, t_cf = handeye_fallback.calibrate_hand_eye(
                    R_flange_base_lista,
                    t_flange_base_lista,
                    R_padrao_cam_lista,
                    t_padrao_cam_lista,
                    metodo=metodo,
                )
        except (cv2.error, ValueError, np.linalg.LinAlgError) as exc:
            print(f"{nome_metodo:<12} falhou: {exc}")
            continue

        T_cf = np.eye(4)
        T_cf[:3, :3] = R_cf
        T_cf[:3, 3] = t_cf.flatten()

        erro_pos, erro_rot, _ = erro_do_alvo_fixo(
            T_cf, T_flange_base_lista, T_padrao_cam_lista
        )
        resultados[nome_metodo] = (T_cf, erro_pos, erro_rot)
        print(f"{nome_metodo:<12} {erro_pos:>14.2f} {erro_rot:>15.2f}")

    if not resultados:
        raise RuntimeError("Todos os métodos de calibração falharam.")

    # Escolhe o método com menor dispersão do alvo fixo
    melhor = min(resultados, key=lambda k: resultados[k][1])
    T_cam_flange, erro_pos, erro_rot = resultados[melhor]

    print(f"\n=== RESULTADO (método {melhor}): T_cam -> flange ===")
    print("Rotação (câmera -> flange):\n", T_cam_flange[:3, :3])
    print("Translação em mm (câmera -> flange):\n", T_cam_flange[:3, 3])

    _, _, pos_alvo = erro_do_alvo_fixo(
        T_cam_flange, T_flange_base_lista, T_padrao_cam_lista
    )

    print("\n--- Validação (o padrão é fixo: a dispersão abaixo é o resíduo) ---")
    print(f"Erro médio de posição do alvo : {erro_pos:.2f} mm")
    print(f"Erro médio de orientação      : {erro_rot:.2f} graus")

    print("\nResíduo por pose (distância até a posição média do alvo):")
    for residuo, nome in sorted(
        zip(residuos_por_pose(T_cam_flange, T_flange_base_lista, T_padrao_cam_lista),
            nomes_usados),
        reverse=True,
    ):
        print(f"  {residuo:7.2f} mm   {nome}")

    # Conferência independente: a origem do ChArUco é um CANTO do tabuleiro,
    # então deslocamos até o centro para comparar com o ponto que a rotina de
    # captura assumiu. Se a calibração estiver certa, os dois têm de bater.
    centro_local = np.array([
        TAMANHO_TABULEIRO[0] * TAMANHO_QUADRADO_MM / 2.0,
        TAMANHO_TABULEIRO[1] * TAMANHO_QUADRADO_MM / 2.0,
        0.0, 1.0,
    ])
    centro_estimado = np.mean(
        [(T_fb @ T_cam_flange @ T_pc @ centro_local)[:3]
         for T_fb, T_pc in zip(T_flange_base_lista, T_padrao_cam_lista)],
        axis=0,
    )
    desvio = centro_estimado - CENTRO_PADRAO

    print("\n--- Conferência independente: onde está o tabuleiro? ---")
    print(f"Canto do tabuleiro estimado na base : {pos_alvo.round(1)} mm")
    print(f"Centro do tabuleiro estimado na base: {centro_estimado.round(1)} mm")
    print(f"Centro assumido na rotina de captura: {CENTRO_PADRAO} mm")
    print(f"Diferença: {desvio.round(1)} mm  (norma {np.linalg.norm(desvio):.1f} mm)")

    os.makedirs(PASTA_DADOS, exist_ok=True)
    np.savez(CAMINHO_SAIDA, T_cam_flange=T_cam_flange)
    print(f"\nSalvo em {CAMINHO_SAIDA}")

    return T_cam_flange
