set -euo pipefail

TS_VERSION="1.104.7"
TS_DIR="tailscale-bin"

mkdir -p "$TS_DIR"

curl -fsSL \
  "https://pkgs.tailscale.com/stable/tailscale_${TS_VERSION}_amd64.tgz" \
  -o "$TS_DIR/tailscale.tgz"

tar -xzf "$TS_DIR/tailscale.tgz" \
  --strip-components=1 \
  -C "$TS_DIR"

rm "$TS_DIR/tailscale.tgz"

chmod +x "$TS_DIR/tailscale"
chmod +x "$TS_DIR/tailscaled"

echo "Tailscale instalado correctamente"
