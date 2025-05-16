#!/bin/bash

# === Configuration ===
WG_INTERFACE="wg0"
WG_DIR="/etc/wireguard"
CLIENT_DIR="$WG_DIR/clients"
WG_CONFIG="$WG_DIR/$WG_INTERFACE.conf"
SERVER_WG_IP="10.0.0.1"
SUBNET_PREFIX="10.0.0"
SERVER_PORT=51820
EMAIL_FROM="lucifer682004@gmail.com"
EMAIL_SUBJECT="Your WireGuard VPN Configuration"

# Automatically detect public IP (fallback if not overridden)
DEFAULT_IP=$(curl -s https://checkip.amazonaws.com)
SERVER_PUBLIC_IP="${SERVER_PUBLIC_IP:-$DEFAULT_IP}"

# Ensure client config directory exists
mkdir -p "$CLIENT_DIR"

# === Functions ===

generate_client() {
    CLIENT_NAME="$1"
    CLIENT_EMAIL="$2"
    echo "🔧 Creating client: $CLIENT_NAME"

    # Generate keypair
    CLIENT_PRIV_KEY=$(wg genkey)
    CLIENT_PUB_KEY=$(echo "$CLIENT_PRIV_KEY" | wg pubkey)

    # Extract server private key and derive public key
    SERVER_PRIV_KEY=$(grep -m1 "^PrivateKey" "$WG_CONFIG" | awk '{print $3}')
    SERVER_PUB_KEY=$(echo "$SERVER_PRIV_KEY" | wg pubkey)

    # Find next free IP
    USED_IPS=$(grep -oP "$SUBNET_PREFIX\.\d+" "$WG_CONFIG")
    NEXT_IP=2
    while echo "$USED_IPS" | grep -q "$SUBNET_PREFIX.$NEXT_IP"; do
        ((NEXT_IP++))
    done
    CLIENT_IP="$SUBNET_PREFIX.$NEXT_IP"

    # Append client to server config
    echo "🔐 Adding $CLIENT_NAME to $WG_CONFIG..."
    sudo bash -c "cat >> $WG_CONFIG <<EOF

[Peer]
# $CLIENT_NAME
PublicKey = $CLIENT_PUB_KEY
AllowedIPs = $CLIENT_IP/32
EOF"

    # Generate client config
    CLIENT_CONF="$CLIENT_DIR/$CLIENT_NAME.conf"
    sudo tee "$CLIENT_CONF" > /dev/null <<EOF
[Interface]
PrivateKey = $CLIENT_PRIV_KEY
Address = $CLIENT_IP/32
DNS = 1.1.1.1

[Peer]
PublicKey = $SERVER_PUB_KEY
Endpoint = $SERVER_PUBLIC_IP:$SERVER_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF

    # Restart WireGuard
    echo "🔄 Restarting WireGuard..."
    sudo systemctl restart "wg-quick@$WG_INTERFACE"

    # Show QR
    echo "📱 WireGuard Mobile QR Code:"
    qrencode -t ansiutf8 < "$CLIENT_CONF"

    # Email config if email provided
    if [[ -n "$CLIENT_EMAIL" ]]; then
        echo "📤 Sending to $CLIENT_EMAIL..."
        echo "Here is your VPN configuration." | mutt -s "$EMAIL_SUBJECT" -a "$CLIENT_CONF" -- "$CLIENT_EMAIL"
    fi

    echo "✅ Client $CLIENT_NAME added with IP $CLIENT_IP"
}

remove_client() {
    CLIENT_NAME="$1"
    echo "🧹 Removing $CLIENT_NAME from server config..."
    sudo sed -i "/# $CLIENT_NAME/,+2d" "$WG_CONFIG"

    echo "🔁 Restarting WireGuard..."
    sudo systemctl restart "wg-quick@$WG_INTERFACE"

    echo "🗑 Deleting client config..."
    sudo rm -f "$CLIENT_DIR/$CLIENT_NAME.conf"

    echo "✅ Client $CLIENT_NAME removed."
}

# === Main ===

case "$1" in
  add)
    if [[ -z "$2" ]]; then
      echo "Usage: $0 add <client-name> [email]"
      exit 1
    fi
    generate_client "$2" "$3"
    ;;
  remove)
    if [[ -z "$2" ]]; then
      echo "Usage: $0 remove <client-name>"
      exit 1
    fi
    remove_client "$2"
    ;;
  *)
    echo "Usage:"
    echo "  $0 add <client-name> [email]   # Add client and optionally email config"
    echo "  $0 remove <client-name>        # Remove client"
    ;;
esac
