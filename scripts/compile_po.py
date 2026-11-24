"""Compile locale/*/LC_MESSAGES/django.po en django.mo sans gettext (parseur minimal)."""
import ast, struct, sys
from pathlib import Path

def parse(path):
    msgs, mid, mstr, cur = {}, None, None, None
    def flush():
        if mid is not None and mstr:
            msgs[mid] = mstr
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("msgid "):
            flush(); mid, mstr, cur = ast.literal_eval(line[6:]), "", "id"
        elif line.startswith("msgstr "):
            mstr, cur = ast.literal_eval(line[7:]), "str"
        elif line.startswith('"'):
            v = ast.literal_eval(line)
            if cur == "id": mid += v
            elif cur == "str": mstr += v
    flush()
    return msgs

def write_mo(msgs, out):
    keys = sorted(msgs)
    ids = b"".join(k.encode() + b"\0" for k in keys)
    strs = b"".join(msgs[k].encode() + b"\0" for k in keys)
    n = len(keys); ko = 28 + n * 16; vo = ko + len(ids)
    kt, vt, o = [], [], 0
    for k in keys: kt.append((len(k.encode()), ko + o)); o += len(k.encode()) + 1
    o = 0
    for k in keys: vt.append((len(msgs[k].encode()), vo + o)); o += len(msgs[k].encode()) + 1
    data = struct.pack("<Iiiiiii", 0x950412DE, 0, n, 28, 28 + n * 8, 0, 0)
    tab = b"".join(struct.pack("<ii", *x) for x in kt) + b"".join(struct.pack("<ii", *x) for x in vt)
    # recalcul des offsets : tables clés puis valeurs, puis chaînes
    ko = 28 + n * 16; vo = ko + len(ids)
    kt = []; o = 0
    for k in keys: kt.append((len(k.encode()), ko + o)); o += len(k.encode()) + 1
    vt = []; o = 0
    for k in keys: vt.append((len(msgs[k].encode()), vo + o)); o += len(msgs[k].encode()) + 1
    tab = b"".join(struct.pack("<ii", *x) for x in kt) + b"".join(struct.pack("<ii", *x) for x in vt)
    Path(out).write_bytes(data + tab + ids + strs)

if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent / "locale"
    for po in root.glob("*/LC_MESSAGES/django.po"):
        write_mo(parse(po), po.with_suffix(".mo")); print("compiled", po)
