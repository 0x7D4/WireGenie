# WireGuard Client Manager

Shell script to automate WireGuard VPN client config generation, with QR code, email delivery, and server integration.

## Features
- Add/remove clients
- Email `.conf` files
- Generate QR codes
- Auto assign IPs
- Restart server automatically

## Usage
```bash
sudo ./wireguard-client-manager.sh add alice alice@example.com
sudo ./wireguard-client-manager.sh remove alice
