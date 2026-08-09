#!/usr/bin/env python3
# =============================================================================
#  diag_hit_install.py -- diagnostic build for the hit-only install failure.
#
#  pl003_hitgrant.* gave no install on hit/whiff/guard, but the on-hit path
#  was designed to be invisible, so we can't tell which link broke:
#    (a) node key "atk_lo02_1" doesn't resolve as a derive target
#    (b) vars[14] hit_combo_stop=1 doesn't fire on AutoCombo nodes
#        (maybe it only evaluates at the instant a hit lands, 17-37/64,
#        outside the 110-300 window -- unlike -1 which holds at action end)
#    (c) the NEW tadj entry (Enhance carrier) isn't loaded by the engine
#
#  This build makes every fired derive VISIBLE (carrier keeps its original
#  cut-move animation, the old atk_lo02 low attack) and splits the tests:
#
#    BASE : node vars[14]=-1 (PROVEN semantics, same as dam_fail), window
#           110-300; base dam_fail node REMOVED from nexts for the test.
#           -> whiff base DP: if the low-attack anim plays, key resolution
#              works (a is fine). If install also appears, tadj entry loads
#              (c is fine).
#    EVO  : node vars[14]=1, window 0-300 (covers the hit frames).
#           -> hit evo DP: if the anim plays, hit-gating works; note WHEN
#              it cuts in (at the hit moment ~17-37/64, or at the end).
#           -> guard evo DP: anim must NOT play.
#    REV  : untouched.
#
#  tadj: same as make_hit_only_install (strip DP Enhance, add carriers).
#  tact: NOT patched -- use pl003_final.tactpkg as pl003.tactpkg so the
#        carrier plays its original, visible motion.
#
#  Inputs pl003_final.tadjpkg/.tcmbpkg -> outputs pl003_diag.tadjpkg/.tcmbpkg
# =============================================================================
import struct, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
RW   = os.path.join(HERE, "Reworked Uryu")

GRANT_WINDOW = (0.0, 10.0)
ENHANCE_PARAMS = [("enhance_start", "1"), ("enhance_mode", "1"),
                  ("max_val", "1800.000000"), ("init_val", "1"),
                  ("enhance_active", "0")]
FIXED17 = bytes.fromhex("000080bfffffffff000000000000803f00")

TIERS = [
    dict(group="1_normal\\attack", act="atk_lo02_1",
         carrier_entry="1_normal_attack_atk_lo02_1",
         after_entry="1_normal_attack_atk_lo02",
         dp1="1_normal_attack_sp_atk02_1", uid_rec=0x51D0AA91,
         uid_node=910, hit_stop=b"-1", win=(110, 300), drop_next=b"900"),
    dict(group="2_evo\\attack", act="evo_atk_lo02_1",
         carrier_entry="2_evo_attack_evo_atk_lo02_1",
         after_entry="2_evo_attack_evo_atk_lo02",
         dp1="2_evo_attack_evo_sp_atk02_1", uid_rec=0x51D0AA92,
         uid_node=911, hit_stop=b"1", win=(0, 300), drop_next=None),
]


def build_record(uid, name, start, end, params):
    rec  = struct.pack("<I", uid)
    rec += name.encode("ascii") + b"\x00"
    rec += struct.pack("<IBffB", 0, 0, float(start), float(end), 0)
    rec += struct.pack("<I", len(params))
    for k, v in params:
        rec += k.encode("shift_jis") + b"\x00" + v.encode("shift_jis") + b"\x00"
    return rec


def find_record_count_pos(blob):
    p = 4
    for _ in range(3):
        p = blob.index(b"\x00", p) + 1
    return p + 17


def find_named_record(blob, rec_name):
    key = rec_name.encode("ascii") + b"\x00"
    j = blob.find(key)
    if j < 0:
        return None
    start = j - 4
    p = j + len(key)
    flag = blob[p + 13]
    p += 14
    if flag != 0:
        p += 4
    pc = struct.unpack_from("<I", blob, p)[0]
    p += 4
    for _ in range(pc):
        p = blob.index(b"\x00", p) + 1
        p = blob.index(b"\x00", p) + 1
    return start, p


def strip_and_insert(blob, rec_name, new_recs):
    blob = bytearray(blob)
    removed = 0
    while True:
        span = find_named_record(bytes(blob), rec_name)
        if span is None:
            break
        blob = blob[:span[0]] + blob[span[1]:]
        removed += 1
    cpos = find_record_count_pos(blob)
    rc = struct.unpack_from("<I", blob, cpos)[0]
    struct.pack_into("<I", blob, cpos, rc - removed + len(new_recs))
    return blob[:cpos + 4] + b"".join(new_recs) + blob[cpos + 4:], removed


