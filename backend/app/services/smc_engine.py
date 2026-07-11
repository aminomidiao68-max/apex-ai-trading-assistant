"""Apex AI — Pro SMC engine v2.
Features: BOS/CHoCH, Order Blocks, FVG (iFVG), Breaker Blocks,
Liquidity sweeps (buyside/sellside), Kill Zones, Session filters,
Order-flow delta (CVD proxy), AI narrative in Persian.
Created by Amin Omidi
"""
from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta
from typing import Any, List, Dict, Tuple

# ---------- Session / Kill-Zone detection (UTC time per candle) ----------
SESSION_TZ = timezone.utc
_SESSIONS = [
    # name, start_utc_hour, end_utc_hour, weight
    ("آسیا (توکیو)",    0,  8, 0.6),
    ("لندن",            7, 12, 1.0),
    ("نیویورک",        12, 17, 1.1),
    ("لندن+نیویورک",   12, 13, 1.4),  # overlap
    ("آمریکا پایانی",  17, 21, 0.7),
]

def _candles(raw):
    out = []
    for c in (raw or []):
        if not isinstance(c, dict):
            try: c = dict(c)
            except Exception: continue
        try:
            out.append({
                "t": float(c.get("t", c.get("time", 0))),
                "o": float(c.get("o", c.get("open", 0))),
                "h": float(c.get("h", c.get("high", 0))),
                "l": float(c.get("l", c.get("low", 0))),
                "c": float(c.get("c", c.get("close", 0))),
                "v": float(c.get("v", c.get("volume", 0))),
            })
        except Exception:
            pass
    out.sort(key=lambda x: x["t"])
    return out

def _swings(candles, left=3, right=3):
    highs, lows = [], []
    n = len(candles)
    for i in range(left, n - right):
        h = candles[i]["h"]; l = candles[i]["l"]
        if all(h > candles[i-k]["h"] for k in range(1, left+1)) and all(h > candles[i+k]["h"] for k in range(1, right+1)):
            highs.append((i, h))
        if all(l < candles[i-k]["l"] for k in range(1, left+1)) and all(l < candles[i+k]["l"] for k in range(1, right+1)):
            lows.append((i, l))
    return highs, lows

def _structure(highs, lows, candles):
    events = []
    if not highs or not lows:
        return events, "neutral", None, None
    bos_hh = max(p for _, p in highs)
    bos_ll = min(p for _, p in lows)
    # initial trend guess using swing positions
    first_h = highs[0][0]; first_l = lows[0][0]
    trend = "bullish" if first_h > first_l else "bearish"
    last_ch = None
    for i, c in enumerate(candles):
        h = c["h"]; l = c["l"]
        if trend == "bullish":
            if l < bos_ll:
                events.append({"type": "CHoCH", "index": i, "price": l, "direction": "bearish"}); trend = "bearish"; bos_ll = l; last_ch = "bearish"
            elif h > bos_hh:
                events.append({"type": "BOS", "index": i, "price": h, "direction": "bullish"}); bos_hh = h; last_ch = "bullish"
        else:
            if h > bos_hh:
                events.append({"type": "CHoCH", "index": i, "price": h, "direction": "bullish"}); trend = "bullish"; bos_hh = h; last_ch = "bullish"
            elif l < bos_ll:
                events.append({"type": "BOS", "index": i, "price": l, "direction": "bearish"}); bos_ll = l; last_ch = "bearish"
    return events, trend, bos_hh, bos_ll

def _fvg(candles):
    out = []
    n = len(candles)
    for i in range(n - 2):
        a, b, c0 = candles[i], candles[i+1], candles[i+2]
        # bullish FVG: gap up
        if a["h"] < c0["l"]:
            out.append({"kind": "bullish", "index": i+1, "top": c0["l"], "bottom": a["h"], "mitigated": False, "size_pct": (c0["l"]-a["h"])/a["h"]*100})
        # bearish FVG: gap down
        if a["l"] > c0["h"]:
            out.append({"kind": "bearish", "index": i+1, "top": a["l"], "bottom": c0["h"], "mitigated": False, "size_pct": (a["l"]-c0["h"])/c0["h"]*100})
        # inverse FVG (iFVG) — continuation
        if i >= 1 and i+3 < n:
            prev = candles[i-1]; nxt = candles[i+3]
            if prev["h"] < nxt["l"] and a["h"] >= c0["l"]:
                out.append({"kind": "bullish", "index": i+2, "top": nxt["l"], "bottom": prev["h"], "mitigated": False, "inverse": True, "size_pct": (nxt["l"]-prev["h"])/prev["h"]*100})
            if prev["l"] > nxt["h"] and a["l"] <= c0["h"]:
                out.append({"kind": "bearish", "index": i+2, "top": prev["l"], "bottom": nxt["h"], "mitigated": False, "inverse": True, "size_pct": (prev["l"]-nxt["h"])/nxt["h"]*100})
    for g in out:
        for j in range(g["index"]+2, n):
            cc = candles[j]
            if g["kind"] == "bullish" and cc["l"] <= g["bottom"]:
                g["mitigated"] = True; break
            if g["kind"] == "bearish" and cc["h"] >= g["top"]:
                g["mitigated"] = True; break
    return out

