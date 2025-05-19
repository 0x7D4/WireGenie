import os
import subprocess
import re
import qrcode
import signal
import tempfile
import atexit
import time
import sys

# === Configuration ===
WG_INTERFACE = "wg0"
WG_DIR = "/etc/wireguard"
CLIENT_DIR = os.path.join(WG_DIR, "clients")
PEER_LIST_FILE = os.path.join(WG_DIR, "peers.list")
WG_CONFIG_FILE = os.path.join(WG_DIR, f"{WG_INTERFACE}.conf")
SUBNET_PREFIX = "10.0.0"
SERVER_PORT = 51820
SERVER_PUBLIC_IP = subprocess.getoutput("curl -s ifconfig.me")
DNS = "1.1.1.1"

# Ensure directories
os.makedirs(CLIENT_DIR, exist_ok=True)

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def get_next_ip():
    try:
        with open(PEER_LIST_FILE, 'r') as f:
            used = re.findall(rf'{SUBNET_PREFIX}\.(\d+)', f.read())
        ips = [int(ip) for ip in used]
    except FileNotFoundError:
        ips = []
    next_ip = 2
    while next_ip in ips:
        next_ip += 1
    return f"{SUBNET_PREFIX}.{next_ip}"

def generate_server_config():
    server_priv_key = run("wg genkey")
    with open(WG_CONFIG_FILE, 'w') as f:
        f.write(f"[Interface]\n")
        f.write(f"Address = {SUBNET_PREFIX}.1/24\n")
        f.write(f"ListenPort = {SERVER_PORT}\n")
        f.write(f"PrivateKey = {server_priv_key}\n")
    return server_priv_key

def add_peer_config(name, pub_key, ip):
    peer_entry = f"\n[Peer]\n# {name}\nPublicKey = {pub_key}\nAllowedIPs = {ip}/32\n"
    with open(WG_CONFIG_FILE, 'a') as f:
        f.write(peer_entry)
    with open(PEER_LIST_FILE, 'a') as f:
        f.write(f"{name},{pub_key},{ip}\n")

def show_qr_terminal(config_path):
    os.system(f"qrencode -t ansiutf8 < {config_path}")

def create_client(name):
    priv = run("wg genkey")
    pub = run(f"echo {priv} | wg pubkey")
    ip = get_next_ip()

    add_peer_config(name, pub, ip)

    client_conf = f"""[Interface]
PrivateKey = {priv}
Address = {ip}/32
DNS = {DNS}

[Peer]
PublicKey = {get_server_pub_key()}
Endpoint = {SERVER_PUBLIC_IP}:{SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    client_path = os.path.join(CLIENT_DIR, f"{name}.conf")
    with open(client_path, 'w') as f:
        f.write(client_conf)

    img = qrcode.make(client_conf)
    img.save(os.path.join(CLIENT_DIR, f"{name}.png"))

    print(f"✅ Added {name} with IP {ip}")
    print("📱 Scan this QR code in your WireGuard app:")
    show_qr_terminal(client_path)

def get_server_pub_key():
    return run(f"wg pubkey < {WG_DIR}/server_private.key")

def monitor_peers():
    seen = set()
    while True:
        try:
            with open(PEER_LIST_FILE, 'r') as f:
                for line in f:
                    name, pub, ip = line.strip().split(',')
                    if name not in seen:
                        run(f"wg set {WG_INTERFACE} peer {pub} allowed-ips {ip}/32")
                        seen.add(name)
        except FileNotFoundError:
            pass
        time.sleep(5)

def signal_handler(sig, frame):
    print("\n🔻 Shutting down WireGuard...")
    run(f"wg-quick down {WG_INTERFACE}")
    print("🧹 WireGuard interface shut down.")
    exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(signal_handler, None, None)

    if not os.path.exists(WG_CONFIG_FILE):
        generate_server_config()

    if len(sys.argv) >= 3 and sys.argv[1] == "add":
        create_client(sys.argv[2])

    print("▶️ Starting WireGuard with server config...")
    try:
        run(f"wg-quick up {WG_INTERFACE}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Failed to bring up {WG_INTERFACE}: {e}\nTrying to continue...")

    print("👀 Monitoring peers for live updates...")
    monitor_peers()
