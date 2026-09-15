from __future__ import annotations
import subprocess

class SystemdUnavailable(Exception):
    pass

class Systemd:
    def _run(self, *args) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise SystemdUnavailable(str(e))
        return proc.returncode, proc.stdout, proc.stderr

    def show(self, unit: str) -> dict:
        rc, out, err = self._run("show", "-p", "ActiveState,SubState,LoadState,InvocationID", unit)
        if rc != 0 and "not-found" not in out:
            raise SystemdUnavailable(err.strip() or f"show rc={rc}")
        props = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
        return {"active_state": props.get("ActiveState", "inactive"), "sub_state": props.get("SubState", "dead"),
                "load_state": props.get("LoadState", "not-found"), "invocation_id": props.get("InvocationID", "")}

    def start(self, unit): rc, _, err = self._run("start", unit); return rc, err
    def stop(self, unit): rc, _, err = self._run("stop", unit); return rc, err
    def kill(self, unit, signal="TERM"): rc, _, err = self._run("kill", "--signal", signal, unit); return rc, err
