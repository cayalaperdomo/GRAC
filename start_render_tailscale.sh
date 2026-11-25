#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
TS_DIR="$PWD/tailscale-bin"
TS_SOCKET="/tmp/grac-tailscale.sock"
: "${TS_AUTHKEY:?Falta TS_AUTHKEY en Render}"
if [[ ! -x "$TS_DIR/tailscale" || ! -x "$TS_DIR/tailscaled" ]]; then
    echo "ERROR: faltan binarios en $TS_DIR; revisar Build Command" >&2
    exit 1
fi
echo "Iniciando Tailscale desde $TS_DIR"
KEY_FILE="$(mktemp)"
chmod 600 "$KEY_FILE"
printf '%s' "$TS_AUTHKEY" > "$KEY_FILE"
unset TS_AUTHKEY
trap 'rm -f "$KEY_FILE"' EXIT
"$TS_DIR/tailscaled" \
    --tun=userspace-networking \
    --state=mem: \
    --socket="$TS_SOCKET" \
    --outbound-http-proxy-listen=127.0.0.1:1055 &
TS_PID=$!
for i in $(seq 1 30); do
    [[ -S "$TS_SOCKET" ]] && break
    kill -0 "$TS_PID" || exit 1
    sleep 1
done
[[ -S "$TS_SOCKET" ]] || { echo "ERROR: socket de Tailscale no disponible" >&2; exit 1; }
"$TS_DIR/tailscale" --socket="$TS_SOCKET" up \
    --auth-key="file:$KEY_FILE" \
    --hostname=grac-render \
    --shields-up \
    --timeout=60s
rm -f "$KEY_FILE"
trap - EXIT
echo "Tailscale conectado correctamente"
if [[ -n "${TS_MIDDLEWARE_URL:-}" ]]; then
    if HTTP_CODE=$(curl --noproxy '' --proxy http://127.0.0.1:1055 \
        --connect-timeout 10 --max-time 20 -sS -o /dev/null \
        -w '%{http_code}' "${TS_MIDDLEWARE_URL%/}/"); then
        echo "Prueba Middleware por Tailscale: HTTP $HTTP_CODE"
    else
        echo "AVISO: no se pudo contactar al Middleware por Tailscale" >&2
    fi
fi
exec bash "$PWD/start_render_lowmem.sh"
