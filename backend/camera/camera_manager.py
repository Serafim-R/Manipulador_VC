import cv2

from backend.camera.camera_thread import CameraThread


class CameraManager:

    def __init__(self):

        self.cap = None
        self.thread = None

    def open(self):

        self.cap = cv2.VideoCapture(0)

        print("Camera aberta:", self.cap.isOpened())

        return self.cap.isOpened()

    def read(self):

        ok, frame = self.cap.read()

        if ok:
            return frame

        return None

    def close(self):

        if self.cap:

            self.cap.release()

    def start(self):

        if not self.open():
            return None

        self.thread = CameraThread(self)

        return self.thread

    def stop(self):

        if self.thread:

            self.thread.stop()

        self.close()