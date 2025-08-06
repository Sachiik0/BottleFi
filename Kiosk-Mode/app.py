from flask import Flask, request, render_template_string, redirect, session
from scanner import scan_bottle
from hardware import tare_weight
from tokens import store_code, claim_code, get_time, expire_check
import os
import threading

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Background timer for internet time expiry
threading.Thread(target=expire_check, args=(lambda ip: print(f"⏱️ Time expired for {ip}"),), daemon=True).start()

@app.route('/')
def index():
    return redirect('/kiosk-page')

# ----------- KIOSK PAGE -----------
@app.route('/kiosk-page', methods=['GET', 'POST'])
def kiosk_page():
    if 'pending_time' not in session:
        session['pending_time'] = 0

    message = ""
    code = ""

    if request.method == 'POST':
        if 'scan' in request.form:
            if scan_bottle():
                tare_weight()
                session['pending_time'] += 300
                message = "✅ Bottle accepted! +300s added."
            else:
                message = "❌ Bottle not accepted."
        elif 'generate' in request.form:
            if session['pending_time'] > 0:
                code = store_code("none", session['pending_time'])
                message = f"✅ Code generated for {session['pending_time']}s!"
                session['pending_time'] = 0
            else:
                message = "❌ No time to generate."

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kiosk Page</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background-color: #f0f2f5;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            .card {
                padding: 30px;
                border-radius: 16px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 class="mb-4">🧃 Kiosk Page</h2>
            <p><strong>Time Collected:</strong> {{ time }} seconds</p>
            {% if code %}
                <p class="fs-4"><strong>Generated Code:</strong> <span class="text-primary">{{ code }}</span></p>
            {% endif %}
            <p class="text-success">{{ message }}</p>
            <form method="post" class="d-grid gap-2">
                <button name="scan" type="submit" class="btn btn-success">Scan Bottle</button>
            </form>
            <form method="post" class="d-grid gap-2 mt-2">
                <button name="generate" type="submit" class="btn btn-primary">Generate Code</button>
            </form>
        </div>
    </body>
    </html>
    """, time=session.get('pending_time', 0), code=code, message=message)

# ----------- USER PAGE -----------
@app.route('/user-page', methods=['GET', 'POST'])
def user_page():
    ip = request.remote_addr
    message = ""
    remaining_time = get_time(ip)

    if request.method == 'POST':
        input_code = request.form.get('code')
        success, time_value = claim_code(ip, input_code)
        if success:
            message = f"✅ Code claimed! +{time_value}s"
            remaining_time = get_time(ip)
        else:
            message = "❌ Invalid or expired code."

    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>User Page</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {
                background-color: #f9f9f9;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            .card {
                padding: 30px;
                border-radius: 16px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2 class="mb-4">🔐 User Page</h2>
            <p><strong>Time Remaining:</strong> {{ time }} seconds</p>
            <form method="post">
                <input type="text" name="code" placeholder="Enter code here" class="form-control mb-3" required>
                <button type="submit" class="btn btn-primary w-100">Claim Code</button>
            </form>
            <p class="text-success mt-2">{{ message }}</p>
        </div>
    </body>
    </html>
    """, time=remaining_time, message=message)

# ----------- RUN APP -----------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)