"""
ETAPA 3 - Pipeline completo: detecção da CNN -> vetor (mm) no frame do robô
=============================================================================
Junta as duas calibrações anteriores com a detecção da CNN para gerar
o vetor 3D final, em mm, no referencial da base do manipulador.

Suporta dois modos:
  MODO A: profundidade fixa/plano conhecido (câmera RGB simples)
  MODO B: profundidade lida de um sensor RGB-D (ex: RealSense)
"""

import cv2
import numpy as np

# ---------- CARREGA AS CALIBRAÇÕES ----------
intrinseca = np.load("calibracao_intrinseca.npz")
K, dist = intrinseca["K"], intrinseca["dist"]

mao_olho = np.load("calibracao_mao_olho.npz")
T_cam_flange = mao_olho["T_cam_flange"]  # 4x4, câmera -> flange

fx, fy = K[0, 0], K[1, 1]
cx, cy = K[0, 2], K[1, 2]


def pixel_para_ponto_camera(u, v, Z_mm):
    """
    Converte um pixel (u, v) + profundidade Z conhecida (em mm)
    em um ponto 3D no referencial da CÂMERA (em mm).
    Fórmula de projeção inversa do modelo pinhole.
    """
    X = (u - cx) * Z_mm / fx
    Y = (v - cy) * Z_mm / fy
    return np.array([X, Y, Z_mm, 1.0])  # coordenadas homogêneas


def matriz_homogenea(R, t):
    """Monta uma matriz 4x4 a partir de rotação R (3x3) e translação t (3,)."""
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def ponto_camera_para_base(ponto_cam_h, T_flange_base):
    """
    Transforma um ponto do frame da câmera para o frame da base do robô,
    passando por: câmera -> flange -> base.
    T_flange_base: pose ATUAL do efetuador em relação à base (cinemática
    direta do robô no momento da captura da imagem).
    """
    T_cam_base = T_flange_base @ T_cam_flange
    ponto_base_h = T_cam_base @ ponto_cam_h
    return ponto_base_h[:3]  # (X, Y, Z) em mm, frame da base do robô


# ---------- MODO A: plano de trabalho a altura Z fixa/conhecida ----------
def obter_vetor_modo_plano(u, v, Z_camera_mm, T_flange_base):
    """
    Usa quando os objetos estão sobre uma superfície plana e a distância
    da câmera até esse plano (Z_camera_mm) é conhecida/medida.
    """
    ponto_cam = pixel_para_ponto_camera(u, v, Z_camera_mm)
    return ponto_camera_para_base(ponto_cam, T_flange_base)


# ---------- MODO B: sensor RGB-D fornece profundidade por pixel ----------
def obter_vetor_modo_rgbd(u, v, mapa_profundidade_mm, T_flange_base):
    """
    Usa quando você tem um sensor RGB-D (RealSense, Kinect etc).
    mapa_profundidade_mm: array 2D com profundidade em mm por pixel,
    alinhado com a imagem RGB usada pela CNN.
    """
    Z_mm = float(mapa_profundidade_mm[int(v), int(u)])
    if Z_mm <= 0:
        raise ValueError("Profundidade inválida nesse pixel (sem leitura).")
    ponto_cam = pixel_para_ponto_camera(u, v, Z_mm)
    return ponto_camera_para_base(ponto_cam, T_flange_base)


# ---------- EXEMPLO DE USO NO LOOP PRINCIPAL ----------
#
# while True:
#     frame_bruto = capturar_imagem()
#     frame, K_novo = undistort_imagem(frame_bruto, K, dist)  # etapa 1
#
#     deteccoes = modelo_cnn.detectar(frame)  # sua CNN (YOLO, etc.)
#     for det in deteccoes:
#         u, v = det.centro_x, det.centro_y  # centroide em pixels
#
#         T_flange_base = ler_pose_atual_do_robo()  # cinemática direta, 4x4
#
#         # Escolha o modo conforme seu hardware:
#         vetor_mm = obter_vetor_modo_plano(u, v, Z_camera_mm=350.0,
#                                            T_flange_base=T_flange_base)
#         # ou, com RGB-D:
#         # vetor_mm = obter_vetor_modo_rgbd(u, v, mapa_profundidade,
#         #                                   T_flange_base)
#
#         enviar_vetor_para_manipulador(vetor_mm)  # (X, Y, Z) em mm
