import cv2
import os
import time
from datetime import datetime

CAMERA_ID = 0

WIDTH = 1280
HEIGHT = 720

WARMUP_TIME = 3.0

SAVE_FOLDER = "capturas_dataset"

os.makedirs(SAVE_FOLDER, exist_ok=True)

camera = cv2.VideoCapture(CAMERA_ID)

if not camera.isOpened():
    print("Erro: não foi possível abrir a câmera.")
    exit()


camera.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

print("Inicializando câmera...")
print(f"Warm-up de {WARMUP_TIME:.1f} segundos...")

inicio = time.time()

while time.time() - inicio < WARMUP_TIME:

    ret, frame = camera.read()

    if not ret:
        print("Erro ao capturar frame.")
        continue

    frame_display = frame.copy()

    cv2.putText(
        frame_display,
        "Aquecendo camera...",
        (30, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 255),
        2
    )

    cv2.imshow("Camera", frame_display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q") or key == 27:
        camera.release()
        cv2.destroyAllWindows()
        exit()


print("Warm-up concluido.")

print()
print("Controles:")
print("S -> salvar imagem")
print("Q -> sair")
print("ESC -> sair")

contador = 0

while True:

    ret, frame_original = camera.read()

    if not ret:
        print("Erro ao capturar imagem.")
        break

    frame_display = frame_original.copy()

    cv2.putText(
        frame_display,
        "S: salvar | Q/ESC: sair",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 0),
        2
    )

    cv2.imshow("Camera", frame_display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):

        contador += 1

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        nome_arquivo = (f"captura_{contador:04d}_{timestamp}.jpg")

        caminho = os.path.join(SAVE_FOLDER,nome_arquivo)

        sucesso = cv2.imwrite(
            caminho,
            frame_original
        )

        if sucesso:

            print(f"Imagem salva: {caminho}")

            feedback = frame_display.copy()

            cv2.putText(
                feedback,
                "CAPTURA SALVA!",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),
                3
            )

            cv2.imshow("Camera", feedback)

            cv2.waitKey(300)

    elif key == ord("q") or key == 27:
        break

camera.release()
cv2.destroyAllWindows()

print("Camera encerrada.")