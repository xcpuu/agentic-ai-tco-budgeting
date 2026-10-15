#!/usr/bin/env python3
"""Memory-light extraction of per-call token usage from large encrypted HAL traces.

Decrypts a HAL *.json.encrypted file as a stream (same procedure as HAL's published
hal-decrypt.sh: PBKDF2-HMAC-SHA256 key from the file's salt, Fernet token), verifies the
token's HMAC at the end, and parses the plaintext JSON incrementally with ijson, so the
decrypted file is never held in memory or written to disk.

Output (in out_dir): <stem>.calls.jsonl  one line per usage-bearing call:
    id, parent_id, task, op, model, prompt_tokens, completion_tokens, cache_read, cache_write
                      <stem>.meta.json   config, results (without per-task latency detail), total_usage, total_cost

Usage: hal_stream_extract.py in.json.encrypted out_dir
"""
import base64, hmac, hashlib, json, os, sys
import ijson
from ijson.common import ObjectBuilder
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

CHUNK = 4 * 1024 * 1024  # bytes of base64 text per read; multiple of 4


class DecryptedStream:
    def __init__(self, path, password=b"hal1234"):
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 400))
            tail = f.read()
        i = tail.rindex(b'",')
        rest = tail[i:]
        salt_b64 = rest.split(b'"salt"')[1].split(b'"')[1]
        self.salt = base64.b64decode(salt_b64)
        self.data_end = size - 400 + i if size > 400 else i
        self.f = open(path, "rb")
        head = self.f.read(200)
        k = head.index(b'"encrypted_data"')
        k = head.index(b'"', k + len(b'"encrypted_data"') + 1) + 1  # opening quote of value
        self.f.seek(k)
        self.remaining = self.data_end - k
        key32 = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=self.salt, iterations=480000).derive(password)
        self.sign_key, self.enc_key = key32[:16], key32[16:]
        self.mac = hmac.new(self.sign_key, digestmod=hashlib.sha256)
        self.dec = None
        self.unpad = padding.PKCS7(128).unpadder()
        self.outer_buf = b""      # outer base64 residue
        self.inner_buf = b""      # inner base64url residue
        self.raw_buf = b""        # raw token bytes withheld (last 32 = HMAC)
        self.header_done = False
        self.plain = b""
        self.eof = False
        self.mac_ok = None

    def _feed_raw(self, raw, final=False):
        self.raw_buf += raw
        if not self.header_done:
            if len(self.raw_buf) < 25:
                return b""
            hdr, self.raw_buf = self.raw_buf[:25], self.raw_buf[25:]
            self.mac.update(hdr)
            self.dec = Cipher(algorithms.AES(self.enc_key), modes.CBC(hdr[9:25])).decryptor()
            self.header_done = True
        out = b""
        if len(self.raw_buf) > 32:
            n = len(self.raw_buf) - 32
            n -= n % 16
            if n > 0:
                body, self.raw_buf = self.raw_buf[:n], self.raw_buf[n:]
                self.mac.update(body)
                out = self.unpad.update(self.dec.update(body))
        return out

    def _pull(self):
        if self.eof:
            return b""
        if self.remaining <= 0:
            return self._finish()
        n = min(CHUNK, self.remaining)
        data = self.f.read(n)
        self.remaining -= len(data)
        buf = self.outer_buf + data
        cut = len(buf) - (len(buf) % 4)
        self.outer_buf = buf[cut:]
        inner = base64.b64decode(buf[:cut])
        ib = self.inner_buf + inner
        cut2 = len(ib) - (len(ib) % 4)
        self.inner_buf = ib[cut2:]
        raw = base64.urlsafe_b64decode(ib[:cut2])
        return self._feed_raw(raw)

    def _finish(self):
        self.eof = True
        if self.outer_buf:
            self.inner_buf += base64.b64decode(self.outer_buf)
        raw = base64.urlsafe_b64decode(self.inner_buf) if self.inner_buf else b""
        out = self._feed_raw(raw)
        # remaining raw_buf = trailing ciphertext (multiple of 16) + 32-byte HMAC
        tag = self.raw_buf[-32:]
        body = self.raw_buf[:-32]
        self.mac.update(body)
        out += self.unpad.update(self.dec.update(body) + self.dec.finalize())
        out += self.unpad.finalize()
        self.mac_ok = hmac.compare_digest(self.mac.digest(), tag)
        return out

    def read(self, size=-1):
        if size == 0:
            return b""
        while len(self.plain) < (size if size and size > 0 else 1 << 62) and not self.eof:
            self.plain += self._pull()
            if size is None or size < 0:
                continue
        if size is None or size < 0:
            out, self.plain = self.plain, b""
        else:
            out, self.plain = self.plain[:size], self.plain[size:]
        return out


import re
_BIGINT = re.compile(rb"(?<![.\w])(\d{19,})(?![.eE\w])")


