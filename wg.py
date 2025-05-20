import os
import subprocess
import signal
import sys
import tempfile
import argparse
from pathlib import Path
from shutil import which

WG_INTERFACE = "wg0"
WG_DIR = "/etc/wireguard"
CLIENT_DIR = f"{WG_DIR}/clients"
WG_CONFIG = f"{WG_DIR}/{WG_INTERFACE}.conf"
SERVER_WG_IP = "10.0.0.1"
SUBNET_PREFIX = "10.0.0"
SERVER_PORT = 51820
DNS_SERVER = "1.1.1.1"

def check_requirements():
    if not which("wg") or not which("wg-quick"):
        print("❌ WireGuard tools (wg, wg-quick) are not installed. Please install them.")
        sys.exit(1)

def check_systemd_service():
    try:
        result = subprocess.run(["systemctl", "is-active", f"wg-quick@{WG_INTERFACE}"], capture_output=True, text=True)
        if result.stdout.strip() == "active":
            print(f"⚠️ Warning: systemd service wg-quick@{WG_INTERFACE} is active. This may conflict with the script.")
            print("Consider disabling the service with: sudo systemctl disable wg-quick@wg0")
        result = subprocess.run(["systemctl", "is-enabled", f"wg-quick@{WG_INTERFACE}"], capture_output=True, text=True)
        if result.stdout.strip() == "enabled":
            print(f"ℹ️ Note: systemd service wg-quick@{WG_INTERFACE} is enabled and may start on boot.")
    except Exception as e:
        print(f"❌ Error checking systemd service status: {str(e)}")

