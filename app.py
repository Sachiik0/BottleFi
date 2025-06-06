
from flask import Flask, request, render_template_string, redirect
import subprocess
import threading
import time
import cv2
from ultralytics import YOLO
from hx711 import HX711
import RPi.GPIO as GPIO

app = Flask(__name__)

# Load YOLOv8n model
model = YOLO('yolov8n.pt')

# HX711 setup
hx = HX711(5, 6)
try:
    hx.tare()
    print("Tare complete. Starting weight should be 0g.")
except AttributeError:
    print("Tare method not available in HX711 library.")

REFERENCE_UNIT = 2280

def get_weight():
    raw_weight = hx.get_weight(5)
    calibrated_weight = raw_weight / REFERENCE_UNIT
    return calibrated_weight

# Servo setup
SERVO_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for SG90
servo_pwm.start(0)  # Initial position

def move_servo():
    print("Rotating servo...")
    servo_pwm.ChangeDutyCycle(2.5)  # 0°
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(7.5)  # 90°
    time.sleep(1)
    servo_pwm.ChangeDutyCycle(2.5)  # back to 0°
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)  # Stop signal

user_times = {}
lock = threading.Lock()

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
            remove_ips = []
            for ip, seconds in list(user_times.items()):
                if seconds > 0:
                    user_times[ip] -= 1
                if user_times[ip] <= 0:
                    block_internet(ip)
                    remove_ips.append(ip)
            for ip in remove_ips:
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

            if cls == 39 and (width > 100 or height > 100):
                print(f"Bottle detected: {width:.1f}x{height:.1f}")
                cap.release()
                return True

        if time.time() - start_time > timeout:
            print("Timeout: No bottle detected")
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

    weight = get_weight()
    print(f"Weight detected: {weight:.2f}g")

    if weight > 150:
        return f"Bottle too heavy ({weight:.2f}g). Max is 150g.", 400

    bottle_detected = scan_bottle()

    if bottle_detected:
        with lock:
            user_times[ip] = user_times.get(ip, 0) + 60  # Add 1 minute
        move_servo()  # 🚀 Trigger servo movement after accepted bottle
        return redirect('/')
    else:
        return "Bottle not detected or too small. Try again.", 400

@app.route('/claim', methods=['POST'])
def claim():
    ip = get_client_ip()
    with lock:
        if user_times.get(ip, 0) > 0:
            grant_internet(ip)
            return redirect('/')
        else:
            return "No internet time to claim. Insert a bottle first.", 400

if __name__ == '__main__':
    try:
        threading.Thread(target=internet_timer, daemon=True).start()
        app.run(host='0.0.0.0', port=80)
    finally:
        servo_pwm.stop()
        GPIO.cleanup()
	
