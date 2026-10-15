#!/usr/bin/env python3
"""Decrypt HAL trace files that macOS already unzipped (*.json.encrypted),
using the same procedure as HAL's published hal-decrypt.sh. Usage: hal_decrypt_json.py in.json.encrypted out.json"""
import json, base64, sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
src, dst = sys.argv[1], sys.argv[2]
enc = json.load(open(src))
salt = base64.b64decode(enc['salt'])
key = base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480000).derive(b'hal1234'))
pt = Fernet(key).decrypt(base64.b64decode(enc['encrypted_data']))
open(dst, 'wb').write(pt)
print('wrote', dst, len(pt))