def patch_tadj():
    data = open(os.path.join(RW, "pl003_final.tadjpkg"), "rb").read()
    assert data[:10] == b"actadj_pkg"
    count = struct.unpack_from("<I", data, 0x20)[0]
    entries, off = [], 0x24
    for _ in range(count):
        name = data[off:off+64].split(b"\x00")[0].decode("shift_jis")
        start, size = struct.unpack_from("<II", data, off+64)
        entries.append([name, data[start:start+size]])
        off += 72
    names = [e[0] for e in entries]
    for t in TIERS:
        i = names.index(t["dp1"])
        entries[i][1], removed = strip_and_insert(entries[i][1], "Enhance", [])
        print("tadj  %-32s stripped %d Enhance" % (t["dp1"], removed))
        blob  = b"adjb" + t["group"].encode("shift_jis") + b"\x00"
        blob += t["act"].encode("shift_jis") + b"\x00"
        blob += t["act"].encode("shift_jis") + b"\x00" + FIXED17
        blob += struct.pack("<I", 1) + build_record(
            t["uid_rec"], "Enhance", *GRANT_WINDOW, ENHANCE_PARAMS)
        at = names.index(t["after_entry"]) + 1
        entries.insert(at, [t["carrier_entry"], blob])
        names.insert(at, t["carrier_entry"])
        print("tadj  %-32s added (Enhance %g->%g)" % (t["carrier_entry"],
                                                      *GRANT_WINDOW))
    count = len(entries)
    out = bytearray(data[:0x24])
    out += b"\x00" * (count * 72)
    struct.pack_into("<I", out, 0x20, count)
    pos = 0x24 + count * 72
    for i, (name, blob) in enumerate(entries):
        nb, row = name.encode("shift_jis"), 0x24 + i * 72
        out[row:row+64] = nb + b"\x00" * (64 - len(nb))
        struct.pack_into("<II", out, row+64, pos, len(blob))
        pos += len(blob)
    for _n, blob in entries:
        out += blob
    open(os.path.join(RW, "pl003_diag.tadjpkg"), "wb").write(out)
    print("tadj  %d entries, %d -> %d bytes" % (count, len(data), len(out)))


NODE_TMPL = (b'\n            "%(key)s": {'
             b'\n                "_uniqueID": "%(uid)d",'
             b'\n                "input_text": "AutoCombo",'
             b'\n                "additional_input1": "",'
             b'\n                "additional_input2": "",'
             b'\n                "push": "0",'
             b'\n                "push_option": "",'
             b'\n                "access_text": "",'
             b'\n                "jump_tip": "0",'
             b'\n                "jump_table_name": "",'
             b'\n                "jump_access_text": "",'
             b'\n                "input_event": "",'
             b'\n                %(vars)s'
             b'\n            },')


def patch_tcmb():
    data = open(os.path.join(RW, "pl003_final.tcmbpkg"), "rb").read()
    assert data.count(b'"atk_lo02_1": {') == 0
    out, pos = bytearray(), 0
    for i in range(3):
        j = data.index(b'"sp_atk02_1": {', pos)
        end = data.index(b"\n            },", j) + len(b"\n            },")
        block = data[j:end]
        if i >= len(TIERS):
            out += data[pos:end]
            pos = end
            continue
        t = TIERS[i]
        m = re.search(rb'"nexts": (\[[^\]]*\]|"[^"]*")', block)
        cur = re.findall(rb'"(\d+)"', m.group(1))
        if t["drop_next"]:
            assert t["drop_next"] in cur
            cur.remove(t["drop_next"])          # diag: base dam_fail off
        cur.append(str(t["uid_node"]).encode())
        rebuilt = b'"nexts": [' + b",".join(b'"%s"' % c for c in cur) + b']'
        block = block[:m.start()] + rebuilt + block[m.end():]
        vs = re.search(rb'"variables": \[(.*?)\]', block, re.S)
        parts = re.findall(rb'"([^"]*)"', vs.group(1))
        assert len(parts) == 23
        parts[12] = str(t["win"][0]).encode()
        parts[13] = str(t["win"][1]).encode()
        parts[14] = t["hit_stop"]
        parts[15] = b"0"
        varline = (b'"variables": ['
                   + b",".join(b'"%s"' % p for p in parts) + b'],')
        node = NODE_TMPL % {b"key": b"atk_lo02_1", b"uid": t["uid_node"],
                            b"vars": varline}
        out += data[pos:j] + block + node
        pos = end
        print("tcmb  tier %d: node %d vars14=%s win=%d-%d nexts=%s"
              % (i, t["uid_node"], t["hit_stop"].decode(), *t["win"],
                 b",".join(cur).decode()))
    out += data[pos:]
    open(os.path.join(RW, "pl003_diag.tcmbpkg"), "wb").write(out)
    print("tcmb  %d -> %d bytes" % (len(data), len(out)))


if __name__ == "__main__":
    patch_tadj()
    patch_tcmb()
    print("\nInstall: pl003_diag.tadjpkg -> pl003.tadjpkg")
    print("         pl003_diag.tcmbpkg -> pl003.tcmbpkg")
    print("         pl003_final.tactpkg -> pl003.tactpkg  (NOT the hitgrant one)")
