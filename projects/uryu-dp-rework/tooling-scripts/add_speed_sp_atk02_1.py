#!/usr/bin/env python3
# =============================================================================
#  add_speed_sp_atk02_1.py   (v9 - + hit-only install via Enhance retiming)
#
#  Shapes Uryu's DP (BASE/EVO/REV) after pl051 True Shikai Ichigo's sp_atk02,
#  the reference "true DP". Three sections, all idempotent (existing records
#  of each type on the target entries are stripped before writing, offsets
#  fully rebuilt):
#
#  1) OPPONENT SLOW (the real "DP speed"): Ichigo's DP has NO WorldSpeedChange;
#     instead it slows the OPPONENT via ObjectSpeedChange while Ichigo himself
#     moves at full speed. Copied 1:1 (his file also has the atk02/_1 split):
#       sp_atk02   : window 0->60  frame=-1 speed=0.01 end_change_frame=0
#                    end_change_speed=1.0     (Uryu's rework had 0.024/15/0.2)
#       sp_atk02_1 : window 0->60  frame=-1 speed=0.10 end_change_frame=10
#                    end_change_speed=0.2     (Uryu had none)
#
#  2) WORLD-SPEED CURVE: default EMPTY for the faithful Ichigo copy. To layer
#     the custom freeze-pop back on top, add (real_frames, Speed) stages, e.g.
#     CURVE = [(3, 0.01), (3, 0.25), (3, 1.0), (3, 2.0)]
#
#  3) TRUE-DP INVINCIBILITY (confirmed working in-game): Ichigo-style
#     Protect type=完全無敵 protect_react=ヒット判定あり on all six entries:
#     stance 0->120, damaging part 0->15 (melee is 5-20; raise
#     DAMAGE_INVULN_END to 20.0 to also cover the trade window).
#
#  Usage: python add_speed_sp_atk02_1.py   (from the project root)
# =============================================================================
import struct, os, sys


# ------------------------------- SETTINGS ------------------------------------
INPUT_FILE  = os.path.join("Reworked Uryu", "pl003.tadjpkg")
OUTPUT_FILE = os.path.join("Reworked Uryu", "pl003_dp.tadjpkg")

# --- 1) opponent slow, values byte-copied from pl051 Ichigo -------------------
STANCE_OBJSPEED = dict(window=(0.0, 60.0), frame="-1.000000", speed="0.010000",
                       end_change_frame="0.000000", end_change_speed="1.000000")
DAMAGE_OBJSPEED = dict(window=(0.0, 60.0), frame="-1.000000", speed="0.100000",
                       end_change_frame="10.000000", end_change_speed="0.200000")

# --- 2) world-speed curve stages: (real_frames_at_60fps, Speed) ---------------
# Layered ON TOP of the Ichigo opponent-slow (both effects active at once).
CURVE = [
    (5, 0.001),   # ~5 real frames near-frozen
    (5, 0.01),    # ~5 real frames slightly less frozen
    (5, 0.1),     # ~5 real frames at 10% speed, then normal
]

# --- 3) invincibility (cloned from pl051 Ichigo's true DP) --------------------
PROTECT_TYPE   = "完全無敵"          # full invulnerability
PROTECT_REACT  = "ヒット判定あり"    # Ichigo's DP setting
STANCE_INVULN_END = 120.0            # sp_atk02 covered 0 -> this
DAMAGE_INVULN_END = 80.0             # sp_atk02_1 covered 0 -> this

# --- 4) frame data (OPTIONAL; None = script leaves these fields alone so
#        Berg's hand edits in his editor are never overwritten) ----------------
MELEE_WINDOW = None           # e.g. (15.0, 30.0) to have the script manage it
CANCEL_START = None           # e.g. 200.0

# --- 5) RETIRED: SlowMotionRate proved a no-op in-game for recovery. The
#        working recovery is the act_data exit chain into dam_fail, handled by
#        patch_dp_intro_anim.py (RECOVERY_NEXT). Any leftover SlowMotionRate
#        records on the targets are stripped on every run. --------------------
RECOVERY_SLOW = None

# --- 6) hit-only install: the whiff branch exits sp_atk02_1 at ~frame 110
#        (WHIFF_STAGGER min_frame in patch_dp_intro_anim.py), so frames after
#        that are only reached when the DP CONNECTED. Moving the Enhance
#        record (install granter, vanilla window 6->10) past the branch point
#        makes the install hit-only. Set None to leave Enhance windows alone.
ENHANCE_HIT_WINDOW = (10, 20)

# --- targets ------------------------------------------------------------------
STANCES = ["1_normal_attack_sp_atk02",
           "2_evo_attack_evo_sp_atk02",
           "3_rev_attack_rev_sp_atk02"]
DAMAGES = ["1_normal_attack_sp_atk02_1",
           "2_evo_attack_evo_sp_atk02_1",
           "3_rev_attack_rev_sp_atk02_1"]
