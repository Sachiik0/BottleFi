from flask import Flask, request, render_template_string, redirect
import subprocess
import threading
import time
import cv2
from ultralytics import YOLO
from gpiozero import PWMOutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory

# Use PiGPIO backend for proper PWM control
factory = PiGPIOFactory()
servo = PWMOutputDevice(17, pin_factory=factory, frequency=50)

app = Flask(__name__)

# Load YOLOv8n model
model = YOLO('yolov8n.pt')

# IP -> time left in seconds
user_times = {}
lock = threading.Lock()

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>BottleScan Captive Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Montserrat', sans-serif;
            background: #f0f2f5;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .card {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
            text-align: center;
            width: 100%;
            max-width: 400px;
        }
        h2 {
            margin-bottom: 1rem;
            color: #333;
        }
        p {
            margin: 0.5rem 0;
            color: #555;
        }
        form {
            margin-top: 1.5rem;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            margin: 0.5rem;
            transition: background-color 0.3s ease;
        }
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="card">
        <h2>Welcome to BottleScan</h2>
        <p><strong>Your IP:</strong> {{ ip }}</p>
        <p><strong>Internet Access Time Left:</strong> {{ time_left }} seconds</p>
        <form method="POST" action="/insert">
            <button type="submit">Insert Bottle (Scan)</button>
        </form>
        <form method="POST" action="/claim">
            <button type="submit">Claim Internet Access</button>
        </form>
    </div>
</body>
</html>
"""


def get_client_ip():
    return request.remote_addr

def grant_internet(ip):
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Granted internet to {ip}")

def block_internet(ip):
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "iptables", "-I", "FORWARD", "-s", ip, "-j", "DROP"])
    print(f"Blocked internet to {ip}")

def internet_timer():
    while True:
        time.sleep(1)
        with lock:
            expired_ips = []
            for ip, seconds in user_times.items():
                if seconds > 0:
                    user_times[ip] -= 1
                if user_times[ip] <= 0:
                    block_internet(ip)
                    expired_ips.append(ip)
            for ip in expired_ips:
                user_times.pop(ip)

def scan_bottle(timeout=10):
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

        results = model(frame)[0]

        for box in results.boxes:
            bbox = box.xyxy[0].cpu().numpy()
            xmin, ymin, xmax, ymax = bbox
            width = xmax - xmin
            height = ymax - ymin
            cls = int(box.cls.cpu().numpy())

            if cls == 39 and (width > 100 or height > 100):  # bottle class
                print(f"Bottle detected with size: {width:.1f}x{height:.1f}")
                
                # Activate continuous rotation servo
                servo.value = 1.0  # rotate one direction
                time.sleep(1)
                servo.value = -1.0  # rotate opposite direction
                time.sleep(1)
                servo.value = 0.0  # stop

                cap.release()
                return True

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
            return "No internet time to claim, insert bottle first", 400

if __name__ == '__main__':
    threading.Thread(target=internet_timer, daemon=True).start()
    app.run(host='0.0.0.0', port=80)
