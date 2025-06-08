from flask import Flask, request, render_template_string, redirect
import subprocess
import threading
import time
import cv2
from ultralytics import YOLO
from hx711 import HX711
import pigpio

app = Flask(__name__)

model = YOLO('yolov8n.pt')  # Load YOLO model

# HX711 setup
hx = HX711(5, 6)
hx.set_scale(2280)
hx.tare()
print("HX711 tared. Ready to measure weight.")

# pigpio for servo control
SERVO_GPIO = 17
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio daemon")

def activate_servo():
    print("Activating servo...")
    pi.set_servo_pulsewidth(SERVO_GPIO, 1000)
    time.sleep(1)
    pi.set_servo_pulsewidth(SERVO_GPIO, 2000)
    time.sleep(1)
    pi.set_servo_pulsewidth(SERVO_GPIO, 0)
    print("Servo movement complete")

# Track internet time
user_times = {}
lock = threading.Lock()

HTML_PAGE = """
<html><body>
<h2>Welcome to BottleScan Captive Portal</h2>
<p>Your IP: {{ ip }}</p>
<p>Internet Access Time Left: {{ time_left }} seconds</p>
{% if time_left == 0 %}
<p style="color:red;">Internet access blocked until you insert a bottle.</p>
{% endif %}
<form method="POST" action="/insert">
    <button type="submit">Insert Bottle (Scan)</button>
</form>
</body></html>
"""

def get_client_ip():
    return request.remote_addr

def grant_internet(ip):
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[+] Granted internet to {ip}")

def block_internet(ip):
    # Remove and re-add rule to ensure blocking
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "iptables", "-I", "FORWARD", "-s", ip, "-j", "DROP"])
    print(f"[-] Blocked internet to {ip}")

def internet_timer():
    while True:
        time.sleep(1)
        with lock:
            expired_ips = []
            for ip in list(user_times):
                if user_times[ip] > 0:
                    user_times[ip] -= 1
                    if user_times[ip] == 0:
                        block_internet(ip)
                        print(f"[!] Time expired for {ip}")
            # Don't delete the IP so they stay blocked and visible on the page

def scan_bottle(timeout=5, max_weight=150):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return False

    start_time = time.time()
    bottle_detected = False

    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        results = model(frame)[0]
        for box in results.boxes:
            cls = int(box.cls.cpu().numpy())
            if cls == 39:  # Bottle class
                bbox = box.xyxy[0].cpu().numpy()
                xmin, ymin, xmax, ymax = bbox
                width, height = xmax - xmin, ymax - ymin

                if width > 100 or height > 340:
                    print(f"Bottle detected: {width:.1f}x{height:.1f}")
                    bottle_detected = True
                    break

        if bottle_detected:
            break

    cap.release()

    if bottle_detected:
        print("Measuring weight...")
        weight = hx.get_weight(5)
        print(f"Weight: {weight:.2f} g")

        if weight <= max_weight:
            print("Bottle accepted")
            activate_servo()
            return True
        else:
            print("Bottle rejected: too heavy")
            return False
    else:
        print("No bottle detected")
        return False

@app.route('/', methods=['GET'])
def index():
    ip = get_client_ip()
    with lock:
        if ip not in user_times:
            user_times[ip] = 0
            block_internet(ip)  # Force block immediately on first visit
        time_left = user_times[ip]
    return render_template_string(HTML_PAGE, ip=ip, time_left=time_left)

@app.route('/insert', methods=['POST'])
def insert():
    ip = get_client_ip()
    if scan_bottle():
        with lock:
            user_times[ip] = user_times.get(ip, 0) + 60
            hx.tare()
            print("Scale reset to 0g")
            grant_internet(ip)  # Auto-claim internet
        return redirect('/')
    else:
        return "Bottle not detected, too heavy, or too small. Try again.", 400

if __name__ == '__main__':
    try:
        subprocess.run(["sudo", "iptables", "-F", "FORWARD"])  # Clear iptables on start
        threading.Thread(target=internet_timer, daemon=True).start()
        app.run(host='0.0.0.0', port=80)
    finally:
        pi.stop()
