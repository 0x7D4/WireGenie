from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import wg
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key'
auth = HTTPBasicAuth()

# Replace with secure values or load from env/secret storage
users = {
    "admin": generate_password_hash("admin")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username

@app.route('/')
@auth.login_required
def index():
    clients = []
    try:
        with open(wg.WG_CONFIG) as f:
            for line in f:
                if line.strip().startswith("#"):
                    clients.append(line.strip().lstrip("#").strip())
    except Exception as e:
        flash(f"Error loading clients: {str(e)}", "danger")
    return render_template('index.html', clients=clients)

@app.route('/add', methods=['POST'])
@auth.login_required
def add_client():
    name = request.form.get('client_name', '').strip()
    if not name:
        flash("Client name cannot be empty.", "warning")
    else:
        try:
            wg.generate_client(name)
            flash(f"Client '{name}' added successfully!", "success")
            return redirect(url_for('show_qr', name=name))
        except Exception as e:
            flash(f"Failed to add client: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/remove/<name>')
@auth.login_required
def remove_client(name):
    try:
        wg.remove_client(name)
        flash(f"Client '{name}' removed successfully!", "success")
    except Exception as e:
        flash(f"Failed to remove client: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/shutdown')
@auth.login_required
def shutdown():
    try:
        wg.turn_off_wireguard()
        flash("WireGuard interface has been brought down.", "info")
    except Exception as e:
        flash(f"Error shutting down interface: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/qr/<name>')
@auth.login_required
def show_qr(name):
    config_path = os.path.join(wg.CLIENT_DIR, f"{name}.conf")
    if not os.path.exists(config_path):
        flash("Client config not found.", "danger")
        return redirect(url_for('index'))

    qr_file = f"/tmp/{name}_qr.png"
    try:
        subprocess.run(["qrencode", "-o", qr_file, "-r", config_path], check=True)
        return render_template('qr.html', name=name, qr_file=f"/download_qr/{name}")
    except Exception as e:
        flash(f"Error generating QR code: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/download_qr/<name>')
@auth.login_required
def download_qr(name):
    qr_file = f"/tmp/{name}_qr.png"
    if os.path.exists(qr_file):
        return send_file(qr_file, mimetype='image/png')
    flash("QR code not found.", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