def validate_config():
    try:
        # Check for empty [Peer] sections and normalize lines
        with open(WG_CONFIG, "r") as f:
            lines = f.readlines()
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("[Peer]"):
                # Check if the next non-empty line is [Peer], [Interface], or end of file
                j = i + 1
                has_content = False
                while j < len(lines) and not (lines[j].strip().startswith("[Peer]") or lines[j].strip().startswith("[Interface]")):
                    if lines[j].strip() and not lines[j].strip().startswith("#"):
                        has_content = True
                        break
                    j += 1
                if not has_content:
                    print(f"ℹ️ Removing empty [Peer] section at line {i + 1}")
                    i = j
                    continue
            new_lines.append(line.rstrip() + "\n")  # Normalize line endings
            i += 1

        # Write cleaned configuration to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.writelines(new_lines)
            temp_file_path = temp_file.name

        # Validate the configuration
        result = subprocess.run(
            ["wg-quick", "up", temp_file_path],
            capture_output=True,
            text=True
        )
        subprocess.run(["wg-quick", "down", temp_file_path], capture_output=True)
        os.unlink(temp_file_path)

        # Update wg0.conf if changes were made
        if len(new_lines) != len(lines) or any(new_lines[i] != lines[i] for i in range(len(new_lines))):
            with open(WG_CONFIG, "w") as f:
                f.writelines(new_lines)
            print(f"ℹ️ Updated {WG_CONFIG} to remove empty [Peer] sections and normalize formatting.")

        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to validate {WG_CONFIG}: {e.stderr.strip() if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error validating {WG_CONFIG}: {str(e)}")
        return False

def get_default_interface():
    result = subprocess.run(["ip", "route", "get", "8.8.8.8"], capture_output=True, text=True)
    return result.stdout.split("dev")[1].split()[0] if "dev" in result.stdout else "eth0"

def initialize_server_config():
    if not os.path.exists(WG_CONFIG):
        print(f"🔧 Creating base config at {WG_CONFIG}...")
        server_private_key_path = Path(f"{WG_DIR}/server_private.key")
        server_public_key_path = Path(f"{WG_DIR}/server_public.key")

        if not server_private_key_path.exists() or not server_public_key_path.exists():
            server_private_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
            server_public_key = subprocess.check_output(["wg", "pubkey"], input=server_private_key.encode()).decode().strip()

            with open(server_private_key_path, "w") as f:
                f.write(server_private_key)
            with open(server_public_key_path, "w") as f:
                f.write(server_public_key)
        else:
            with open(server_private_key_path) as f:
                server_private_key = f.read().strip()

        interface = get_default_interface()

        config_content = f"""[Interface]
Address = {SERVER_WG_IP}/24
SaveConfig = false
PostUp = iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE; iptables -A FORWARD -i {WG_INTERFACE} -o {interface} -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o {interface} -j MASQUERADE; iptables -D FORWARD -i {WG_INTERFACE} -o {interface} -j ACCEPT
ListenPort = {SERVER_PORT}
PrivateKey = {server_private_key}
"""
        with open(WG_CONFIG, "w") as f:
            f.write(config_content)
        print("✅ Server base configuration created.")

def start_wireguard():
    try:
        # Check if wg0 interface is already up
        result = subprocess.run(["wg", "show", WG_INTERFACE], capture_output=True, text=True)
        if result.returncode == 0 and WG_INTERFACE in result.stdout:
            print(f"ℹ️ WireGuard interface {WG_INTERFACE} is already up.")
            return
        # Validate configuration before starting
        if not os.path.exists(WG_CONFIG):
            print(f"❌ Configuration file {WG_CONFIG} does not exist.")
            sys.exit(1)
        if not validate_config():
            print(f"❌ Invalid configuration in {WG_CONFIG}. Please check the file.")
            sys.exit(1)
        # Start the interface
        subprocess.run(["sudo", "wg-quick", "up", WG_INTERFACE], check=True)
        print(f"🚀 WireGuard interface {WG_INTERFACE} is now up.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start WireGuard: {e.stderr.strip() if e.stderr else str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking WireGuard interface: {str(e)}")
        sys.exit(1)

def turn_off_wireguard():
    try:
        # Check if wg0 interface is up
        result = subprocess.run(["wg", "show", WG_INTERFACE], capture_output=True, text=True)
        if result.returncode == 0 and WG_INTERFACE in result.stdout:
            subprocess.run(["sudo", "wg-quick", "down", WG_INTERFACE], check=True)
            print(f"🛑 WireGuard interface {WG_INTERFACE} has been brought down.")
        else:
            print(f"ℹ️ WireGuard interface {WG_INTERFACE} is already down.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to bring down WireGuard: {e.stderr.strip() if e.stderr else str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking WireGuard interface: {str(e)}")
        sys.exit(1)

def get_used_ips():
    used = set()
    if os.path.exists(WG_CONFIG):
        with open(WG_CONFIG) as f:
            for line in f:
                if SUBNET_PREFIX in line:
                    ip = line.strip().split(".")[-1].split("/")[0]
                    used.add(int(ip))
    return used

def get_next_ip():
    used = get_used_ips()
    for i in range(2, 255):
        if i not in used:
            return f"{SUBNET_PREFIX}.{i}"
    raise Exception("No IPs left in subnet")

def generate_keypair():
    private = subprocess.check_output(["wg", "genkey"]).decode().strip()
    public = subprocess.check_output(["wg", "pubkey"], input=private.encode()).decode().strip()
    return private, public

def get_server_public_key():
    try:
        with open(f"{WG_DIR}/server_private.key") as f:
            private = f.read().strip()
        return subprocess.check_output(["wg", "pubkey"], input=private.encode()).decode().strip()
    except Exception as e:
        print(f"❌ Error reading server private key: {str(e)}")
        sys.exit(1)

def get_public_ip():
    try:
        return subprocess.check_output(["curl", "-s", "https://checkip.amazonaws.com"], timeout=5).decode().strip()
    except:
        try:
            return subprocess.check_output(["curl", "-s", "https://api.ipify.org"], timeout=5).decode().strip()
        except:
            return "YOUR_PUBLIC_IP"

def generate_client(name):
    print(f"🔧 Creating client: {name}")
    try:
        client_private, client_public = generate_keypair()
        client_ip = get_next_ip()
        server_pub = get_server_public_key()

        peer_entry = f"""
[Peer]
# {name}
PublicKey = {client_public}
AllowedIPs = {client_ip}/32
"""

        # Append the new peer to wg0.conf
        with open(WG_CONFIG, "a") as f:
            f.write(peer_entry)

        # Create client configuration
        client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {client_ip}/32
DNS = {DNS_SERVER}

[Peer]
PublicKey = {server_pub}
Endpoint = {get_public_ip()}:{SERVER_PORT}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

        os.makedirs(CLIENT_DIR, exist_ok=True)
        config_path = Path(CLIENT_DIR) / f"{name}.conf"
        with open(config_path, "w") as f:
            f.write(client_config)

        # Restart the WireGuard service
        print(f"ℹ️ Restarting WireGuard service to apply new client {name}...")
        turn_off_wireguard()
        start_wireguard()
        print(f"✅ Client {name} added and service restarted.")

        if which("qrencode"):
            subprocess.run(["qrencode", "-t", "ansiutf8"], input=client_config.encode())
        else:
            print("ℹ️ 'qrencode' not found, skipping QR code display.")

    except Exception as e:
        print(f"❌ Error creating client {name}: {str(e)}")
        # Attempt to revert changes if configuration is invalid
        turn_off_wireguard()
        sys.exit(1)

def remove_client(name):
    print(f"🧹 Removing client {name}...")
    try:
        with open(WG_CONFIG, "r") as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        found = False
        i = 0
        while i < len(lines):
            line = lines[i]
            # Check for the Peer block with the client name
            if line.strip().startswith("[Peer]") and i + 1 < len(lines) and lines[i + 1].strip().startswith(f"# {name}"):
                skip = True
                found = True
                print(f"ℹ️ Found client {name} at line {i + 1}, starting to skip [Peer] block...")
                i += 1  # Skip the [Peer] line
                # Skip all lines until the next [Peer], [Interface], or end of file
                while i < len(lines) and not (lines[i].strip().startswith("[Peer]") or lines[i].strip().startswith("[Interface]")):
                    print(f"ℹ️ Skipping line: {lines[i].strip()}")
                    i += 1
                continue
            if not skip:
                new_lines.append(line.rstrip() + "\n")  # Normalize line endings
            i += 1

        if not found:
            print(f"❌ Client {name} not found in {WG_CONFIG}.")
            return

        # Write the updated configuration to a temporary file for validation
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.writelines(new_lines)
            temp_file_path = temp_file.name

        # Validate the updated configuration
        try:
            result = subprocess.run(
                ["wg-quick", "up", temp_file_path],
                capture_output=True,
                text=True
            )
            subprocess.run(["wg-quick", "down", temp_file_path], capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Updated configuration is invalid: {e.stderr.strip() if e.stderr else str(e)}")
            os.unlink(temp_file_path)
            raise Exception("Failed to validate configuration after removal")

        # Write the updated configuration to wg0.conf
        with open(WG_CONFIG, "w") as f:
            f.writelines(new_lines)
        print(f"ℹ️ Updated {WG_CONFIG} written successfully.")
        print(f"ℹ️ Updated {WG_CONFIG} contents:")
        with open(WG_CONFIG, "r") as f:
            print(f.read())

        # Remove client configuration file
        config_path = Path(CLIENT_DIR) / f"{name}.conf"
        if config_path.exists():
            config_path.unlink()
            print(f"ℹ️ Removed client config: {config_path}")

        # Restart the WireGuard service
        print(f"ℹ️ Restarting WireGuard service to apply client removal for {name}...")
        turn_off_wireguard()
        start_wireguard()
        print(f"✅ Client {name} removed and service restarted.")

        os.unlink(temp_file_path)
    except Exception as e:
        print(f"❌ Error removing client {name}: {str(e)}")
        # Attempt to revert changes if configuration is invalid
        turn_off_wireguard()
        sys.exit(1)

def list_clients():
    print("📜 Current clients in config:")
    try:
        with open(WG_CONFIG) as f:
            for line in f:
                if line.strip().startswith("#"):
                    print(" -", line.strip().lstrip("#").strip())
    except Exception as e:
        print(f"❌ Error listing clients: {str(e)}")

def handle_shutdown(signum, frame):
    print(f"\n🛑 Received signal {signum}. Bringing down {WG_INTERFACE}...")
    turn_off_wireguard()
    sys.exit(0)

def main():
    if os.geteuid() != 0:
        print("❌ This script must be run as root (use sudo).")
        sys.exit(1)
    check_requirements()
    check_systemd_service()
    initialize_server_config()
    start_wireguard()

    while True:
        print("\nWhat would you like to do?")
        print("1. Add a new client")
        print("2. Remove an existing client")
        print("3. List clients")
        print("4. Exit")

        choice = input("Enter choice [1-4]: ").strip()

        if choice == "1":
            name = input("Enter client name: ").strip()
            if name:
                generate_client(name)
            else:
                print("❌ Client name cannot be empty.")
        elif choice == "2":
            name = input("Enter client name to remove: ").strip()
            if name:
                remove_client(name)
            else:
                print("❌ Client name cannot be empty.")
        elif choice == "3":
            list_clients()
        elif choice == "4":
            print("👋 Exiting. Bringing down WireGuard interface...")
            turn_off_wireguard()
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="WireGuard Management Script")
    parser.add_argument(
        "--turn-off", "-t",
        action="store_true",
        help="Turn off the WireGuard interface and exit"
    )
    args = parser.parse_args()

    # Handle turn-off argument
    if args.turn_off:
        turn_off_wireguard()
        sys.exit(0)

    # Register signal handlers and run main loop
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    main()
