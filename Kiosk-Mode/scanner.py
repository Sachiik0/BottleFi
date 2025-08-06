import time
import cv2
from ultralytics import YOLO
from hardware import get_weight, activate_servo

model = YOLO('yolov8n.pt')

def scan_bottle(timeout=5, max_weight=150):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False

    start_time = time.time()
    bottle_detected = False

    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame)[0]
        for box in results.boxes:
            cls = int(box.cls.cpu().numpy())
            if cls == 39:
                xmin, ymin, xmax, ymax = box.xyxy[0].cpu().numpy()
                width, height = xmax - xmin, ymax - ymin
                if width > 100 or height > 310:
                    bottle_detected = True
                    break
        if bottle_detected:
            break
    cap.release()

    if bottle_detected:
        try:
            weight = get_weight()
            if weight <= max_weight:
                activate_servo()
                return True
        except:
            return False
    return False
