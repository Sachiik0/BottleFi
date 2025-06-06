# BottleDetect: Smart Recycling Captive Portal

This project sets up a smart recycling kiosk using a Raspberry Pi 4B that detects bottles using a YOLOv8 object detection model and a weight sensor (HX711). Users insert a plastic bottle to gain internet access via a captive portal.

## 🧰 Hardware Requirements

* Raspberry Pi 4 Model B (4GB or 8GB recommended)
* HX711 Load Cell Amplifier + Weight Sensor (e.g., 1kg strain gauge)
* SG90 Servo Motor
* USB Camera (compatible with OpenCV)
* Jumper Wires
* Breadboard (optional)

## 📦 Software Requirements

* Raspberry Pi OS (Bookworm/Bullseye)
* Python 3.9+
* Flask
* OpenCV
* Ultralytics YOLOv8
* RPi.GPIO
* HX711 Python Library

## 📲 Setup Instructions

### 1. 🔌 Prepare Raspberry Pi OS

* Flash Raspberry Pi OS using Raspberry Pi Imager.
* Connect RPi to monitor, keyboard, and internet (or SSH).
* Enable camera: `sudo raspi-config`
* Update system:

  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

### 2. 🛠 Install Dependencies

```bash
sudo apt install python3-pip python3-opencv libatlas-base-dev -y
pip3 install flask opencv-python ultralytics RPi.GPIO
```

Install HX711 library (save as `hx711.py` or use a pip version if available):

```bash
wget https://raw.githubusercontent.com/tatobari/hx711py/master/hx711.py
```

### 3. 📂 Clone Project Files

```bash
git clone https://github.com/yourusername/bottledetect.git
cd bottledetect
```

Place your YOLOv8n model file in the same directory:

```bash
# You can get yolov8n.pt from Ultralytics
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
```

### 4. 🧪 Test the Script

```bash
python3 app.py
```

Visit `http://<RPi-IP>` on a device connected to the same network. Use the buttons to simulate bottle detection and grant internet access.

### 5. 🌐 Internet Access Control (iptables)

Run these commands to allow IP-based internet restriction:

```bash
sudo iptables -I FORWARD -s 0.0.0.0/0 -j DROP
```

The script will manage IP-specific unblock/drop rules dynamically.

### 6. ⚙️ Setup as a Systemd Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/bottledetect.service
```

Paste the following:

```ini
[Unit]
Description=Bottle Detection Captive Portal
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/bottledetect/app.py
WorkingDirectory=/home/pi/bottledetect
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable bottledetect.service
sudo systemctl start bottledetect.service
sudo systemctl status bottledetect.service
```

To view logs:

```bash
journalctl -u bottledetect.service -f
```

### 7. 🔧 Configure Camera and Servo Wiring

* **Servo Motor** (SG90): Connect signal wire to GPIO 17
* **HX711**: DT to GPIO 5, SCK to GPIO 6
* **Camera**: USB webcam or CSI camera

## 📷 How it Works

1. User accesses the captive portal.
2. On clicking "Insert Bottle", weight and visual detection are triggered.
3. If valid (YOLO detects a plastic bottle, and weight < 150g), servo activates.
4. Internet is granted to user IP for 60 seconds.

## 👨‍💻 Author

Marc Anthony M. San Juan

