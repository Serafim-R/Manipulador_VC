import cv2

cap = cv2.VideoCapture(
    0,
    cv2.CAP_V4L2
)

print(cap.isOpened())

while True:

    ok, frame = cap.read()

    if not ok:
        break

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()