import random
import threading

user_times = {}
lock = threading.Lock()

def generate_code():
    return ''.join(random.choices('0123456789', k=6))

def store_code(ip, seconds):
    code = generate_code()
    with lock:
        user_times[code] = {'ip': ip, 'time': seconds}
    return code

def claim_code(ip, code):
    with lock:
        data = user_times.get(code)
        if not data:
            return False, 0
        time_value = data['time']
        user_times[ip] = user_times.get(ip, 0) + time_value
        del user_times[code]
        return True, time_value

def get_time(ip):
    with lock:
        return user_times.get(ip, 0) if isinstance(user_times.get(ip, 0), int) else 0

def add_timer(ip, seconds):
    with lock:
        user_times[ip] = user_times.get(ip, 0) + seconds

def expire_check(callback):
    import time
    while True:
        time.sleep(1)
        expired = []
        with lock:
            for ip, val in list(user_times.items()):
                if isinstance(val, int):
                    user_times[ip] -= 1
                    if user_times[ip] <= 0:
                        expired.append(ip)
        for ip in expired:
            callback(ip)