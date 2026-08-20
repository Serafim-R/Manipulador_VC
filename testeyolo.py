import cv2
from ultralytics import YOLO

# Carrega o modelo
model = YOLO('yolo/pesos/last.pt')

# Abre a câmera (0 é a webcam/câmera padrão)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Processa a inferência no frame atual
    results = model(frame, conf=0.3)

    # Desenha as detecções na imagem
    annotated_frame = results[0].plot()

    # Mostra a imagem na tela
    cv2.imshow("Teste YOLOv12 - Raspberry Pi 5", annotated_frame)

    # Pressione a tecla 'q' para encerrar
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()