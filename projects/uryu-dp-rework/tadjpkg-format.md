---
name: tadjpkg-format
description: Byte layout of Bleach RoS .tadjpkg / .tcmbpkg files (pl003 Uryu) and parsing pitfalls
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3af549cc-8a4b-4d46-9fa0-c38e714e2ede
---

.tadjpkg (action adjust pkg): magic "actadj_pkg", u32 entry count @0x20, entry table @0x24 (72B rows: 64B shift-jis name + u32 offset + u32 size), then contiguous entry blobs. Blob: "adjb" + 3 null-terminated strings + 17 fixed bytes + u32 record count + records. Record: u32 uid + ascii name\0 + 14-byte middle `<IBffB>` (0, 0, f32 start_frame, f32 end_frame, 0) + u32 param count + shift-jis key\0value\0 pairs (floats as %.6f).

Pitfalls: some records (certain Attack_Bullet) have a nonzero final middle byte followed by an extra u32 before param count; ~36 of pl003's 244 entries have further layout variants (Warp, CameraFixedAngle, some Effect_OneShot) that a naive parser fails on — grep raw bytes instead of full-parsing when surveying. Editing safely = extract all blobs, verify contiguity, splice, rebuild every offset (see [[uryu-dp-rework-state]]; blueprint script add_tadj_record.py in project root).

.tcmbpkg: shift-jis JSON combo/branch graph. Nodes have input_text, input_event, nexts, variables[23]. No speed data lives there.
