#!/usr/bin/env python3
"""Simple Postgres connectivity tester using psycopg2.

Usage:
  - Set env vars (recommended): AWS_DB_HOST, AWS_DB_PORT, AWS_DB_NAME, AWS_DB_USER, AWS_DB_PASSWORD
  - Or pass a password interactively when prompted.

The script prints DNS resolution info and attempts a short psycopg2 connection.
"""
import os
import socket
import sys
from getpass import getpass

try:
    import psycopg2
    from psycopg2 import OperationalError
except Exception:
    print("psycopg2 is not installed. Install it in your environment and try again.")
    print("pip install psycopg2-binary")
    raise


def main():
    host = os.getenv("AWS_DB_HOST") or input("AWS_DB_HOST: ")
    port = int(os.getenv("AWS_DB_PORT", "5432"))
    db = os.getenv("AWS_DB_NAME") or input("AWS_DB_NAME: ")
    user = os.getenv("AWS_DB_USER") or input("AWS_DB_USER: ")
    password = os.getenv("AWS_DB_PASSWORD")
    if not password:
        password = getpass("AWS_DB_PASSWORD: ")

    sslmode = os.getenv("AWS_REQUIRE_SSL", "False").lower()
    # If user explicitly set sslrootcert path via env var, use it
    sslrootcert = os.getenv("AWS_SSLROOTCERT")

    print(f"Testing DNS resolution for host: {host}")
    try:
        addrs = socket.getaddrinfo(host, port)
        for a in addrs:
            fam, socktype, proto, canonname, sockaddr = a
            print(" ->", sockaddr)
    except Exception as e:
        print(f"DNS resolution failed: {e}")

    conn = None
    try:
        conn_params = dict(host=host, port=port, database=db, user=user, password=password, connect_timeout=5)
        if sslmode in ("1", "true", "yes") or sslmode == "require":
            conn_params["sslmode"] = "verify-full"
            if sslrootcert:
                conn_params["sslrootcert"] = sslrootcert

        print("Attempting psycopg2 connection with parameters:")
        masked = conn_params.copy()
        masked["password"] = "********"
        print(masked)

        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        cur.execute('SELECT version();')
        print("Postgres version:", cur.fetchone()[0])
        cur.close()
    except OperationalError as e:
        print("OperationalError connecting to Postgres:", e)
        print("Common causes: DNS, port blocked by firewall/security group, private RDS endpoint (VPC), or invalid SSL settings.")
        raise
    except Exception as e:
        print("Database error:", e)
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
