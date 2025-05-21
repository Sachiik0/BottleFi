import cv2
from ultralytics import YOLO

# Load the YOLOv8n model
model = YOLO('yolov8n.pt')

# Define the class name for bottle
BOTTLE_CLASS_ID = 39  # COCO class ID for 'bottle'

# Open a webcam stream (0 for default camera)
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Run detection
    results = model(frame)[0]

    # Iterate over the detected objects
    for box in results.boxes:
        class_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        height_pixels = y2 - y1

        # Only detect bottles
        if class_id == BOTTLE_CLASS_ID:
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"Bottle: {height_pixels}px"
            cv2.putText(frame, label, (x1, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Display the frame
    cv2.imshow('Bottle Detection', frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
