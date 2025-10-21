#!/usr/bin/env python3
"""Robust extractor for JSON metadata embedded in PX4/firmware binaries.

This script searches the binary for the first balanced JSON object (handles
strings and escaped characters), parses it with json.loads, and prints
some common metadata tags.
"""
import json
import sys
from typing import Optional
import os
import base64
import re


def find_json_bytes(data: bytes, max_search_len: Optional[int] = None) -> Optional[bytes]:
    """Find a balanced JSON object in `data` and return it as bytes.

    Scans for a starting '{', then walks forward tracking nesting depth while
    respecting string literals and escape characters. Limits the scan length
    from each start position to `max_search_len` to avoid pathological scans.
    Returns None if no valid JSON object is found.
    """
    start = data.find(b'{')
    while start != -1:
        depth = 0
        in_str = False
        escape = False
        i = start
        # limit how far we scan from this start; None means no extra cap
        if max_search_len is None:
            limit = len(data)
        else:
            limit = min(len(data), start + max_search_len)
        while i < limit:
            ch = data[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == 0x5C:  # backslash \
                    escape = True
                elif ch == 0x22:  # double quote "
                    in_str = False
            else:
                if ch == 0x22:  # start string
                    in_str = True
                elif ch == 0x7B:  # {
                    depth += 1
                elif ch == 0x7D:  # }
                    depth -= 1
                    if depth == 0:
                        # return the JSON slice
                        return data[start:i + 1]
            i += 1

        # try next '{' after current start
        start = data.find(b'{', start + 1)

    return None


def quick_extract_tags(px4_file: str):
    """Extract metadata JSON object from a firmware file and print common tags."""
    try:
        with open(px4_file, 'rb') as f:
            data = f.read()
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {px4_file}")
        return None

    # Try robust balanced-brace search first
    json_bytes = find_json_bytes(data)

    # Fallback: previous heuristics (null or double newline) if robust search fails
    if json_bytes is None:
        null_pos = data.find(b'\x00')
        if null_pos != -1:
            candidate = data[:null_pos]
        else:
            dn_pos = data.find(b"\n\n")
            candidate = data[:dn_pos] if dn_pos != -1 else None
        if candidate:
            # try to find JSON inside candidate
            start = candidate.find(b'{')
            if start != -1:
                json_bytes = candidate[start:]

    if not json_bytes:
        print("메타데이터(JSON 객체)를 찾을 수 없습니다.")
        return None

    # Parse JSON
    try:
        metadata = json.loads(json_bytes.decode('utf-8', errors='strict'))
    except UnicodeDecodeError:
        # Try a lossy decode as last resort
        try:
            metadata = json.loads(json_bytes.decode('utf-8', errors='replace'))
        except Exception as e:
            print(f"JSON 디코딩 실패: {e}")
            return None
    except Exception as e:
        print(f"JSON 파싱 실패: {e}")
        return None

    # 주요 태그만 출력
    tags = [
        'board_id',
        'magic',
        'description',
        'image',
        'build_time',
        'image_size',
        'image_maxsize',
        'git_identity',
        'board_revision',
        'git_hash',
        'parameter_xml_size',
        'parameter_xml',
        'mav_autopilot',
        'airframe_xml',
        'airframe_xml_size',
    ]

    print("주요 태그 값:")
    for tag in tags:
        if tag in metadata:
            value = metadata[tag]
            if tag.endswith('_size') and isinstance(value, int):
                print(f"{tag}: {value} bytes")
            else:
                print(f"{tag}: {value}")

    if 'airframe_xml' in metadata:
        print(f"airframe_xml: 존재 (길이: {len(metadata['airframe_xml'])} bytes)")

    return metadata


def save_metadata_files(metadata: dict, output_dir: str = 'extracted'):
    """Save each metadata field into a separate file under `output_dir`.

    - base64-like fields (e.g. 'image') are decoded and written as binary.
    - '*_xml' fields and other long strings are written as UTF-8 text files.
    - other scalar fields are written into a JSON file containing them all.
    """
    os.makedirs(output_dir, exist_ok=True)

    # heuristic for base64: long ascii string with only base64 chars and +/=
    b64_re = re.compile(r'^[A-Za-z0-9+/=\n\r]+$')

    # collect non-file fields to dump as metadata.json
    remaining = {}

    for key, val in metadata.items():
        if val is None:
            continue

        # handle image-like large base64 fields
        if isinstance(val, str) and len(val) > 100 and b64_re.match(val):
            # try to decode
            try:
                decoded = base64.b64decode(val.encode('utf-8'), validate=False)
                # special-case names
                if key == 'image':
                    out_path = os.path.join(output_dir, 'firmware.bin')
                elif key in ('airframe_xml', 'parameter_xml'):
                    # For XML fields: try to detect compression and/or binary data.
                    # Write raw decoded bytes first, then attempt to decompress and
                    # decode to UTF-8 text if possible. This avoids losing data by
                    # doing `decode(errors='replace')` which inserts replacement
                    # characters for non-UTF8 payloads (already seen in prior runs).
                    raw = decoded

                    def try_decompress(b: bytes) -> bytes | None:
                        # gzip
                        try:
                            import gzip

                            if b.startswith(b"\x1f\x8b"):
                                return gzip.decompress(b)
                        except Exception:
                            pass
                        # zlib/deflate (common prefix 0x78)
                        try:
                            import zlib

                            if len(b) >= 2 and b[0] == 0x78:
                                return zlib.decompress(b)
                        except Exception:
                            pass
                        # zip container
                        try:
                            import zipfile
                            import io

                            if b.startswith(b"PK\x03\x04"):
                                z = zipfile.ZipFile(io.BytesIO(b))
                                names = z.namelist()
                                if names:
                                    return z.read(names[0])
                        except Exception:
                            pass
                        return None

                    decompressed = try_decompress(raw)

                    if decompressed is not None:
                        # If we got decompressed bytes, try to decode to UTF-8 text
                        try:
                            text = decompressed.decode('utf-8')
                            out_path = os.path.join(output_dir, f"{key}.xml")
                            with open(out_path, 'w', encoding='utf-8') as f:
                                f.write(text)
                            print(f"[+] Decompressed+decoded XML field '{key}' -> {out_path} ({os.path.getsize(out_path)} bytes)")
                            continue
                        except Exception:
                            # If decompressed bytes are not valid UTF-8, fall through
                            # and write the raw decompressed bytes as a .bin file so
                            # nothing is lost.
                            out_path = os.path.join(output_dir, f"{key}.bin")
                            with open(out_path, 'wb') as f:
                                f.write(decompressed)
                            print(f"[+] Decompressed binary XML payload for '{key}' -> {out_path} ({os.path.getsize(out_path)} bytes)")
                            continue

                    # No decompression available; check if raw bytes are valid UTF-8
                    try:
                        text = raw.decode('utf-8')
                        out_path = os.path.join(output_dir, f"{key}.xml")
                        with open(out_path, 'w', encoding='utf-8') as f:
                            f.write(text)
                        print(f"[+] Decoded base64 XML field '{key}' -> {out_path} ({os.path.getsize(out_path)} bytes)")
                        continue
                    except Exception:
                        # Not UTF-8: preserve raw bytes to avoid corruption.
                        out_path = os.path.join(output_dir, f"{key}.bin")
                        with open(out_path, 'wb') as f:
                            f.write(raw)
                        print(f"[+] Saved raw binary XML payload for '{key}' -> {out_path} ({os.path.getsize(out_path)} bytes)")
                        continue
                else:
                    out_path = os.path.join(output_dir, f"{key}.bin")

                with open(out_path, 'wb') as f:
                    f.write(decoded)
                print(f"[+] Decoded base64 field '{key}' -> {out_path} ({len(decoded)} bytes)")
                continue
            except Exception as e:
                # fallthrough to save as text
                print(f"[!] base64 decode failed for {key}: {e}")

        # write xml or long text
        if isinstance(val, str) and (key.endswith('_xml') or '\n' in val or len(val) > 200):
            ext = 'xml' if key.endswith('_xml') or key in ('airframe_xml', 'parameter_xml') else 'txt'
            out_path = os.path.join(output_dir, f"{key}.{ext}")
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(val)
            print(f"[+] Wrote text field '{key}' -> {out_path} ({len(val)} chars)")
            continue

        # small scalars -> collect
        remaining[key] = val

    # dump remaining small fields
    meta_file = os.path.join(output_dir, 'metadata.json')
    with open(meta_file, 'w', encoding='utf-8') as f:
        json.dump(remaining, f, indent=2, ensure_ascii=False)
    print(f"[+] Saved remaining metadata -> {meta_file}")


def _usage():
    print("사용법: extract_meta.py <firmware-file>")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        _usage()
        sys.exit(1)
    metadata = quick_extract_tags(sys.argv[1])
    if metadata:
        save_metadata_files(metadata, output_dir='extracted')



