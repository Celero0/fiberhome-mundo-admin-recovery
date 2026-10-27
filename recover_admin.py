#!/usr/bin/env python3
"""Recover the admin password of a FiberHome GPON ONT.

Mundo Pacifico (Chile) rolled out TR-069, which rewrites the admin password on
their FiberHome ONTs and locks customers out of their own device. The basic
customer account can still trigger a configuration backup, and that backup
contains the admin password in a recoverable form.

This tool logs in with the customer account, downloads the backup, decrypts it,
and prints the admin credentials. It then logs out.
"""

import argparse
import random
import re
import sys

import requests
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Constants baked into the FiberHome firmware.
_XOR_KEY = 0x2537                    # XOR key for the config backup
_AES_ECB_KEY = b"ABCDEFGHIJKLMNOP"   # AES-128-ECB key for strings in the config
_AES_CBC_KEY = b"opqrstuvwxyz{|}~"   # AES-128-CBC key/IV for the login password


def _aes_cbc_encrypt(plaintext: str) -> str:
    padder = padding.PKCS7(128).padder()
    data = padder.update(plaintext.encode()) + padder.finalize()
    enc = Cipher(algorithms.AES(_AES_CBC_KEY), modes.CBC(_AES_CBC_KEY)).encryptor()
    return (enc.update(data) + enc.finalize()).hex().upper()


def _aes_ecb_decrypt(hexstr: str) -> str:
    data = bytes.fromhex(hexstr)
    dec = Cipher(algorithms.AES(_AES_ECB_KEY), modes.ECB()).decryptor()
    return (dec.update(data) + dec.finalize()).rstrip(b"\x00").decode("utf-8", "replace")


def _xor_decrypt(data: bytes, key: int) -> bytes:
    size = len(data)
    out = bytearray(size)
    q = size // key
    for i, b in enumerate(data):
        out[i] = b ^ ((size + key + i - q) & 0xFF)
    return bytes(out)


def _api_get(session: requests.Session, host: str, method: str):
    return session.get(host + "/cgi-bin/ajax",
                       params={"ajaxmethod": method, "_": random.random()},
                       timeout=30)


def _api_post(session: requests.Session, host: str, method: str, data: dict):
    payload = dict(data)
    payload["ajaxmethod"] = method
    payload["sessionid"] = _api_get(session, host, "get_refresh_sessionid").json()["sessionid"]
    payload["_"] = random.random()
    return session.post(host + "/cgi-bin/ajax", data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=30)


def _login(session: requests.Session, host: str, user: str, password: str) -> None:
    result = _api_post(session, host, "do_login", {
        "username": user,
        "loginpd": _aes_cbc_encrypt(password),
        "port": 0,
    }).json()
    if result.get("login_result") != 0:
        raise RuntimeError(f"login failed: {result}")


def _super_username(session: requests.Session, host: str) -> str:
    try:
        return _api_get(session, host, "get_super_userName").json().get("super_userName") or "admin"
    except Exception:
        return "admin"


def _download_config(session: requests.Session, host: str) -> bytes:
    result = _api_post(session, host, "down_cfgfile", {}).json()
    if result.get("success") != "true":
        raise RuntimeError(f"config backup rejected: {result}")
    response = session.get(host + "/cgi-bin/download?usrconfig_conf", timeout=60)
    response.raise_for_status()
    return response.content


def _logout(session: requests.Session, host: str) -> None:
    try:
        _api_post(session, host, "do_logout", {"username": "common"})
    except Exception:
        pass


def _extract_password(config: bytes) -> str:
    text = _xor_decrypt(config, _XOR_KEY).decode("utf-8", "replace")
    match = re.search(r"option\s+WebSuperPassword\s+'([0-9A-Fa-f]+)'", text)
    if not match:
        raise RuntimeError("WebSuperPassword not found in configuration")
    return _aes_ecb_decrypt(match.group(1))


def recover(host: str, user: str, password: str):
    session = requests.Session()
    _login(session, host, user, password)
    username = _super_username(session, host)
    config = _download_config(session, host)
    secret = _extract_password(config)
    _logout(session, host)
    return username, secret


def decrypt_file(path: str) -> str:
    with open(path, "rb") as f:
        return _extract_password(f.read())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Recover the admin password of a FiberHome GPON ONT "
                    "(tested on HG6145F provisioned by Mundo Pacifico).")
    parser.add_argument("--host", default="http://192.168.1.1",
                        help="router base URL (default: %(default)s)")
    parser.add_argument("--user", default="user",
                        help="customer account username (default: %(default)s)")
    parser.add_argument("--password", default="user1234",
                        help="customer account password (default: %(default)s)")
    parser.add_argument("--config", metavar="FILE",
                        help="decrypt a local config backup instead of downloading one")
    args = parser.parse_args(argv)

    if args.config:
        secret = decrypt_file(args.config)
        print(f"admin password: {secret}")
        return 0

    username, secret = recover(args.host, args.user, args.password)
    print(f"username: {username}")
    print(f"password: {secret}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
