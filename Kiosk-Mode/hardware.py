# hardware.py
import time
import RPi.GPIO as GPIO
from hx711 import HX711

SERVO_PIN = 17
DT = 5
SCK = 6
REFERENCE_UNIT = 2280

# Setup GPIO and HX711
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(SERVO_PIN, GPIO.OUT)

hx = HX711(DT, SCK)
hx.set_scale(REFERENCE_UNIT)
hx.tare()

servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

def activate_servo():
    print("Rotating servo...")
    servo_pwm.ChangeDutyCycle(2.5)  # 0?
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(7.5)  # 90?
    time.sleep(1)
    servo_pwm.ChangeDutyCycle(2.5)  # back to 0?
    time.sleep(0.5)
    servo_pwm.ChangeDutyCycle(0)

def get_weight(samples=5):
    values = [hx.get_weight() for _ in range(samples)]
    return sum(values) / len(values)

def tare_weight():
    hx.tare()

def cleanup():
    servo_pwm.stop()
    GPIO.cleanup()