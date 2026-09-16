import os

from ultralytics import YOLO


# Caminho padrao dos pesos treinados, relativo a raiz do projeto
DEFAULT_WEIGHTS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "yolo",
    "pesos",
    "last.pt"
)


class YOLODetector:
    """
    Encapsula o modelo YOLOv12 treinado. Recebe um frame (BGR, formato
    do OpenCV) e devolve o frame anotado com as caixas + a lista de
    deteccoes encontradas.
    """

    def __init__(self, weights_path=DEFAULT_WEIGHTS, conf=0.5):

        if not os.path.exists(weights_path):
            raise FileNotFoundError(
                f"Pesos do YOLO nao encontrados em: {weights_path}"
            )

        print("Carregando modelo YOLO:", weights_path)

        self.model = YOLO(weights_path)
        self.conf = conf

        print("Modelo YOLO carregado. Classes:", self.model.names)

    def detect(self, frame):
        """
        frame: imagem BGR (numpy array), como vem do cv2.VideoCapture

        Retorna (annotated_frame, detections):
          - annotated_frame: copia do frame com as caixas desenhadas (BGR)
          - detections: lista de dicts {"class", "confidence", "bbox"}
        """

        results = self.model.predict(
            frame,
            conf=self.conf,
            verbose=False
        )

        result = results[0]

        # imagem ja anotada (BGR) gerada pelo proprio ultralytics
        annotated_frame = result.plot()

        detections = []

        for box in result.boxes:

            cls_id = int(box.cls[0])
            cls_name = self.model.names[cls_id]
            confidence = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()

            detections.append({
                "class": cls_name,
                "confidence": confidence,
                "bbox": xyxy
            })

        return annotated_frame, detections
