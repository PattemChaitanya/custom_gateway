#!/usr/bin/env python3
"""
Stop SSH tunnel by reading `tunnel.pid` and terminating the process.

This is a lightweight cross-platform wrapper so you can run:
  python stop_tunnel.py

It performs the same steps as `stop_tunnel.ps1`:
- read `tunnel.pid` from the script directory
- validate the PID
- kill the process (uses taskkill on Windows)
- remove the pid file
"""
from __future__ import annotations
import os
import sys
import subprocess


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pid_path = os.path.join(script_dir, "tunnel.pid")

    if not os.path.exists(pid_path):
        print(f"No tunnel is running (no {pid_path} found).")
        return 0

    try:
        with open(pid_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except Exception as e:
        print(f"Failed to read {pid_path}: {e}")
        return 1

    if not content.isdigit():
        print(f"PID file does not contain a valid PID: {content}")
        try:
            os.remove(pid_path)
        except Exception:
            pass
        return 1

    pid = int(content)
    print(f"Attempting to stop tunnel (PID: {pid})...")

    try:
        if os.name == "nt":
            # Use taskkill on Windows
            res = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"Tunnel stopped (PID: {pid})")
            else:
                # If process not found, treat as stale
                print(res.stdout.strip())
                print(res.stderr.strip())
                if "not found" in res.stdout.lower() or "not running" in res.stdout.lower():
                    print("No process found. Removing stale PID file.")
        else:
            # POSIX
            import signal
            os.kill(pid, signal.SIGTERM)
            print(f"Tunnel stopped (PID: {pid})")
    except Exception as e:
        print(f"Error stopping process {pid}: {e}")

    try:
        os.remove(pid_path)
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
