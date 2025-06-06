from flask import Flask, request, render_template_string, redirect
import subprocess
import threading
import time
import cv2
from ultralytics import YOLO

# Servo control imports
from gpiozero import Servo
from time import sleep
import os

# Ensure gpiozero uses the native pin factory (needed if running as root)
os.environ["GPIOZERO_PIN_FACTORY"] = "native"

app = Flask(__name__)

# Load YOLOv8n model (make sure ultralytics is installed and yolov8n.pt is available)
model = YOLO('yolov8n.pt')

# Initialize servo on GPIO pin 17
servo = Servo(17)

# Store user internet time left: {client_ip: seconds}
user_times = {}

# Lock to avoid race conditions on user_times
lock = threading.Lock()

# HTML template with Insert (scan) and Claim buttons
HTML_PAGE = """
<html><body>
  <h2>Welcome to BottleScan Captive Portal</h2>
  <p>Your IP: {{ ip }}</p>
  <p>Internet Access Time Left: {{ time_left }} seconds</p>
  <form method="POST" action="/insert">
      <button type="submit">Insert Bottle (Scan)</button>
  </form>
  <form method="POST" action="/claim">
      <button type="submit">Claim Access</button>
  </form>
</body></html>
"""

def get_client_ip():
    # If behind a proxy, you might need to use X-Forwarded-For:
    # return request.headers.get('X-Forwarded-For', request.remote_addr)
    return request.remote_addr

def grant_internet(ip):
    # Remove any existing DROP rule (in case it's there), then allow traffic
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Granted internet to {ip}")

def block_internet(ip):
    # Remove any existing DROP rule first, then insert a new one
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "iptables", "-I", "FORWARD", "-s", ip, "-j", "DROP"])
    print(f"Blocked internet to {ip}")

def internet_timer():
    """
    Background thread that decrements each user's remaining time every second.
    When time hits zero, block their internet and remove them from user_times.
    """
    while True:
        time.sleep(1)
        with lock:
            to_remove = []
            for ip, remaining in user_times.items():
                if remaining > 0:
                    user_times[ip] = remaining - 1
                if user_times[ip] <= 0:
                    # Time is up: block internet and mark for removal
                    block_internet(ip)
                    to_remove.append(ip)
            for ip in to_remove:
                user_times.pop(ip, None)

def scan_bottle(timeout=10):
    """
    Capture frames from the default camera and run YOLO inference until a bottle is detected
    (class 39 in COCO) with sufficient size, or until timeout.
    When a bottle is detected, trigger the servo to open/close and return True.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return False

    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Run the YOLO model on the current frame
        results = model(frame)[0]

        for box in results.boxes:
            bbox = box.xyxy[0].cpu().numpy()
            xmin, ymin, xmax, ymax = bbox
            width = xmax - xmin
            height = ymax - ymin
            cls = int(box.cls.cpu().numpy())

            # Class 39 corresponds to "bottle" in COCO; check size threshold
            if cls == 39 and (width > 100 or height > 100):
                print(f"Bottle detected with size: {width:.1f}x{height:.1f}")

                # Move servo to "open" position
                servo.max()
                sleep(1)         # Hold for 1 second
                servo.min()      # Move back to "closed" position

                cap.release()
                return True

        # Check for timeout
        if time.time() - start_time > timeout:
            print("Timeout reached, no bottle detected")
            break

    cap.release()
    return False

@app.route('/', methods=['GET'])
def index():
    ip = get_client_ip()
    with lock:
        time_left = user_times.get(ip, 0)
    return render_template_string(HTML_PAGE, ip=ip, time_left=time_left)

@app.route('/insert', methods=['POST'])
def insert():
    ip = get_client_ip()
    bottle_detected = scan_bottle()
    if bottle_detected:
        with lock:
            # Add 60 seconds of internet time for this IP
            user_times[ip] = user_times.get(ip, 0) + 60
        return redirect('/')
    else:
        return "Bottle not detected or too small, try again", 400

@app.route('/claim', methods=['POST'])
def claim():
    ip = get_client_ip()
    with lock:
        if user_times.get(ip, 0) > 0:
            grant_internet(ip)
            return redirect('/')
        else:
            return "No internet time to claim; insert bottle first", 400

if __name__ == '__main__':
    # Start the internet timer thread
    threading.Thread(target=internet_timer, daemon=True).start()
    # Run Flask app on port 80, accessible from any interface
    app.run(host='0.0.0.0', port=80)
