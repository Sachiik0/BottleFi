# BottleFi

BottleFi is a smart recycling kiosk that incentivizes plastic bottle disposal by granting internet access time to users. It operates on a Raspberry Pi with a connected weight sensor and optional internet access control.

## Features

- Scan bottles and accumulate time
- Generate time codes based on scans
- Redeem codes to gain internet access
- Kiosk and user-friendly web interfaces

## Requirements

- Raspberry Pi (tested on RPi 4)
- Load Cell + HX711
- Internet access (via router or hotspot)
- Python 3
- Flask
- GPIO access libraries (`RPi.GPIO` or `gpiozero`)
- Chromium (for kiosk display)

## Installation

```bash
# Clone the repository
git clone https://github.com/Sachiik0/BottleFi.git
cd BottleFi

# Install dependencies
sudo apt update
sudo apt install python3-pip python3-flask chromium-browser
pip3 install flask

# Optional: Install GPIO libraries if not already installed
sudo apt install python3-rpi.gpio

# Enable necessary services
sudo systemctl enable pigpiod.service
sudo systemctl start pigpiod.service
```

## Autostart Configuration

To launch BottleFi automatically on boot in kiosk mode:

### 1. Kiosk Autostart for Chromium

Edit the autostart file:

```bash
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
```

Add the following lines at the end:

```
@xset s off
@xset -dpms
@xset s noblank
@chromium-browser --noerrdialogs --kiosk http://localhost:5000/kiosk-page
```

### 2. Start the Flask App Automatically

Create a shell script `bottle-detect.sh`:

```bash
nano ~/bottle-detect.sh
```

Insert:

```bash
#!/bin/bash
cd ~/BottleFi
flask run --host=0.0.0.0 --port=5000
```

Make it executable:

```bash
chmod +x ~/bottle-detect.sh
```

Then add it to `.bashrc` to run on terminal login:

```bash
nano ~/.bashrc
```

Add this line at the bottom:

```
bash ~/bottle-detect.sh &
```

## Usage

- Go to your Kiosk screen and scan bottles
- Time will accumulate
- Generate a time code when you're done
- Users can go to the user page and input the code to claim internet time

## Repository

https://github.com/Sachiik0/BottleFi
