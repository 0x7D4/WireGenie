#!/usr/bin/env python3

import os
import re
import subprocess
import sys
import time
import signal
import atexit
from pathlib import Path

# === Configuration ===
WG_INTERFACE = "wg0"
WG_DIR = "/etc/wireguard"
CLIENT_DIR = f"{WG_DIR}/clients"
WG_CONFIG = f"{WG_DIR}/{WG_INTERFACE}.conf"
SUBNET_PREFIX = "10.0.0"
SERVER_PORT = 51820

# === Init ===
os.makedirs(CLIENT_DIR, exist_ok=True)

# === Utility Functions ===
def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode().strip()

def get_public_ip():
    return run("curl -s https://checkip.amazonaws.com")

def detect_outbound_interface():
    try:
        return run("ip route get 1.1.1.1 | awk '{print $5}'")
    except:
        return "eth0"

def get_server_keys():
    try:
        priv_path = Path(WG_DIR) / "server_private.key"
        pub_path = Path(WG_DIR) / "server_public.key"
        server_priv = priv_path.read_text().strip()
        server_pub = pub_path.read_text().strip()
        return server_priv, server_pub
    except Exception as e:
        raise Exception(f"❌ Error reading server keys: {e}")

def get_used_ips():
    if not Path(WG_CONFIG).exists():
        return []
    with open(WG_CONFIG) as f:
        return re.findall(f"{SUBNET_PREFIX}\\.\\d+", f.read())

def get_next_ip(used_ips):
    next_ip = 2
    while f"{SUBNET_PREFIX}.{next_ip}" in used_ips:
        next_ip += 1
    return f"{SUBNET_PREFIX}.{next_ip}"

def generate_keys():
    private_key = run("wg genkey")
    public_key = run(f"echo {private_key} | wg pubkey")
    return private_key, public_key

def ensure_server_config():
    if not Path(WG_CONFIG).exists():
        print("⚙️ Creating wg0.conf...")
        server_priv, _ = get_server_keys()
        interface = detect_outbound_interface()

        config = f"""[Interface]
Address = 10.0.0.1/24
SaveConfig = false
PostUp = iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE; iptables -A FORWARD -i wg0 -o wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o {interface} -j MASQUERADE; iptables -D FORWARD -i wg0 -o wg0 -j ACCEPT
ListenPort = {SERVER_PORT}
PrivateKey = {server_priv}
"""
        Path(WG_CONFIG).write_text(config)
        print("✅ Server config created.")

def is_interface_up():
    try:
        output = run(f"sudo wg show {WG_INTERFACE}")
        return "interface: " in output
    except:
        return False

def keep_interface_up():
    if not is_interface_up():
        print(f"🚀 Bringing up {WG_INTERFACE}...")
        subprocess.run(["sudo", "wg-quick", "up", WG_INTERFACE])
    else:
        print(f"🔄 Interface {WG_INTERFACE} already up.")

    print("⏳ VPN is active. Press Ctrl+C to terminate and bring down the interface...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Caught termination signal.")

# === Cleanup on Exit ===
def cleanup():
    print("\n🧼 Cleaning up: Bringing interface down...")
    subprocess.run(["sudo", "wg-quick", "down", WG_INTERFACE])
    print("✅ Interface brought down. Exiting.")

atexit.register(cleanup)

# === Client Management ===
def generate_client(client_name):
    ensure_server_config()
    print(f"🔧 Creating client: {client_name}")

    priv_key, pub_key = generate_keys()
    server_priv, server_pub = get_server_keys()
    server_ip = get_public_ip()

    used_ips = get_used_ips()
    client_ip = get_next_ip(used_ips)

    # Append to server config
    peer_block = f"""
[Peer]
# {client_name}
PublicKey = {pub_key}
AllowedIPs = {client_ip}/32
"""
    with open(WG_CONFIG, "a") as f:
        f.write(peer_block)

    # Apply without restarting
    print("🔄 Reloading WireGuard config dynamically...")
    subprocess.run(["sudo", "wg", "addconf", WG_INTERFACE, WG_CONFIG])

    # Client config
    client_config = f"""
[Interface]
PrivateKey = {priv_key}
Address = {client_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub}
Endpoint = {server_ip}:{SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    client_path = Path(CLIENT_DIR) / f"{client_name}.conf"
    client_path.write_text(client_config.strip())

    print("📱 WireGuard Mobile QR Code:")
    subprocess.run(f"qrencode -t ansiutf8 < {client_path}", shell=True)

    print(f"✅ Client {client_name} added with IP {client_ip}")

def remove_client(client_name):
    print(f"🧹 Removing {client_name} from server config...")
    with open(WG_CONFIG, "r") as f:
        lines = f.readlines()

    with open(WG_CONFIG, "w") as f:
        skip = 0
        for line in lines:
            if line.strip() == f"# {client_name}":
                skip = 3
                continue
            if skip > 0:
                skip -= 1
                continue
            f.write(line)

    print("🔄 Reloading WireGuard config dynamically...")
    subprocess.run(["sudo", "wg", "addconf", WG_INTERFACE, WG_CONFIG])

    client_path = Path(CLIENT_DIR) / f"{client_name}.conf"
    if client_path.exists():
        client_path.unlink()
        print(f"🗑 Deleted client config: {client_path}")

    print(f"✅ Client {client_name} removed.")

# === Entry Point ===
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  sudo python3 wg.py add <client-name>")
        print("  sudo python3 wg.py remove <client-name>")
        sys.exit(1)

    action = sys.argv[1]
    client_name = sys.argv[2]

    if action == "add":
        generate_client(client_name)
        keep_interface_up()
    elif action == "remove":
        remove_client(client_name)
    else:
        print("❌ Invalid action. Use 'add' or 'remove'.")
