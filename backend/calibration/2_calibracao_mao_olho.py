"""
ETAPA 2 - Calibração mão-olho (Hand-Eye, configuração eye-in-hand)
====================================================================
Objetivo: encontrar a transformação FIXA entre o frame da câmera e o
frame do efetuador (flange) do robô: T_cam_para_flange.

Configuração eye-in-hand: a câmera se move junto com o braço,
observando um padrão ChArUco/xadrez FIXO no ambiente.

Para cada uma das N poses do robô, você precisa de DOIS dados:
  (a) R_flange_base, t_flange_base -> pose do efetuador em relação à
      base do robô (você já tem isso pela cinemática direta / driver do robô)
  (b) R_padrao_cam, t_padrao_cam   -> pose do padrão em relação à câmera
      (calculada com solvePnP a partir da imagem capturada)

Colete de 10 a 20 poses bem distribuídas (variando posição E orientação
do braço) para um resultado robusto.
"""

import cv2
import numpy as np

# ---------- CARREGA A CALIBRAÇÃO INTRÍNSECA (etapa 1) ----------
dados = np.load("calibracao_intrinseca.npz")
K, dist = dados["K"], dados["dist"]

PADRAO_CANTOS = (9, 6)
TAMANHO_QUADRADO_MM = 25.0

objp = np.zeros((PADRAO_CANTOS[0] * PADRAO_CANTOS[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:PADRAO_CANTOS[0], 0:PADRAO_CANTOS[1]].T.reshape(-1, 2)
objp *= TAMANHO_QUADRADO_MM


def pose_padrao_na_camera(imagem_cinza):
    """Detecta o padrão e retorna (R, t) do padrão em relação à câmera."""
    encontrou, cantos = cv2.findChessboardCorners(imagem_cinza, PADRAO_CANTOS, None)
    if not encontrou:
        return None, None
    ok, rvec, tvec = cv2.solvePnP(objp, cantos, K, dist)
    if not ok:
        return None, None
    R, _ = cv2.Rodrigues(rvec)
    return R, tvec


# ---------- COLETA DE DADOS (uma entrada por pose do robô) ----------
# Preencha estas listas em runtime, movendo o robô e capturando imagem
# a cada pose. Aqui está o formato esperado; substitua pelo seu loop real
# de aquisição (integração com o driver/SDK do seu manipulador).

R_flange_base_lista = []   # lista de matrizes 3x3 (pose do efetuador->base)
t_flange_base_lista = []   # lista de vetores 3x1 (em mm)
R_padrao_cam_lista = []    # lista de matrizes 3x3 (pose do padrão->câmera)
t_padrao_cam_lista = []    # lista de vetores 3x1 (em mm)

# Exemplo de loop de aquisição (adapte à sua API de robô/câmera):
#
# for pose_robo in lista_de_poses_planejadas:
#     mover_robo_para(pose_robo)
#     time.sleep(0.5)  # estabilizar
#     img = capturar_imagem()
#     cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     R_pc, t_pc = pose_padrao_na_camera(cinza)
#     if R_pc is None:
#         continue  # padrão não visível nesta pose, pule
#     R_fb, t_fb = ler_pose_efetuador_do_robo()  # via cinemática direta
#     R_flange_base_lista.append(R_fb)
#     t_flange_base_lista.append(t_fb)
#     R_padrao_cam_lista.append(R_pc)
#     t_padrao_cam_lista.append(t_pc)

# ---------- CALIBRAÇÃO MÃO-OLHO ----------
if len(R_flange_base_lista) < 10:
    raise RuntimeError(
        "Colete pelo menos 10 poses (idealmente 15-20) antes de calibrar."
    )

R_cam_flange, t_cam_flange = cv2.calibrateHandEye(
    R_gripper2base=R_flange_base_lista,
    t_gripper2base=t_flange_base_lista,
    R_target2cam=R_padrao_cam_lista,
    t_target2cam=t_padrao_cam_lista,
    method=cv2.CALIB_HAND_EYE_TSAI,  # alternativas: PARK, HORAUD, DANIILIDIS
)

print("=== RESULTADO: T_cam -> flange ===")
print("Rotação (câmera -> flange):\n", R_cam_flange)
print("Translação em mm (câmera -> flange):\n", t_cam_flange)

# Monta a matriz homogênea 4x4 para uso direto na etapa 3
T_cam_flange = np.eye(4)
T_cam_flange[:3, :3] = R_cam_flange
T_cam_flange[:3, 3] = t_cam_flange.flatten()

np.savez("calibracao_mao_olho.npz", T_cam_flange=T_cam_flange)
print("\nSalvo em calibracao_mao_olho.npz")

# ---------- VALIDAÇÃO RECOMENDADA ----------
# Após calibrar: coloque um objeto em posição conhecida (medida com régua/
# paquímetro), rode o pipeline completo (etapa 3) e compare o vetor
# calculado com a posição real medida. Erro esperado: poucos mm,
# dependendo da qualidade da calibração e do padrão usado.
