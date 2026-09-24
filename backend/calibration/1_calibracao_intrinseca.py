"""
ETAPA 1 - Calibração intrínseca da câmera (Padrão ChArUco)
===========================================================
Objetivo: obter a matriz de câmera (K) e os coeficientes de distorção
a partir de várias fotos de um padrão ChArUco.
"""

import cv2
import numpy as np
import glob

# ---------- CONFIGURAÇÃO ----------
CAMINHO_IMAGENS = "calibracao_fotos/*.png"

# Tamanho da grade ChArUco em número de QUADRADOS (Colunas, Linhas)
TAMANHO_TABULEIRO = (10, 8)  

TAMANHO_QUADRADO_MM = 22.0   
TAMANHO_MARCADOR_MM = 16.5   

# Dicionário do ArUco usado na impressão da folha
DICIONARIO_ARUCO = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# Criando o objeto da grade ChArUco no OpenCV
board = cv2.aruco.CharucoBoard(
    TAMANHO_TABULEIRO,
    TAMANHO_QUADRADO_MM,
    TAMANHO_MARCADOR_MM,
    DICIONARIO_ARUCO
)

# Criador do detector ChArUco
detector = cv2.aruco.CharucoDetector(board)

# Armazenamento dos pontos para calibração
todos_cantos_charuco = []
todos_ids_charuco = []

imagens = glob.glob(CAMINHO_IMAGENS)
if not imagens:
    raise RuntimeError(f"Nenhuma imagem encontrada em {CAMINHO_IMAGENS}")

tamanho_img = None
imagens_validas = 0

for caminho in imagens:
    img = cv2.imread(caminho)
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    tamanho_img = cinza.shape[::-1]

    # Detecção de marcadores e cantos do ChArUco
    charuco_corners, charuco_ids, marker_corners, marker_ids = detector.detectBoard(cinza)

    if charuco_corners is not None and charuco_ids is not None and len(charuco_corners) >= 4:
        todos_cantos_charuco.append(charuco_corners)
        todos_ids_charuco.append(charuco_ids)
        imagens_validas += 1
        print(f"[OK] {len(charuco_corners)} cantos ChArUco detectados em: {caminho}")
    else:
        print(f"[AVISO] Padrão não encontrado em: {caminho}")

if imagens_validas < 10:
    print(f"\nAviso: poucas imagens válidas ({imagens_validas}/10). A calibração pode ficar imprecisa.")

if imagens_validas == 0:
    raise RuntimeError("Nenhum padrão ChArUco foi detectado.")

# ---------- PREPARAÇÃO DOS PONTOS PARA CALIBRAÇÃO ----------
obj_points = []  # Pontos 3D reais no referencial do tabuleiro
img_points = []  # Pontos 2D correspondentes detectados na imagem

for corners, ids in zip(todos_cantos_charuco, todos_ids_charuco):
    # O método matchImagePoints cruza os IDs detectados com as coordenadas 3D do tabuleiro
    obj_p, img_p = board.matchImagePoints(corners, ids)
    
    # Adiciona à lista geral apenas se conseguiu fazer a correspondência corretamente
    if obj_p is not None and img_p is not None and len(obj_p) >= 4:
        obj_points.append(obj_p)
        img_points.append(img_p)

# ---------- CALIBRAÇÃO ----------
print("\nIniciando cálculo de calibração...")
ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
    obj_points, 
    img_points, 
    tamanho_img, 
    None, 
    None
)

print("\n=== RESULTADO ===")
print("Erro de reprojeção médio (RMS):", ret)
print("Matriz da câmera (K):\n", K)
print("Coeficientes de distorção:\n", dist)

# ---------- SALVAR PARA AS PRÓXIMAS ETAPAS ----------
np.savez("calibracao_intrinseca.npz", K=K, dist=dist, tamanho_img=tamanho_img)
print("\nSalvo em calibracao_intrinseca.npz")


def undistort_imagem(img, K, dist):
    """Remove a distorção de uma imagem usando os parâmetros calibrados."""
    h, w = img.shape[:2]
    novo_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), alpha=0)
    mapx, mapy = cv2.initUndistortRectifyMap(
        K, dist, None, novo_K, (w, h), cv2.CV_32FC1
    )
    return cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR), novo_K