"""
ETAPA 1 - Calibração intrínseca da câmera (Padrão ChArUco)
===========================================================
Objetivo: obter a matriz de câmera (K) e os coeficientes de distorção
a partir de várias fotos de um padrão ChArUco.
"""

import cv2
import numpy as np
import glob
import os

# Caminhos absolutos, derivados da posição deste arquivo, para a calibração
# funcionar independentemente do diretório de onde o app foi iniciado.
RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PASTA_CAPTURAS = os.path.join(RAIZ_PROJETO, "capturas")
PASTA_DADOS = os.path.join(RAIZ_PROJETO, "backend", "calibration", "dados")


def calibrate_1():
    # ---------- CONFIGURAÇÃO ----------
    CAMINHO_IMAGENS = os.path.join(PASTA_CAPTURAS, "*.jpg")

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
    nomes_validos = []

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
            nomes_validos.append(os.path.basename(caminho))
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
    nomes_usados = []

    for corners, ids, nome in zip(todos_cantos_charuco, todos_ids_charuco, nomes_validos):
        # O método matchImagePoints cruza os IDs detectados com as coordenadas 3D do tabuleiro
        obj_p, img_p = board.matchImagePoints(corners, ids)
        
        # Adiciona à lista geral apenas se conseguiu fazer a correspondência corretamente
        if obj_p is not None and img_p is not None and len(obj_p) >= 4:
            obj_points.append(obj_p)
            img_points.append(img_p)
            nomes_usados.append(nome)

    # ---------- CALIBRAÇÃO ----------
    print("\nIniciando cálculo de calibração...")
    # CALIB_FIX_K3: numa webcam comum o termo radial de 6a ordem so e
    # "visto" nos cantos extremos da imagem. Sem pontos la, o otimizador
    # usa o k3 para compensar ruido e chega a valores absurdos (ja saiu
    # k3 = -1.26), que distorcem justamente as bordas da conversao pixel->mm.
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points,
        img_points,
        tamanho_img,
        None,
        None,
        flags=cv2.CALIB_FIX_K3,
    )

    # Erro por imagem: uma foto ruim (borrada, deteccao torta) aparece
    # aqui bem acima das outras e vale ser apagada antes de recalibrar.
    erros_por_imagem = []
    for obj_p, img_p, rvec, tvec in zip(obj_points, img_points, rvecs, tvecs):
        projetado, _ = cv2.projectPoints(obj_p, rvec, tvec, K, dist)
        erros_por_imagem.append(float(np.sqrt(np.mean(np.sum(
            (projetado.reshape(-1, 2) - img_p.reshape(-1, 2)) ** 2, axis=1
        )))))

    print("\n=== RESULTADO ===")
    print(f"Erro de reprojeção médio (RMS): {ret:.3f} px")
    if ret > 0.5:
        print("AVISO: RMS acima de 0.5 px. Confira as imagens com maior erro "
              "abaixo e se o foco estava travado durante as fotos.")
    print("Matriz da câmera (K):\n", K)
    print("Coeficientes de distorção (k1, k2, p1, p2, k3):\n", dist)

    print("\nErro de reprojeção por imagem (maiores primeiro):")
    for erro, nome in sorted(zip(erros_por_imagem, nomes_usados), reverse=True):
        print(f"  {erro:6.3f} px   {nome}")

    # ---------- SALVAR PARA AS PRÓXIMAS ETAPAS ----------
    caminho_saida = os.path.join(PASTA_DADOS, "calibracao_intrinseca.npz")
    os.makedirs(PASTA_DADOS, exist_ok=True)
    np.savez(caminho_saida, K=K, dist=dist, tamanho_img=tamanho_img, rms=ret)
    print(f"\nSalvo em {caminho_saida}")

    return K, dist


    def undistort_imagem(img, K, dist):
        """Remove a distorção de uma imagem usando os parâmetros calibrados."""
        h, w = img.shape[:2]
        novo_K, roi = cv2.getOptimalNewCameraMatrix(K, dist, (w, h), alpha=0)
        mapx, mapy = cv2.initUndistortRectifyMap(
            K, dist, None, novo_K, (w, h), cv2.CV_32FC1
        )
        return cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR), novo_K