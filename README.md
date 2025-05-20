# WireGenie – WireGuard Management Tool

**WireGenie** is a Python-based tool that simplifies the management of a WireGuard VPN server on Linux systems. It includes both a **command-line interface (CLI)** and a **Flask-based Web UI** for easy administration.

---

## 🚀 Features

### ✅ CLI (`wg.py`)
- Add, remove, and list WireGuard clients.
- Automatically restarts the WireGuard service after changes.
- Ensures configuration validity before applying.
- Brings down `wg0` on exit or termination.
- Optionally displays QR code on the terminal (if `qrencode` is installed).

### ✅ Web UI (`web_ui.py`)
- Simple Web Dashboard built with **Flask**.
- Protected by **Basic Authentication** (username/password).
- Easily **add or remove clients** from the browser.
- Automatically displays a **QR code** for newly added clients.
- Accessible via local network or public server IP.

---

## 📦 Requirements

### 🔧 System Dependencies

Install these on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install wireguard iptables curl iproute2 qrencode
```

### 🐍 Python Dependencies

```bash
pip3 install flask flask-httpauth
```

> ✅ Ensure Python 3.6+ is installed:
> ```bash
> python3 --version
> ```

---

## 📁 Project Structure

```
WireGenie/
├── wg.py              # CLI management tool
├── web_ui.py          # Flask Web UI with Basic Auth + QR support
└── templates/
    ├── index.html     # Main dashboard
    └── qr.html        # QR display page for clients
```

---

## 🔧 Setup & Usage

### 1. Clone the Repository

```bash
git clone https://github.com/0x7D4/WireGenie.git
cd WireGenie
```

### 2. Disable systemd `wg-quick@wg0` (Recommended)

To prevent conflicts with the script:

```bash
sudo systemctl disable wg-quick@wg0
sudo systemctl stop wg-quick@wg0
```

---

## ⚙️ CLI Usage

### Start the CLI Menu

```bash
sudo python3 wg.py
```

### Menu Options

```
1. Add a new client
2. Remove an existing client
3. List clients
4. Exit
```

---

## 🌐 Web UI Usage

### 1. Start the Flask Server

```bash
sudo python3 web_ui.py
```

### 2. Open in Your Browser

```
http://<your-server-ip>:5000
```

### 3. Login Credentials (Default)

```
Username: admin
Password: admin
```

> 🔒 You can change this inside `web_ui.py` in the `users` dictionary.

---

## 📸 QR Code Display

After adding a client through the Web UI, you are redirected to a page that shows the client’s config as a **QR code**.  
You can scan it using the **WireGuard mobile app** for easy setup.

---

## 📂 Configuration Paths

| Component             | Path                                |
|-----------------------|-------------------------------------|
| Server Config         | `/etc/wireguard/wg0.conf`           |
| Client Configs        | `/etc/wireguard/clients/<name>.conf`|
| Server Private Key    | `/etc/wireguard/server_private.key` |
| Server Public Key     | `/etc/wireguard/server_public.key`  |

---

## 🧪 Example CLI Session

```bash
$ sudo python3 wg.py
What would you like to do?
1. Add a new client
2. Remove an existing client
3. List clients
4. Exit
Enter choice [1-4]: 1
Enter client name: alice
✅ Client alice added and service restarted.
```

---

## 🔐 Security Notes

- The Flask Web UI is protected with **Basic Authentication**.

---

## 📌 To Do / Coming Soon

- `.env` support for environment-based configuration
---
