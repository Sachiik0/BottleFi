from flask import Flask, request, render_template_string, redirect
import subprocess
import threading
import time
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# Load YOLOv8n model (make sure ultralytics installed and model available)
model = YOLO('yolov8n.pt')

# Store user internet time left: {client_ip: seconds}
user_times = {}

# Lock to avoid race condition on user_times
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
    # Behind proxy? Use request.headers.get('X-Forwarded-For') if needed
    return request.remote_addr

def grant_internet(ip):
    # Remove blocking iptables rule for this IP
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"Granted internet to {ip}")

def block_internet(ip):
    # Add iptables DROP rule for this IP
    subprocess.run(["sudo", "iptables", "-D", "FORWARD", "-s", ip, "-j", "DROP"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["sudo", "iptables", "-I", "FORWARD", "-s", ip, "-j", "DROP"])
    print(f"Blocked internet to {ip}")

def internet_timer():
    while True:
        time.sleep(1)
        with lock:
            remove_ips = []
            for ip, seconds in user_times.items():
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

            # Class 39 corresponds to 'bottle' in COCO
            if cls == 39 and (width > 100 or height > 100):
                print(f"Bottle detected with size: {width:.1f}x{height:.1f}")
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
            user_times[ip] = user_times.get(ip, 0) + 60  # +1 minute
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
