#!/usr/bin/env python3
"""
Start SSH tunnel by reading `tunnel.json` and launching `ssh`.

Use:
  python start_tunnel.py

This replicates the behavior of `start_tunnel.ps1` but is safe to run with Python.
"""
from __future__ import annotations
import os
import sys
import json
import time
import subprocess


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_process_running(pid: int) -> bool:
    try:
        if os.name == "nt":
            # tasklist returns non-zero on failure; check presence
            res = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
            return str(pid) in res.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(script_dir, "tunnel.json")
    pid_path = os.path.join(script_dir, "tunnel.pid")

    if not os.path.exists(cfg_path):
        print(f"Missing config: {cfg_path}")
        return 1

    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print(f"Failed to load {cfg_path}: {e}")
        return 1

    if os.path.exists(pid_path):
        try:
            with open(pid_path, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            existing_pid = int(existing)
            if is_process_running(existing_pid):
                print(f"Tunnel is already running (PID: {existing_pid})")
                return 0
            else:
                print(f"Stale PID file found (PID: {existing_pid}); removing.")
                try:
                    os.remove(pid_path)
                except Exception:
                    pass
        except Exception:
            # remove invalid pid file
            try:
                os.remove(pid_path)
            except Exception:
                pass

    ec2_user = cfg.get("ec2_user")
    ec2_host = cfg.get("ec2_host")
    ec2_key = cfg.get("ec2_key")
    rds_host = cfg.get("rds_host")
    rds_port = cfg.get("rds_port")
    local_port = cfg.get("local_port")

    print("\n=== Starting SSH Tunnel ===")
    print(f"EC2: {ec2_user}@{ec2_host}")
    print(f"Forwarding: localhost:{local_port} -> {rds_host}:{rds_port}")

    ssh_args = [
        "ssh",
        "-i",
        ec2_key,
        "-L",
        f"{local_port}:{rds_host}:{rds_port}",
        "-N",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "ServerAliveInterval=60",
        f"{ec2_user}@{ec2_host}",
    ]

    try:
        # Start detached process
        if os.name == "nt":
            proc = subprocess.Popen(ssh_args, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            proc = subprocess.Popen(
                ssh_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(
            "ssh executable not found on PATH. Install OpenSSH or ensure ssh is available.")
        return 1
    except Exception as e:
        print(f"Failed to start ssh: {e}")
        return 1

    # write pid
    try:
        with open(pid_path, "w", encoding="utf-8") as f:
            f.write(str(proc.pid))
    except Exception as e:
        print(f"Failed to write PID file: {e}")

    time.sleep(3)

    if is_process_running(proc.pid):
        print("\nTunnel started successfully!")
        print(f"PID: {proc.pid}")
        print(f"\nConnect to: localhost:{local_port}")
        print("\nTest with: python test_tunnel.py")
        return 0
    else:
        print("\nFailed to start tunnel")
        try:
            os.remove(pid_path)
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
