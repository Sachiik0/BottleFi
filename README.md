BottleDetect: Smart Bottle Scanner with Internet Access Control

This project allows Raspberry Pi 4B to detect bottle insertions using object detection (YOLOv8), weight sensing (HX711), and servo actuation. Users are granted temporary internet access through IP-based firewall rules when a valid bottle is inserted.

📦 Features

Detects plastic bottles using YOLOv8.

Validates bottle weight using HX711 load cell.

Grants 1 minute of internet access per bottle.

Controls internet access using iptables.

Servo actuation simulates bottle intake.

Simple web interface for interaction.

🧰 Hardware Requirements

Raspberry Pi 4B

USB webcam

HX711 module + Load cell

Servo motor (SG90)

Breadboard + jumper wires

🔧 Software Requirements

🐍 Python Dependencies

Install all Python dependencies with:

pip install -r requirements.txt

requirements.txt contents:

flask
opencv-python
ultralytics
RPi.GPIO
hx711

💡 Note: If hx711 is not found in PyPI, use a GitHub repo or manually install the library you're using.

🚀 Setup Instructions

1. 🔌 Prepare the Raspberry Pi

sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-opencv git iptables -y

2. 🧠 Clone this repository

git clone https://github.com/yourusername/bottledetect.git
cd bottledetect

3. 🔽 Install Python Dependencies

pip3 install -r requirements.txt

4. 🧠 Download YOLOv8 Model

# Model used: yolov8n (nano version)
python3 -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

🧪 Test the Application

Run the Flask app:

sudo python3 app.py

Visit http://<RPI-IP> in your browser.

⚙️ Set Up as a Systemd Service

Create a systemd service file:

# /etc/systemd/system/bottledetect.service
[Unit]
Description=BottleDetect Flask Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/bottledetect/app.py
WorkingDirectory=/home/pi/bottledetect
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target

Enable and start:

sudo systemctl daemon-reload
sudo systemctl enable bottledetect.service
sudo systemctl start bottledetect.service
sudo systemctl status bottledetect.service

Check logs:

journalctl -u bottledetect.service -f

📡 SSH into Raspberry Pi

ssh pi@<RPI-IP>

Replace <RPI-IP> with your Raspberry Pi's actual IP address.

🔒 IPTables Setup

Ensure the default rule is to block all forwarded IPs:

sudo iptables -P FORWARD DROP

The app automatically manages IP rules using:

iptables -D FORWARD -s <ip> -j DROP (remove drop rule)

iptables -I FORWARD -s <ip> -j DROP (insert drop rule)
