#!/usr/bin/env bash
# Install the camera (spec: docs/superpowers/specs/2026-11-03-access-camera-design.md, R6, R11).
# Run as the house user; root steps go through sudo. Installs; starts nothing unless --start.
#
#   deploy/camera/install.sh [--start]
#
# 1. The gate and camera.py are copied root-owned to /usr/local/lib/hamutay-camera (R11); sha256 logged.
# 2. net.unix.max_dgram_qlen raised to 1024 (host-wide; previous value logged).
# 3. The system user hamutay-camera, and both system units (gate as root, scribe as hamutay-camera).
# 4. Database ayllu_camera on arango-apacheta (8529), with users camera_scribe (rw) and camera_reader (ro).
#    Admin credentials are read from ~/.yanantin/config/db.ini inside Python and never printed.
#    The scribe's password is regenerated on every install and written only to
#    /etc/hamutay-camera/scribe.ini (owner hamutay-camera, mode 600). The house user keeps only the
#    read-only user's credentials, in ~/.config/hamutay/camera.ini [reader] (mode 600). (R12)
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
lib=/usr/local/lib/hamutay-camera
state="$HOME/.local/state/hamutay-camera"
log="$state/install.log"
mkdir -p "$state"
stamp() { echo "$(date -u +%FT%TZ) $*" | tee -a "$log"; }

sudo install -d -o root -g root -m 755 "$lib"
sudo install -o root -g root -m 755 "$root/deploy/camera/gate.py" "$lib/gate.py"
sudo install -o root -g root -m 644 "$root/src/hamutay/camera.py" "$lib/camera.py"
sudo install -o root -g root -m 644 "$root/src/hamutay/camera_scribe.py" "$lib/scribe.py"
stamp "installed gate.py $(sha256sum "$lib/gate.py" | cut -c1-64) scribe.py $(sha256sum "$lib/scribe.py" | cut -c1-64) camera.py $(sha256sum "$lib/camera.py" | cut -c1-64) from $(git -C "$root" rev-parse --short HEAD)"

prev="$(sysctl -n net.unix.max_dgram_qlen)"
echo "net.unix.max_dgram_qlen = 1024" | sudo tee /etc/sysctl.d/90-hamutay-camera.conf >/dev/null
sudo sysctl -q -w net.unix.max_dgram_qlen=1024
stamp "net.unix.max_dgram_qlen $prev -> 1024"

getent passwd hamutay-camera >/dev/null || sudo useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin hamutay-camera
if [ -f "$HOME/.config/systemd/user/hamutay-camera-scribe.service" ]; then  # r6 ran the scribe as the house user
  systemctl --user disable --now hamutay-camera-scribe.service 2>/dev/null || true
  rm -f "$HOME/.config/systemd/user/hamutay-camera-scribe.service"; systemctl --user daemon-reload
  stamp "removed r6 user unit for the scribe"
fi
sudo install -o root -g root -m 644 "$root/deploy/camera/hamutay-camera-gate.service" /etc/systemd/system/
sudo install -o root -g root -m 644 "$root/deploy/camera/hamutay-camera-scribe.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hamutay-camera-gate.service hamutay-camera-scribe.service 2>/dev/null
stamp "units installed and enabled (not started)"

scribe_tmp="$(mktemp)"; chmod 600 "$scribe_tmp"; trap 'rm -f "$scribe_tmp"' EXIT
python3 -I - "$HOME/.yanantin/config/db.ini" "$HOME/.config/hamutay/camera.ini" "$scribe_tmp" <<'PY'
import base64, configparser, json, os, secrets, sys, urllib.error, urllib.request
admin_ini, camera_ini, scribe_out = sys.argv[1], sys.argv[2], sys.argv[3]
c = configparser.ConfigParser(); c.read(admin_ini); d = c["database"]
auth = "Basic " + base64.b64encode(f"{d['admin_user']}:{d['admin_passwd']}".encode()).decode()
url = "http://127.0.0.1:8529"
def call(method, path, body=None, ok=(200, 201, 202)):
    req = urllib.request.Request(url + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": auth})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if e.code in ok: return e.code
        if e.code == 409: return 409  # already exists
        raise SystemExit(f"database setup: {method} {path} -> HTTP {e.code}")
print("database:", call("POST", "/_api/database", {"name": "ayllu_camera"}))
for coll in ("entries", "status"):
    print("collection", coll + ":", call("POST", "/_db/ayllu_camera/_api/collection", {"name": coll}))
cam = configparser.ConfigParser()
cam.read(camera_ini)
cam.remove_section("scribe")  # r6 kept it here, readable by the house user; never again (R12)
if not cam.has_section("reader"):
    cam["reader"] = {"url": url, "user": "camera_reader", "password": secrets.token_urlsafe(24)}
scribe = configparser.ConfigParser()
scribe["scribe"] = {"url": url, "user": "camera_scribe", "password": secrets.token_urlsafe(24)}
for section, conf, user, grant in (("scribe", scribe, "camera_scribe", "rw"), ("reader", cam, "camera_reader", "ro")):
    status = call("POST", "/_api/user", {"user": user, "passwd": conf[section]["password"]})
    if status == 409:
        call("PATCH", f"/_api/user/{user}", {"passwd": conf[section]["password"]})
    print("user", user, "grant", grant + ":",
          call("PUT", f"/_api/user/{user}/database/ayllu_camera", {"grant": grant}),
          call("PUT", f"/_api/user/{user}/database/ayllu_camera/*", {"grant": grant}))
with open(scribe_out, "w") as f:
    scribe.write(f)
os.makedirs(os.path.dirname(camera_ini), exist_ok=True)
fd = os.open(camera_ini, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    cam.write(f)
os.chmod(camera_ini, 0o600)
print("credentials:", camera_ini, "(mode 600; not printed)")
PY
sudo install -d -o root -g hamutay-camera -m 750 /etc/hamutay-camera
sudo install -o hamutay-camera -g hamutay-camera -m 600 "$scribe_tmp" /etc/hamutay-camera/scribe.ini
stamp "database ayllu_camera ready; scribe credentials rotated into /etc/hamutay-camera/scribe.ini"

if [ "${1:-}" = "--start" ]; then
  sudo systemctl restart hamutay-camera-scribe.service
  sudo systemctl restart hamutay-camera-gate.service
  stamp "started"
fi