def _obs(candles, events):
    obs = []
    for ev in events:
        if ev["type"] not in ("BOS", "CHoCH"): continue
        i = ev["index"]; d = ev["direction"]; found = None
        for k in range(i-1, max(0, i-25), -1):
            c = candles[k]
            bull = c["c"] > c["o"]
            body_up = abs(c["c"] - c["o"]) >= (c["h"] - c["l"]) * 0.35
            if d == "bullish" and not bull:
                found = k; break
            if d == "bearish" and bull:
                found = k; break
        if found is None: continue
        oc = candles[found]
        ob = {"kind": d, "index": found, "top": oc["h"], "bottom": oc["l"],
              "mitigated": False, "volume": oc["v"]}
        obs.append(ob)
    # mark mitigated
    for ob in obs:
        mid = (ob["top"]+ob["bottom"])/2
        for j in range(ob["index"]+1, len(candles)):
            cc = candles[j]
            if ob["kind"] == "bullish" and cc["l"] <= mid:
                ob["mitigated"] = True; break
            if ob["kind"] == "bearish" and cc["h"] >= mid:
                ob["mitigated"] = True; break
    return obs

def _breakers(candles, obs):
    br = []
    for ob in obs:
        if not ob["mitigated"]: continue
        tested = False
        for j in range(ob["index"], len(candles)):
            cc = candles[j]
            if ob["kind"] == "bullish" and cc["h"] >= ob["top"]: tested = True; break
            if ob["kind"] == "bearish" and cc["l"] <= ob["bottom"]: tested = True; break
        if tested:
            br.append({**ob, "kind": "bearish" if ob["kind"] == "bullish" else "bullish"})
    return br

def _liquidity(candles, highs, lows, lookback=8):
    """Identify equal highs/lows (EQH/EQL) and recent sweeps = buysiside/sellside liquidity."""
    out = []
    tol = 0.0008  # 0.08% tolerance for "equal"
    # EQH / EQL detection
    for i in range(1, len(highs)):
        i1, p1 = highs[i-1]; i2, p2 = highs[i]
        if abs(p1-p2)/p1 < tol and (i2-i1) <= 20:
            out.append({"kind": "eqh", "index": i2, "price": p2})
    for i in range(1, len(lows)):
        i1, p1 = lows[i-1]; i2, p2 = lows[i]
        if abs(p1-p2)/p1 < tol and (i2-i1) <= 20:
            out.append({"kind": "eql", "index": i2, "price": p2})
    # Liquidity sweeps
    for si, sp in highs:
        for j in range(si+1, min(si+8, len(candles))):
            if candles[j]["h"] > sp and candles[j]["c"] < sp:
                out.append({"kind": "sellside_liq", "index": si, "sweep": j, "price": sp})
                break
    for si, sp in lows:
        for j in range(si+1, min(si+8, len(candles))):
            if candles[j]["l"] < sp and candles[j]["c"] > sp:
                out.append({"kind": "buyside_liq", "index": si, "sweep": j, "price": sp})
                break
    # recent high/low liquidity (last N candles)
    if candles:
        recent = candles[-lookback:]
        rh = max(c["h"] for c in recent); rl = min(c["l"] for c in recent)
        out.append({"kind": "recent_high_liq", "index": len(candles)-1, "price": rh})
        out.append({"kind": "recent_low_liq",  "index": len(candles)-1, "price": rl})
    return out

