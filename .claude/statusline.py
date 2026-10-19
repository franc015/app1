import sys, json, time

d = json.load(sys.stdin)

def k(n):
    n = n or 0
    return f"{n/1e6:.1f}M" if n >= 1e6 else f"{n/1e3:.1f}k" if n >= 1e3 else str(int(n))

def reset(ts):
    s = int(ts - time.time())
    if s <= 0: return "0m"
    h, m = divmod(s // 60, 60)
    return f"{h // 24}j{h % 24}h" if h >= 24 else f"{h}h{m:02d}" if h else f"{m}m"

cw = d.get("context_window") or {}
parts = [(d.get("model") or {}).get("display_name", "?")]
pct = cw.get("used_percentage")
parts.append(f"ctx {pct:.0f}% ({k(cw.get("total_input_tokens"))}/{k(cw.get("context_window_size"))})" if pct is not None else "ctx 0%")

# cumul de session : somme des requetes distinctes du journal
tin = tout = 0
seen = set()
try:
    for line in open(d["transcript_path"], encoding="utf-8"):
        try: e = json.loads(line)
        except ValueError: continue
        m = e.get("message")
        u = m.get("usage") if isinstance(m, dict) else None
        key = e.get("requestId") or e.get("uuid")
        if e.get("type") != "assistant" or not u or key in seen: continue
        seen.add(key)
        tin += u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
        tout += u.get("output_tokens", 0)
except (KeyError, OSError):
    pass
parts.append(f"session in {k(tin)} / out {k(tout)}")

rl = d.get("rate_limits") or {}
q = []
for key, label in (("five_hour", "5h"), ("seven_day", "7j")):
    w = rl.get(key)
    if w and w.get("used_percentage") is not None:
        q.append(f"{label} {w["used_percentage"]:.0f}%" + (f" (reset {reset(w["resets_at"])})" if w.get("resets_at") else ""))
sl = rl.get("spend_limit")
if sl and sl.get("used_percentage") is not None:
    q.append(f"budget {sl["used_percentage"]:.0f}%")
parts.append("quotas " + " | ".join(q) if q else "quotas n/d")

c = (d.get("cost") or {}).get("total_cost_usd")
if c is not None: parts.append(f"${c:.2f}")
print(" | ".join(parts))

