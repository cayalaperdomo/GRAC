#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
TS_DIR="$PWD/tailscale-bin"
TS_VERSION="1.104.7"
mkdir -p "$TS_DIR"
ARCHIVE="$(mktemp)"
trap 'rm -f "$ARCHIVE"' EXIT
curl -fSL --retry 3 "https://pkgs.tailscale.com/stable/tailscale_${TS_VERSION}_amd64.tgz" -o "$ARCHIVE"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$TS_DIR"
chmod +x "$TS_DIR/tailscale" "$TS_DIR/tailscaled"
test -x "$TS_DIR/tailscale"
test -x "$TS_DIR/tailscaled"
"$TS_DIR/tailscale" version
echo "Tailscale instalado correctamente en $TS_DIR"