def _orderflow(candles, window=14):
    """Simple CVD/delta proxy from candle direction × volume -> order flow score."""
    if not candles: return {"delta":0.0, "pressure":"neutral", "cvd_curve":[]}
    cvd = 0.0; curve = []
    for c in candles[-window*3:]:
        body = c["c"] - c["o"]; rng = c["h"] - c["l"]
        if rng <= 0: continue
        buying = abs(body) / rng if body > 0 else 0
        selling = abs(body) / rng if body < 0 else 0
        delta = (buying - selling) * c["v"]
        cvd += delta
        curve.append({"t": c["t"], "cvd": cvd})
    last = candles[-window:]
    dlt = 0
    for c in last:
        body = c["c"] - c["o"]; rng = c["h"] - c["l"]
        if rng <= 0: continue
        dlt += (1 if body > 0 else -1) * c["v"] * abs(body)/rng
    vol = sum(c["v"] for c in last) or 1
    norm = dlt / vol
    pressure = "buy" if norm > 0.1 else "sell" if norm < -0.1 else "neutral"
    return {"delta": round(norm, 3), "pressure": pressure, "cvd_curve": curve[-30:]}

def _sessions(candles, interval_minutes):
    """Tag each candle with its session, return kill-zones (high-weight windows) as shaded zones."""
    if not candles or candles[0]["t"] <= 0:
        return [], []
    zones = []
    names = []
    # Determine bucket step in minutes to use as bar width
    step = interval_minutes or 15
    for i, c in enumerate(candles):
        try:
            dt = datetime.fromtimestamp(c["t"], tz=SESSION_TZ)
        except Exception: continue
        h = dt.hour + dt.minute/60
        active = None
        for name, s, e, w in _SESSIONS:
            if s <= h < e:
                if w >= 1.3:
                    zones.append({"kind": "killzone", "name": name, "index": i, "weight": w})
                    if name not in names: names.append(name)
                break
    # Compress contiguous kill-zone candles into ranges
    compressed = []
    for z in zones:
        if compressed and compressed[-1]["name"] == z["name"] and z["index"] == compressed[-1]["end"]+1:
            compressed[-1]["end"] = z["index"]
        else:
            compressed.append({"kind": "killzone", "name": z["name"], "start": z["index"], "end": z["index"], "weight": z["weight"]})
    # Return as list of zones (top/bottom = price range will be filled by overlay on app side using min/max of zone)
    out = []
    for z in compressed:
        seg = candles[z["start"]:z["end"]+1]
        if not seg: continue
        out.append({"kind": "KZ", "name": z["name"], "side": z["weight"] >= 1.3 and "high" or "mid",
                    "start_idx": z["start"], "end_idx": z["end"],
                    "top": max(x["h"] for x in seg), "bottom": min(x["l"] for x in seg),
                    "index": z["start"]})
    return out, names

def _parse_tf_minutes(tf):
    try:
        t = (tf or "15").lower().strip()
        if t.endswith("min") or t.endswith("m"):
            return int(''.join(ch for ch in t if ch.isdigit()) or 15)
        if t.endswith("h"): return int(''.join(ch for ch in t if ch.isdigit()) or 1) * 60
        if t.endswith("d"): return 1440
    except Exception: pass
    return 15

def _narrative(bias, direction, conf, oflow, active_sessions, liq_side, near_ob, near_fvg, price, note):
    """Persian narrative for the trade setup."""
    side_label = {"long": "خرید (لانگ)", "short": "فروش (شورت)", "neutral": "انتظار"}[direction]
    trend_label = {"bullish": "صعودی", "bearish": "نزولی", "neutral": "خنثی"}[bias]
    session_txt = "، ".join(active_sessions) if active_sessions else "خارج از سشن اصلی"
    # confluence text
    reasons = []
    if bias == "bullish": reasons.append("ساختار بازار صعودی (Higher High)")
    if bias == "bearish": reasons.append("ساختار بازار نزولی (Lower Low)")
    if near_ob:
        reasons.append(("اوردر بلاک " + ("صعودی" if direction=="long" else "نزولی") + " تایید شده"))
    if near_fvg: reasons.append("FVG پُر نشده در مسیر")
    if oflow["pressure"] == "buy": reasons.append("فشار خرید در اوردر فلو")
    if oflow["pressure"] == "sell": reasons.append("فشار فروش در اوردر فلو")
    if liq_side == "sellside": reasons.append("لیکوئیدیتی سل‌ساید (سقف‌ها) جمع شد")
    if liq_side == "buyside": reasons.append("لیکوئیدیتی بای‌ساید (کف‌ها) جمع شد")
    rec = "◀ سناریوی پیشنهادی: " + side_label
    verdict = "با کانفلونس " + str(conf) + "/4. "
    if conf >= 3 and direction != "neutral":
        verdict += "✅ ستاپ با احتمال بالا."
    elif conf == 2 and direction != "neutral":
        verdict += "⚠️ ستاپ متوسط — مدیریت سرمایه رعایت شود."
    else:
        verdict += "❌ ستاپ ضعیف — منتظر تایید بیشتر بمانید."
    body = "بر اساس تحلیل ساختار، روند " + trend_label + " است. "
    if reasons:
        body += "دلایل: " + "؛ ".join(reasons[:5]) + ". "
    body += "سشن فعال: " + session_txt + ". " + verdict
    return {"side": side_label, "trend": trend_label, "summary": body, "recommendation": rec, "confluence": conf}