UID = {  # (record kind, entry) -> unique id;   curve stages use base+i
    ("recovery", 0): 0x51D0AA81, ("recovery", 1): 0x51D0AA82, ("recovery", 2): 0x51D0AA83,
    ("objspeed", 0): 0x51D0AA61, ("objspeed", 1): 0x51D0AA62, ("objspeed", 2): 0x51D0AA63,
    ("objspeed", 3): 0x51D0AA71, ("objspeed", 4): 0x51D0AA72, ("objspeed", 5): 0x51D0AA73,
    ("curve",    0): 0x51D0AA10, ("curve",    1): 0x51D0AA20, ("curve",    2): 0x51D0AA30,
    ("protect",  0): 0x51D0AA41, ("protect",  1): 0x51D0AA42, ("protect",  2): 0x51D0AA43,
    ("protect",  3): 0x51D0AA51, ("protect",  4): 0x51D0AA52, ("protect",  5): 0x51D0AA53,
}
# -----------------------------------------------------------------------------


def stages_to_windows(curve):
    out, pos = [], 0.0
    for real_frames, speed in curve:
        span = real_frames * speed
        out.append((pos, pos + span, speed))
        pos += span
    return out


def build_record(uid, name, start, end, params):
    rec  = struct.pack("<I", uid)
    rec += name.encode("ascii") + b"\x00"
    rec += struct.pack("<IBffB", 0, 0, float(start), float(end), 0)
    rec += struct.pack("<I", len(params))
    for k, v in params:
        rec += k.encode("shift_jis") + b"\x00" + v.encode("shift_jis") + b"\x00"
    return rec


def find_record_count_pos(blob):
    p = 4                                    # skip "adjb"
    for _ in range(3):                       # skip the 3 text strings
        p = blob.index(b"\x00", p) + 1
    p += 17                                  # skip the 17 fixed bytes
    return p


def find_named_record(blob, rec_name):
    key = rec_name.encode("ascii") + b"\x00"
    j = blob.find(key)
    if j < 0:
        return None
    start = j - 4                            # uid sits before the name
    p = j + len(key)
    flag = blob[p + 13]                      # last byte of the 14-byte middle
    p += 14
    if flag != 0:                            # rare variant: extra u32 follows
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


def objspeed_record(uid, cfg):
    return build_record(uid, "ObjectSpeedChange", cfg["window"][0], cfg["window"][1],
                        [("frame", cfg["frame"]), ("speed", cfg["speed"]),
                         ("end_change_frame", cfg["end_change_frame"]),
                         ("end_change_speed", cfg["end_change_speed"])])