class BigIntSafe:
    """Wraps a byte stream; turns integers of 19+ digits into floats (adds '.0') so the
    C JSON parser cannot overflow. Only the digits of such runs are touched; fields used
    by this analysis (ids, token counts) are unaffected. read(n) never returns more than n bytes."""
    def __init__(self, src):
        self.src, self.carry, self.out, self.eof = src, b"", b"", False

    def _fill(self):
        data = self.src.read(1 << 22)
        if not data:
            self.eof = True
            buf, self.carry = self.carry, b""
            self.out += _BIGINT.sub(lambda m: m.group(1) + b".0", buf)
            return
        buf = self.carry + data
        k = len(buf)
        while k > 0 and k > len(buf) - 40 and (48 <= buf[k - 1] <= 57 or buf[k - 1] in b".eE"):
            k -= 1
        buf, self.carry = buf[:k], buf[k:]
        self.out += _BIGINT.sub(lambda m: m.group(1) + b".0", buf)

    def read(self, size=-1):
        if size == 0:
            return b""
        n = size if size and size > 0 else 1 << 22
        while len(self.out) < n and not self.eof:
            self._fill()
        res, self.out = self.out[:n], self.out[n:]
        return res


def extract(path, out_dir):
    """Single streaming pass; no object building for the (huge) call inputs."""
    stem = os.path.basename(path).replace(".json.encrypted", "")
    os.makedirs(out_dir, exist_ok=True)
    ds = DecryptedStream(path)
    meta = {}
    n_calls = n_usage = 0
    P = "raw_logging_results.item"
    cur = {}
    builder = None
    top = None
    depth = 0
    with open(os.path.join(out_dir, stem + ".calls.jsonl"), "w") as out:
        for prefix, event, value in ijson.parse(BigIntSafe(ds), use_float=True, buf_size=1 << 22):
            if builder is not None:
                builder.event(event, value)
                if event in ("start_map", "start_array"):
                    depth += 1
                elif event in ("end_map", "end_array"):
                    depth -= 1
                    if depth == 0:
                        obj = builder.value; builder = None
                        if top == "results" and isinstance(obj, dict):
                            obj.pop("latencies", None)
                        meta[top] = obj
                continue
            if prefix in ("config", "results", "total_usage") and event == "start_map":
                top = prefix; builder = ObjectBuilder(); builder.event(event, value); depth = 1; continue
            if prefix == "total_cost" and event == "number":
                meta["total_cost"] = value; continue
            if not prefix.startswith(P):
                continue
            if prefix == P:
                if event == "start_map":
                    cur = {}
                elif event == "end_map":
                    n_calls += 1
                    if cur.get("pt") is not None or cur.get("ct") is not None or cur.get("spt") is not None:
                        n_usage += 1
                        out.write(json.dumps(dict(
                            id=cur.get("id"), parent_id=cur.get("parent_id"),
                            task=cur.get("task") or cur.get("task2"), op=cur.get("op"), model=cur.get("model"),
                            prompt_tokens=cur.get("pt") or 0, completion_tokens=cur.get("ct") or 0,
                            has_output_usage=cur.get("pt") is not None or cur.get("ct") is not None,
                            sum_prompt=cur.get("spt") or 0, sum_completion=cur.get("sct") or 0,
                            cache_read=cur.get("cr") or cur.get("cached") or 0, cache_write=cur.get("cw") or 0)) + "\n")
                continue
            if event in ("string", "number", "null", "boolean"):
                sub = prefix[len(P) + 1:]
                if sub == "id": cur["id"] = value
                elif sub == "parent_id": cur["parent_id"] = value
                elif sub == "weave_task_id": cur["task"] = value
                elif sub == "attributes.weave_task_id": cur["task2"] = value
                elif sub == "op_name": cur["op"] = (value or "").split("/")[-1].split(":")[0]
                elif sub == "output.model": cur["model"] = value
                elif sub == "output.usage.prompt_tokens": cur["pt"] = value
                elif sub == "output.usage.completion_tokens": cur["ct"] = value
                elif sub == "output.usage.cache_read_input_tokens": cur["cr"] = value
                elif sub == "output.usage.cached_tokens": cur["cached"] = value
                elif sub == "output.usage.cache_creation_input_tokens": cur["cw"] = value
                elif sub.startswith("summary.usage.") and sub.endswith(".prompt_tokens"): cur["spt"] = value
                elif sub.startswith("summary.usage.") and sub.endswith(".completion_tokens"): cur["sct"] = value
    meta["_stream"] = dict(mac_verified=ds.mac_ok, calls=n_calls, usage_calls=n_usage)
    json.dump(meta, open(os.path.join(out_dir, stem + ".meta.json"), "w"), indent=1, default=str)
    return meta["_stream"]


if __name__ == "__main__":
    print(extract(sys.argv[1], sys.argv[2]))