def analyze(candles_raw, symbol="", timeframe=""):
    candles = _candles(candles_raw)
    if len(candles) < 30:
        return {"symbol":symbol, "timeframe":timeframe, "price":0, "bias":"neutral",
                "direction":"neutral", "confluence":0,
                "note":"حداقل ۳۰ کندل برای تحلیل لازم است.", "status":"insufficient_data",
                "levels":{"entry":None,"sl":None,"tp":None},
                "events":[], "order_blocks":[], "fvg":[], "breakers":[],
                "inducements":[], "sessions":[], "killzones":[],
                "orderflow": {"delta":0,"pressure":"neutral","cvd_curve":[]},
                "ai": {"side":"انتظار","trend":"خنثی","summary":"داده کافی نیست.","recommendation":"منتظر بمانید","confluence":0},
                "overlay":{"lines":[],"zones":[],"labels":[]},
                "candles_count": len(candles), "created_by":"Amin Omidi"}
    highs, lows = _swings(candles)
    events, bias, bh, bl = _structure(highs, lows, candles)
    fvgs = _fvg(candles)
    obs = _obs(candles, events)
    br = _breakers(candles, obs)
    liq = _liquidity(candles, highs, lows)
    oflow = _orderflow(candles)
    kz, session_names = _sessions(candles, _parse_tf_minutes(timeframe))

    price = candles[-1]["c"]
    active_obs = [o for o in obs if not o["mitigated"]]
    active_fvg = [g for g in fvgs if not g["mitigated"]]

    entry = sl = tp = None; direction = "neutral"; conf = 0
    near_ob = False; near_fvg = False; liq_side = None

    # confluence logic
    if bias == "bullish":
        cands = [o for o in active_obs if o["kind"]=="bullish" and o["top"] < price]
        cands += [b for b in br if b["kind"]=="bullish" and b["top"] < price]
        if cands:
            z = max(cands, key=lambda x: x["top"])
            entry = z["top"]; sl = z["bottom"] - 0.0004*z["bottom"]
            tp = price + (price - sl) * 2
            direction = "long"; conf += 2; near_ob = True
        # if price inside bullish FVG
        if any(g["kind"]=="bullish" and g["bottom"] < price < g["top"]*1.01 for g in active_fvg):
            conf += 1; near_fvg = True
        if oflow["pressure"] == "buy": conf += 1
        # liq: last sweep was buyside (swept lows -> now up)
        recent_sweeps = [l for l in liq if l.get("kind") in ("buyside_liq","sellside_liq")]
        if recent_sweeps and recent_sweeps[-1]["kind"] == "buyside_liq":
            conf += 1; liq_side = "buyside"
    elif bias == "bearish":
        cands = [o for o in active_obs if o["kind"]=="bearish" and o["bottom"] > price]
        cands += [b for b in br if b["kind"]=="bearish" and b["bottom"] > price]
        if cands:
            z = min(cands, key=lambda x: x["bottom"])
            entry = z["bottom"]; sl = z["top"] + 0.0004*z["top"]
            tp = price - (sl - price) * 2
            direction = "short"; conf += 2; near_ob = True
        if any(g["kind"]=="bearish" and g["top"] > price > g["bottom"]*0.99 for g in active_fvg):
            conf += 1; near_fvg = True
        if oflow["pressure"] == "sell": conf += 1
        recent_sweeps = [l for l in liq if l.get("kind") in ("buyside_liq","sellside_liq")]
        if recent_sweeps and recent_sweeps[-1]["kind"] == "sellside_liq":
            conf += 1; liq_side = "sellside"
    conf = min(conf, 4)

    # Build overlay
    zones = []
    for o in active_obs[-8:]:
        zones.append({"kind":"OB","side":o["kind"],"index":o["index"],"top":o["top"],"bottom":o["bottom"]})
    for g in active_fvg[-8:]:
        tag = "FVG" if not g.get("inverse") else "iFVG"
        zones.append({"kind":tag,"side":g["kind"],"index":g["index"],"top":g["top"],"bottom":g["bottom"]})
    for b in br[-5:]:
        zones.append({"kind":"BRK","side":b["kind"],"index":b["index"],"top":b["top"],"bottom":b["bottom"]})
    for k in kz[-6:]:
        zones.append({"kind":"KZ","side":k["side"],"index":k["index"],"top":k["top"],"bottom":k["bottom"],
                      "name":k["name"],"start_idx":k["start_idx"],"end_idx":k["end_idx"]})

    labels = []
    for ev in events[-15:]:
        labels.append({"kind":ev["type"],"dir":ev["direction"],"index":ev["index"],"price":ev["price"]})
    for li in liq[-12:]:
        labels.append({"kind":"LIQ","dir":li["kind"],"index":li.get("sweep",li["index"]),"price":li["price"]})

    lines = []
    if bh is not None: lines.append({"kind":"high","price":bh})
    if bl is not None: lines.append({"kind":"low","price":bl})
    # Nearby liquidity lines
    for li in liq[-6:]:
        if li["kind"] in ("eqh","eql","recent_high_liq","recent_low_liq"):
            lines.append({"kind": li["kind"], "price": li["price"]})

    note = "روند خنثی — منتظر تایید"
    if direction == "long" and conf >= 2: note = "ناحیه لانگ بالقوه با تایید روند و اوردر فلو"
    if direction == "short" and conf >= 2: note = "ناحیه شورت بالقوه با تایید روند و اوردر فلو"
    if bias == "bullish" and not entry: note = "روند صعودی، منتظر پولبک به ناحیه ORB/OB"
    if bias == "bearish" and not entry: note = "روند نزولی، منتظر پولبک به ناحیه ORB/OB"

    ai = _narrative(bias, direction, conf, oflow, session_names, liq_side, near_ob, near_fvg, price, note)

    return {
        "symbol": symbol, "timeframe": timeframe, "price": price,
        "bias": bias, "direction": direction, "confluence": conf,
        "note": note, "status": "ok",
        "levels": {"entry": entry, "sl": sl, "tp": tp},
        "events": [{"kind":e["type"],"dir":e["direction"],"index":e["index"],"price":e["price"]} for e in events[-10:]],
        "order_blocks": [{"kind":o["kind"],"top":o["top"],"bottom":o["bottom"],"index":o["index"]} for o in active_obs[-8:]],
        "fvg": [{"kind":g["kind"],"top":g["top"],"bottom":g["bottom"],"index":g["index"],
                 "inverse": bool(g.get("inverse")), "size_pct": g.get("size_pct",0)} for g in active_fvg[-8:]],
        "breakers": [{"kind":b["kind"],"top":b["top"],"bottom":b["bottom"],"index":b["index"]} for b in br[-5:]],
        "inducements": [{"kind":l["kind"],"price":l["price"],"index":l.get("sweep",l["index"])} for l in liq[-10:] if "sweep" in l or l["kind"] in ("eqh","eql")],
        "sessions": session_names,
        "killzones": [{"kind":k["kind"],"name":k["name"],"side":k["side"],
                       "start_idx":k["start_idx"],"end_idx":k["end_idx"],
                       "top":k["top"],"bottom":k["bottom"],"index":k["index"]} for k in kz],
        "orderflow": oflow,
        "ai": ai,
        "overlay": {"lines": lines, "zones": zones, "labels": labels},
        "candles_count": len(candles),
        "created_by": "Amin Omidi"
    }


def detect_smc_features(candles, trend="neutral"):
    """Backward-compat wrapper used by signal_engine."""
    r = analyze(candles)
    obs = r.get("order_blocks", [])
    fvgs = r.get("fvg", [])
    liq = r.get("inducements", [])
    bos = [e for e in r.get("events",[]) if e.get("kind")=="BOS"]
    choch = [e for e in r.get("events",[]) if e.get("kind")=="CHoCH"]
    return {
        "bias": r.get("bias","neutral"),
        "bos": bos, "choch": choch,
        "order_blocks": obs, "fvg": fvgs, "liquidity_sweeps": liq,
        "active_ob": None,
        "entry": (r.get("levels") or {}).get("entry"),
        "sl": (r.get("levels") or {}).get("sl"),
        "tp": (r.get("levels") or {}).get("tp"),
    }
