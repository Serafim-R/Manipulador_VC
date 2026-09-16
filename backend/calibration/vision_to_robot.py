import os

import cv2
import numpy as np


class VisionToRobot:
    """
    Etapa 3 do pipeline de calibracao: converte deteccoes 2D (pixel) da CNN
    em vetores 3D (mm), no referencial da BASE do manipulador.

    Carrega as duas calibracoes ja feitas:
      - intrinseca (etapa 1): K, dist
      - mao-olho  (etapa 2): T_cam_flange (fixo, camera -> flange)
    """

    def __init__(self, intrinsic_path, hand_eye_path):

        if not os.path.exists(intrinsic_path):
            raise FileNotFoundError(
                f"Calibracao intrinseca nao encontrada: {intrinsic_path}"
            )
        if not os.path.exists(hand_eye_path):
            raise FileNotFoundError(
                f"Calibracao mao-olho nao encontrada: {hand_eye_path}"
            )

        intrinseca = np.load(intrinsic_path)
        self.K = intrinseca["K"]
        self.dist = intrinseca["dist"]

        mao_olho = np.load(hand_eye_path)
        self.T_cam_flange = mao_olho["T_cam_flange"]  # 4x4, camera -> flange

        self.fx, self.fy = self.K[0, 0], self.K[1, 1]
        self.cx, self.cy = self.K[0, 2], self.K[1, 2]

        # matriz "nova" usada para desdistorcer os frames - precisa ser
        # a MESMA usada no undistort_frame(), senao K e frame ficam
        # inconsistentes entre si
        self._novo_K = None

    def preparar_undistort(self, largura, altura):
        """Calcula o novo K (para alpha=0) uma unica vez, para um dado
        tamanho de frame. Chame isso antes do primeiro undistort_frame()."""

        self._novo_K, _ = cv2.getOptimalNewCameraMatrix(
            self.K, self.dist, (largura, altura), alpha=0
        )

        # a partir de agora, pixel_para_ponto_camera deve usar o NOVO K,
        # ja que e ele que descreve a geometria do frame ja desdistorcido
        self.fx, self.fy = self._novo_K[0, 0], self._novo_K[1, 1]
        self.cx, self.cy = self._novo_K[0, 2], self._novo_K[1, 2]

    def undistort_frame(self, frame):
        """Remove a distorcao de lente do frame (BGR). Chame isso ANTES
        de passar o frame para a YOLO."""

        h, w = frame.shape[:2]

        if self._novo_K is None:
            self.preparar_undistort(w, h)

        mapx, mapy = cv2.initUndistortRectifyMap(
            self.K, self.dist, None, self._novo_K, (w, h), cv2.CV_32FC1
        )

        return cv2.remap(frame, mapx, mapy, cv2.INTER_LINEAR)

    def pixel_para_ponto_camera(self, u, v, Z_mm):
        """Projecao inversa do modelo pinhole: pixel + profundidade -> ponto
        3D no referencial da CAMERA (em mm)."""

        X = (u - self.cx) * Z_mm / self.fx
        Y = (v - self.cy) * Z_mm / self.fy

        return np.array([X, Y, Z_mm, 1.0])

    def ponto_camera_para_base(self, ponto_cam_h, R_flange_base, t_flange_base):
        """Transforma um ponto do frame da camera para o frame da base do
        robo: camera -> flange -> base."""

        T_flange_base = np.eye(4)
        T_flange_base[:3, :3] = R_flange_base
        T_flange_base[:3, 3] = t_flange_base

        T_cam_base = T_flange_base @ self.T_cam_flange
        ponto_base_h = T_cam_base @ ponto_cam_h

        return ponto_base_h[:3]  # (X, Y, Z) em mm, referencial da base

    def vetor_para_deteccao(self, u, v, Z_camera_mm, R_flange_base, t_flange_base):
        """Modo A (plano de trabalho a distancia Z_camera_mm conhecida e
        fixa, medida na pose de observacao). Retorna (X, Y, Z) em mm,
        ja no referencial da base do robo - pronto para mover_para()."""

        ponto_cam = self.pixel_para_ponto_camera(u, v, Z_camera_mm)

        return self.ponto_camera_para_base(ponto_cam, R_flange_base, t_flange_base)
