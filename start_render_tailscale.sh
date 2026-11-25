KEY_FILE="$(mktemp)"
chmod 600 "$KEY_FILE"
printf '%s' "$TS_AUTHKEY" > "$KEY_FILE"

"$TS_DIR/tailscale" \
  --socket="$TS_SOCKET" up \
  --auth-key="file:$KEY_FILE" \
  --hostname=grac-render \
  --shields-up \
  --timeout=60s || {
    rm -f "$KEY_FILE"
    exit 1
  }

rm -f "$KEY_FILE"
unset TS_AUTHKEY

echo "Tailscale conectado correctamente"

exec bash start_render_lowmem.sh
