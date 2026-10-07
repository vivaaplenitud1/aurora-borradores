#!/usr/bin/env bash
# Instalador del artículo diario en BORRADOR (usagastosfinales.com). Nunca publica.
# Uso (como root en el VPS, dentro de la carpeta descomprimida):  bash instalar-vps.sh
set -euo pipefail
DEST=/opt/aurora-borradores
SRC="$(cd "$(dirname "$0")" && pwd)"
echo "== 1/7 Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
if command -v apt-get >/dev/null; then apt-get update -y >/dev/null && apt-get install -y python3 python3-venv python3-pip curl >/dev/null
elif command -v dnf >/dev/null; then dnf install -y python3 python3-pip curl >/dev/null; fi
echo "== 2/7 Copiar programa a $DEST"
id aurora >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin aurora
mkdir -p "$DEST"
if [ "$SRC" != "$DEST" ]; then cp -a "$SRC"/. "$DEST"/; fi
echo "== 3/7 Entorno de Python"
python3 -m venv "$DEST/.venv"
"$DEST/.venv/bin/pip" install -q --upgrade pip
"$DEST/.venv/bin/pip" install -q -r "$DEST/requirements.txt"
echo "== 4/7 Claves (se escriben ocultas; no se muestran)"
if [ -f "$DEST/.env" ]; then
  echo "Ya existe $DEST/.env; se conserva."
else
  read -r -p "Usuario de WordPress [Aurora]: " WPU </dev/tty; WPU=${WPU:-Aurora}
  read -r -s -p "Contraseña de APLICACIÓN de WordPress (con espacios): " WPP </dev/tty; echo
  read -r -s -p "Clave de Gemini (Google AI Studio): " GK </dev/tty; echo
  umask 077
  cat > "$DEST/.env" <<ENV
WP_URL="https://usagastosfinales.com"
WP_USER="$WPU"
WP_APP_PASSWORD="$WPP"
GEMINI_API_KEY="$GK"
GEMINI_MODELS="gemini-3.8-flash,gemini-flash-latest,gemini-3.5-flash-lite"
ENV
fi
chown -R aurora:aurora "$DEST"; chmod 600 "$DEST/.env"
set -a; . "$DEST/.env"; set +a
echo "== 5/7 Prueba sin claves (dry-run)"
cd "$DEST" && sudo -u aurora "$DEST/.venv/bin/python" generar.py --dry-run >/tmp/aurora-dryrun.txt 2>&1 && echo "Dry-run OK" || { echo "Dry-run FALLÓ:"; tail -20 /tmp/aurora-dryrun.txt; exit 1; }
echo "== 6/7 ¿El VPS entra a WordPress?"
CODE=$(curl -s -o /tmp/aurora-wp.json -w "%{http_code}" --max-time 20 -u "$WP_USER:$WP_APP_PASSWORD" "$WP_URL/wp-json/wp/v2/users/me?context=edit" || echo 000)
echo "Respuesta de WordPress: $CODE"
if [ "$CODE" != "200" ]; then
  echo "NO entró (esperado 200). 401 = usuario o contraseña de aplicación incorrectos; 000 = bloqueo de red."
  echo "Corrige la clave con: nano $DEST/.env   y vuelve a correr: bash $DEST/instalar-vps.sh"
  exit 1
fi
echo "== 7/7 Temporizador diario 10:17 AM hora de Nueva York"
cat > /etc/systemd/system/articulo-diario.service <<UNIT
[Unit]
Description=Borrador diario usagastosfinales.com (nunca publica)
After=network-online.target
Wants=network-online.target
[Service]
Type=oneshot
User=aurora
WorkingDirectory=$DEST
EnvironmentFile=$DEST/.env
ExecStart=$DEST/.venv/bin/python generar.py
Nice=10
UNIT
cp "$DEST/systemd/articulo-diario.timer" /etc/systemd/system/articulo-diario.timer
systemctl daemon-reload
systemctl enable --now articulo-diario.timer
systemctl list-timers articulo-diario.timer --no-pager || true
echo
read -r -p "¿Crear AHORA un borrador de prueba en WordPress? (s/n): " R </dev/tty
if [ "${R,,}" = "s" ]; then systemctl start articulo-diario.service; journalctl -u articulo-diario --no-pager -n 30; fi
echo
echo "LISTO. Ver registro: journalctl -u articulo-diario -n 50 --no-pager"
echo "Pausar: systemctl disable --now articulo-diario.timer"