def poke_mid_floats(blob, rec_name, expect_olds, new_vals):
    """Overwrite the two window floats of an existing record, sanity-checked."""
    key = rec_name.encode("ascii") + b"\x00"
    j = blob.find(key)
    assert j >= 0, rec_name
    p = j + len(key) + 5
    cur = struct.unpack_from("<ff", blob, p)
    cur = (round(cur[0], 3), round(cur[1], 3))
    if expect_olds is not None:
        assert cur in expect_olds, (rec_name, cur)
    struct.pack_into("<ff", blob, p, *new_vals)
    return cur


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    in_path  = INPUT_FILE  if os.path.isabs(INPUT_FILE)  else os.path.join(here, INPUT_FILE)
    out_path = OUTPUT_FILE if os.path.isabs(OUTPUT_FILE) else os.path.join(here, OUTPUT_FILE)

    if not os.path.exists(in_path):
        sys.exit("ERROR: input file not found: " + in_path)
    data = open(in_path, "rb").read()
    if data[:10] != b"actadj_pkg":
        sys.exit("ERROR: this does not look like a .tadjpkg file: " + in_path)

    count = struct.unpack_from("<I", data, 0x20)[0]
    entries = []
    off = 0x24
    for _ in range(count):
        name = data[off:off + 64].split(b"\x00")[0].decode("shift_jis", "replace")
        start, size = struct.unpack_from("<II", data, off + 64)
        entries.append((name, start, size))
        off += 72

    blobs = [bytearray(data[o:o + s]) for _, o, s in entries]
    pos = 0x24 + count * 72
    for (nm, o, s), _b in zip(entries, blobs):
        if o != pos:
            sys.exit("ERROR: file is not contiguous at entry '%s'. Aborting." % nm)
        pos += s

    def entry_index(name):
        idx = next((i for i, e in enumerate(entries) if e[0] == name), None)
        if idx is None:
            sys.exit("ERROR: target entry not found: " + name)
        return idx

    # ---- 1) opponent slow (Ichigo clone) ----
    print("opponent slow (ObjectSpeedChange, Ichigo values):")
    for slot, (tname, cfg) in enumerate(
            [(n, STANCE_OBJSPEED) for n in STANCES] +
            [(n, DAMAGE_OBJSPEED) for n in DAMAGES]):
        idx = entry_index(tname)
        rec = objspeed_record(UID[("objspeed", slot)], cfg)
        blobs[idx], removed = strip_and_insert(blobs[idx], "ObjectSpeedChange", [rec])
        print("   %-32s speed=%s end=(%s,%s) (replaced %d)"
              % (tname, cfg["speed"], cfg["end_change_frame"],
                 cfg["end_change_speed"], removed))

    # ---- 2) world-speed curve ----
    windows = stages_to_windows(CURVE)
    if windows:
        print("world-speed curve:")
        for (a, b, sp), (rf, _s) in zip(windows, CURVE):
            print("   %-8g -> %-8g @ Speed=%-6g (~%g real frames)" % (a, b, sp, rf))
    else:
        print("world-speed curve: none (Ichigo has no WorldSpeedChange on his DP)")
    for i, tname in enumerate(DAMAGES):
        idx = entry_index(tname)
        recs = [build_record(UID[("curve", i)] + k, "WorldSpeedChange", a, b,
                             [("Speed", "%.6f" % sp)])
                for k, (a, b, sp) in enumerate(windows)]
        blobs[idx], removed = strip_and_insert(blobs[idx], "WorldSpeedChange", recs)
        if removed or recs:
            print("   %-32s -%d +%d curve records" % (tname, removed, len(recs)))

    # ---- 3) true-DP invincibility ----
    print("invincibility (Protect %s / %s):" % (PROTECT_TYPE, PROTECT_REACT))
    for slot, (tname, endf) in enumerate(
            [(n, STANCE_INVULN_END) for n in STANCES] +
            [(n, DAMAGE_INVULN_END) for n in DAMAGES]):
        idx = entry_index(tname)
        rec = build_record(UID[("protect", slot)], "Protect", 0.0, endf,
                           [("type", PROTECT_TYPE), ("protect_react", PROTECT_REACT)])
        blobs[idx], removed = strip_and_insert(blobs[idx], "Protect", [rec])
        print("   %-32s 0 -> %-4g (replaced %d)" % (tname, endf, removed))

    # ---- 4) optional frame data pokes (skipped when None) ----
    if MELEE_WINDOW or CANCEL_START:
        print("frame data (sp_atk02_1):")
        for tname in DAMAGES:
            idx = entry_index(tname)
            blob = bytearray(blobs[idx])
            if MELEE_WINDOW:
                poke_mid_floats(blob, "Attack_Melee", None, MELEE_WINDOW)
            if CANCEL_START:
                poke_mid_floats(blob, "CancelTiming", None, (CANCEL_START, -1.0))
            blobs[idx] = blob
            print("   %-32s melee=%s cancel=%s" % (tname, MELEE_WINDOW, CANCEL_START))
    else:
        print("frame data: untouched (Berg manages melee/cancel by hand)")

    # ---- 5) strip retired SlowMotionRate records; re-add only if configured ----
    for tname in DAMAGES:
        idx = entry_index(tname)
        blobs[idx], removed = strip_and_insert(blobs[idx], "SlowMotionRate", [])
        if removed:
            print("   %-32s stripped %d retired SlowMotionRate" % (tname, removed))
    if RECOVERY_SLOW:
        w, rate = RECOVERY_SLOW["window"], RECOVERY_SLOW["rate"]
        extra = (w[1] - w[0]) * (float(rate) - 1.0)
        print("recovery slow (SlowMotionRate): %g -> %g @ %s  (~+%g real frames)"
              % (w[0], w[1], rate.rstrip('0').rstrip('.'), extra))
        for i, tname in enumerate(DAMAGES):
            idx = entry_index(tname)
            rec = build_record(UID[("recovery", i)], "SlowMotionRate", w[0], w[1],
                               [("slow_motion_rate", rate)])
            blobs[idx], removed = strip_and_insert(blobs[idx], "SlowMotionRate", [rec])
            print("   %-32s (replaced %d)" % (tname, removed))

    # ---- 6) hit-only install: retime the Enhance record ----
    if ENHANCE_HIT_WINDOW:
        print("install (Enhance) hit-only window:")
        for tname in DAMAGES:
            idx = entry_index(tname)
            blob = bytearray(blobs[idx])
            if blob.find(b"Enhance\x00") < 0:
                print("   %-32s no Enhance record (skipped)" % tname)
                continue
            was = poke_mid_floats(blob, "Enhance", None, ENHANCE_HIT_WINDOW)
            blobs[idx] = blob
            print("   %-32s Enhance %s -> %s" % (tname, was, ENHANCE_HIT_WINDOW))

    # ---- rebuild the whole file with fresh offsets ----
    out = bytearray(data[:0x24])
    out += b"\x00" * (count * 72)
    struct.pack_into("<I", out, 0x20, count)
    pos = 0x24 + count * 72
    for i, (name, _o, _s) in enumerate(entries):
        nb  = name.encode("shift_jis")
        row = 0x24 + i * 72
        out[row:row + 64] = nb + b"\x00" * (64 - len(nb))
        struct.pack_into("<II", out, row + 64, pos, len(blobs[i]))
        pos += len(blobs[i])
    for bl in blobs:
        out += bl

    open(out_path, "wb").write(out)
    print("\nfile size : %d -> %d (%+d)" % (len(data), len(out), len(out) - len(data)))
    print("saved to  : %s" % out_path)
    print("Rename to pl003.tadjpkg for the game.")


if __name__ == "__main__":
    main()
