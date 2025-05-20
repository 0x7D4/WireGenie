# WireGuard Management Script

This Python script (`wg.py`) simplifies the management of a WireGuard VPN server on a Linux system. It provides a command-line interface to add, remove, and list WireGuard clients, as well as manage the WireGuard interface (`wg0`). The script is designed for Ubuntu-based systems and automates tasks such as generating client configurations, updating the server configuration, and restarting the WireGuard service.

## Features
- **Add a new client**: Generates a client configuration with a unique IP, private/public key pair, and optional QR code for easy setup.
- **Remove an existing client**: Removes a client’s `[Peer]` block from the server configuration and deletes their config file.
- **List clients**: Displays all clients configured in `/etc/wireguard/wg0.conf`.
- **Service management**: Restarts the WireGuard service (`wg-quick down wg0` and `wg-quick up wg0`) when adding or removing clients to apply changes.
- **Turn off the interface**: Supports a `--turn-off` argument to bring down the `wg0` interface.
- **Automatic shutdown**: Brings down the `wg0` interface on exit (option 4) or when interrupted (e.g., Ctrl+C).
- **Configuration validation**: Ensures the server configuration is valid before applying changes, preventing errors like invalid `[Peer]` blocks or formatting issues.

## Requirements

### System Dependencies
- **wireguard-tools**: Provides `wg` and `wg-quick` for managing WireGuard.
- **iptables**: Used for NAT and forwarding rules in the server configuration.
- **curl**: Fetches the server’s public IP for client configurations.
- **iproute2**: Provides the `ip` command for detecting the default network interface.
- **qrencode** (optional): Displays client configurations as QR codes for easy scanning.

### Python Requirements
- **Python 3.6 or higher**: The script uses standard library modules only (no external packages required).
- Modules used: `os`, `subprocess`, `signal`, `sys`, `tempfile`, `argparse`, `pathlib`, `shutil`.

## Installation

1. **Clone or Copy the Script**
     ```bash
     git clone https://github.com/0x7D4/WireGenie.git
     ```

2. **Install System Dependencies**
   - On Ubuntu, install the required tools:
     ```bash
     sudo apt update
     sudo apt install wireguard iptables curl iproute2 qrencode
     ```
   - Note: `qrencode` is optional; skip it if QR code support is not needed.

3. **Verify Python Version**
   - Ensure Python 3.6 or higher is installed:
     ```bash
     python3 --version
     ```
   - Ubuntu typically includes a compatible version. If not, install it:
     ```bash
     sudo apt install python3
     ```

4. **Disable Systemd Service (Recommended)**
   - The script manages the `wg0` interface directly. To avoid conflicts with the `wg-quick@wg0` systemd service, disable it:
     ```bash
     sudo systemctl disable wg-quick@wg0
     sudo systemctl stop wg-quick@wg0
     ```

## Usage

1. **Run the Script**
   - Execute the script with `sudo` (required for file access and WireGuard commands):
     ```bash
     sudo python3 /home/ubuntu/WireGenie/wg.py
     ```
   - The script initializes the server configuration (`/etc/wireguard/wg0.conf`) if it doesn’t exist and starts the `wg0` interface.

2. **Main Menu**
   - The script presents a menu with four options:
     ```
     What would you like to do?
     1. Add a new client
     2. Remove an existing client
     3. List clients
     4. Exit
     Enter choice [1-4]:
     ```

   - **Option 1: Add a new client**
     - Prompts for a client name, generates a key pair, assigns an IP (e.g., `10.0.0.2/32`), and creates a client config file in `/etc/wireguard/clients/<name>.conf`.
     - Restarts the `wg0` interface to apply the new client.
     - Displays a QR code if `qrencode` is installed.

   - **Option 2: Remove an existing client**
     - Prompts for a client name, removes the corresponding `[Peer]` block from `/etc/wireguard/wg0.conf`, and deletes the client’s config file.
     - Restarts the `wg0` interface to apply the change.
     - Validates the updated configuration to prevent errors.

   - **Option 3: List clients**
     - Lists all clients defined in `/etc/wireguard/wg0.conf` (based on `# <name>` comments).

   - **Option 4: Exit**
     - Brings down the `wg0` interface and exits the script.

3. **Command-Line Argument**
   - Use the `--turn-off` argument to bring down the `wg0` interface and exit:
     ```bash
     sudo python3 /home/ubuntu/WireGenie/wg.py --turn-off
     ```

## Configuration

- **Server Configuration**: Stored in `/etc/wireguard/wg0.conf`.
  - Contains the `[Interface]` section with the server’s private key, IP (`10.0.0.1/24`), and port (`51820`).
  - Includes `[Peer]` sections for each client, with their public key, allowed IPs, and a comment (`# <name>`).
- **Client Configurations**: Stored in `/etc/wireguard/clients/<name>.conf`.
- **Keys**: Server private and public keys are stored in `/etc/wireguard/server_private.key` and `/etc/wireguard/server_public.key`.

**Note**: Always back up `/etc/wireguard/wg0.conf` before making changes:
```bash
sudo cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.bak
```

## Example Usage
```bash
$ sudo python3 /home/ubuntu/WireGenie/wg.py
What would you like to do?
1. Add a new client
2. Remove an existing client
3. List clients
4. Exit
Enter choice [1-4]: 1
Enter client name: testclient
🔧 Creating client: testclient
ℹ️ Restarting WireGuard service to apply new client testclient...
🛑 WireGuard interface wg0 has been brought down.
🚀 WireGuard interface wg0 is now up.
✅ Client testclient added and service restarted.
[QR code displayed if qrencode is installed]
```
