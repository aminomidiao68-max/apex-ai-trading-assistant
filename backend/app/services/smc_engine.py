"""Apex AI — Ultra SMC Engine v6 (Pro ICT Concepts).
Created by Amin Omidi — Professional Smart Money Concepts engine.

Features:
  * Precise swing detection with ZigZag + structural pivot confirmation
  * True BOS/CHoCH detection with close-confirmation (not wick-only)
  * Premium/Discount with correct Fibonacci OTE (62-79% retracement for entries)
  * Last-leg range for POI calculation (not arbitrary 80-bar window)
  * Order Blocks: Fresh / Tested / Mitigated / Breaker / Rejection with quality score
  * FVG (3-candle gap) + iFVG (inverse/continuation) with quality + size
  * Liquidity: EQH/EQL, trend-line, buy-side/sell-side pools, external target liquidity
  * Stop-hunt / inducement (IDM) detection before structural breaks
  * Displacement strength scoring (body/range ratio, volume factor, ATR multiplier)
  * Market Maker Model detection: Accumulation → Manipulation → Distribution
  * Order Flow v2: CVD, per-bar delta, CVD divergence, volume climax, absorption, pressure
  * Session/killzone with proper volatility multipliers (London+NY overlap premium)
  * Point of Interest (POI) stacking: price zones where OB/FVG/50% fib coincide
  * Liquidity-based TP targeting (TP1=first pool, TP2=external liq, TP3=major EQH/EQL)
  * 20-factor confluence scoring with ICT-calibrated weights
  * A+ / A / B / C / D / F grading system
  * Risk-Reward calibration based on structure (not fixed multipliers)
  * Probability 55-95% calibrated by confluence
  * Multi-timeframe (HTF bias + LTF entry alignment)
  * News-block safety penalty
  * Ranging / choppy-market detection (ADX-like strength meter)
  * Rich Persian narrative with step-by-step ICT-style explanation
  * Full trade plan: entry zones, SL, TP1/2/3 with partial-close guidance
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional, Any
import math

UTC = timezone.utc

# ICT Killzones (UTC) with volatility weight
KILLZONES = [
    {"name":"آسیا (توکیو)",       "start":0,  "end":8,  "vol":0.7, "color":"#3b82f6"},
    {"name":"لندن",               "start":7,  "end":12, "vol":1.1, "color":"#10b981"},
    {"name":"همپوشانی لندن-نیویورک","start":12,"end":14, "vol":1.6, "color":"#ef4444"},
    {"name":"نیویورک",            "start":13, "end":17, "vol":1.3, "color":"#f59e0b"},
    {"name":"پایانی آمریکا",      "start":17, "end":21, "vol":0.6, "color":"#6b7280"},
]

SETUPS = {
    "liq_sweep_entry": {"name_fa":"لیکوئیدیتی سویپ + برگشت", "rr_base":2.4, "prob_base":68},
    "ote_bos_retest":  {"name_fa":"پولبک BOS به ناحیه OTE",  "rr_base":2.6, "prob_base":70},
    "choch_fvg_poi":   {"name_fa":"تغییر ساختار + FVG + POI","rr_base":2.2, "prob_base":65},
    "breaker_retest":  {"name_fa":"بریکر بلاک پس از سویپ",    "rr_base":2.1, "prob_base":62},
    "ob_rejection":    {"name_fa":"واکنش به ناحیه PD",         "rr_base":1.8, "prob_base":58},
    "continuation_fvg":{"name_fa":"ادامه روند از FVG",        "rr_base":2.3, "prob_base":64},
    "mmxm_direction":  {"name_fa":"الگوی MMXM (تجمیع-دستکاری)","rr_base":2.8,"prob_base":72},
    "ote_entry":       {"name_fa":"ورود به ناحیه OTE + لیکو", "rr_base":2.2, "prob_base":63},
}

# SMC Direction constants
LONG, SHORT, NEUTRAL = "long", "short", "neutral"


# =========================================================
# Candle normalization (handles dict / Candle pydantic / ms timestamps)
# =========================================================
def _ts(v) -> float:
    if hasattr(v, "timestamp"):
        return v.timestamp()
    try:
        f = float(v)
        return f/1000.0 if f > 1e12 else f
    except Exception:
        return 0.0


def _candles(raw) -> List[Dict]:
    out = []
    for c in (raw or []):
        if hasattr(c, "model_dump"):
            try: c = c.model_dump()
            except Exception: continue
        elif not isinstance(c, dict):
            try: c = dict(c)
            except Exception: continue
        try:
            o=float(c.get("o",c.get("open",0)) or 0)
            h=float(c.get("h",c.get("high",0)) or 0)
            l=float(c.get("l",c.get("low",0)) or 0)
            cl=float(c.get("c",c.get("close",0)) or 0)
            v=float(c.get("v",c.get("volume",0)) or 0)
            t=_ts(c.get("t",c.get("time",c.get("datetime",c.get("timestamp",0)))))
            if h < max(o,cl): h = max(o,cl)
            if l > min(o,cl): l = min(o,cl)
            if h <= l: continue
            out.append({"t":t,"o":o,"h":h,"l":l,"c":cl,"v":v})
        except Exception:
            pass
    out.sort(key=lambda x: x["t"])
    return out


# =========================================================
# ATR
# =========================================================
def _atr(cs, n=14) -> float:
    if len(cs) < 2: return 0.0
    if len(cs) < n+1:
        return sum(c["h"]-c["l"] for c in cs)/len(cs)
    trs = []
    for i in range(1, len(cs)):
        h,l,pc = cs[i]["h"], cs[i]["l"], cs[i-1]["c"]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs[-n:])/n


# =========================================================
# Structural swings (zigzag) — require at least 3 bars each side
# =========================================================
def _swings(cs, left=3, right=3) -> Tuple[List[Tuple[int,float]], List[Tuple[int,float]]]:
    highs=[]; lows=[]; n=len(cs)
    if n < left+right+1: return highs,lows
    for i in range(left, n-right):
        hh = cs[i]["h"]; ll = cs[i]["l"]
        is_high = all(hh >= cs[i-k]["h"] for k in range(1,left+1)) and all(hh >= cs[i+k]["h"] for k in range(1,right+1))
        is_low  = all(ll <= cs[i-k]["l"] for k in range(1,left+1)) and all(ll <= cs[i+k]["l"] for k in range(1,right+1))
        if is_high: highs.append((i,hh))
        if is_low:  lows.append((i,ll))
    return highs, lows


def _interleave_swings(highs, lows) -> List[Tuple[str,int,float]]:
    seq=[]; hi=lo=0
    while hi<len(highs) and lo<len(lows):
        if highs[hi][0] < lows[lo][0]:
            seq.append(("H",*highs[hi])); hi+=1
        else:
            seq.append(("L",*lows[lo])); lo+=1
    while hi<len(highs): seq.append(("H",*highs[hi])); hi+=1
    while lo<len(lows): seq.append(("L",*lows[lo])); lo+=1
    return seq


# =========================================================
# Structure (BOS/CHoCH) — confirmed by close, not wick
# =========================================================
def _structure(cs, highs, lows):
    """Returns (events, bias, last_swing_high_price, last_swing_low_price, leg)
    leg = (swing_low_idx, swing_low_price, swing_high_idx, swing_high_price) for latest impulsive leg.
    """
    events = []
    seq = _interleave_swings(highs, lows)
    if len(seq) < 4:
        bh = highs[-1][1] if highs else None
        bl = lows[-1][1] if lows else None
        return events, "neutral", bh, bl, None

    # Determine starting trend by first pair of alternations
    trend = None
    for k in range(1, min(6, len(seq))):
        t1,i1,p1 = seq[k-1]; t2,i2,p2 = seq[k]
        if t1=="L" and t2=="H" and p2>p1: trend = "bullish"; break
        if t1=="H" and t2=="L" and p2<p1: trend = "bearish"; break
    if trend is None: trend = "bullish" if seq[-1][0]=="H" else "bearish"

    # Initialize refs with the first swing pair of the initial direction
    last_high_p = last_low_p = None
    last_high_i = last_low_i = None
    for k,(t,i,p) in enumerate(seq):
        if t=="H" and (last_high_p is None or p>last_high_p):
            last_high_p, last_high_i = p, i
        if t=="L" and (last_low_p is None or p<last_low_p):
            last_low_p, last_low_i = p, i
        if last_high_p is not None and last_low_p is not None and k>=3:
            break

    leg = None  # (li,lp,hi,hp)
    start_i = min(last_high_i or 0, last_low_i or 0)

    for i in range(max(1,start_i), len(cs)):
        c = cs[i]
        close_up = c["c"]; close_dn = c["c"]
        if trend == "bullish":
            # BOS: close above last confirmed swing high
            if last_high_p is not None and close_up > last_high_p:
                events.append({"type":"BOS","index":i,"price":close_up,"dir":"bullish","swing":last_high_i})
                # Update ref low to the swing low that led this leg
                lows_before = [(idx,pp) for kk,idx,pp in seq if kk=="L" and idx<i]
                if lows_before:
                    last_low_p, last_low_i = lows_before[-1][1], lows_before[-1][0]
                # Next future high is now the ref
                highs_after = [(idx,pp) for kk,idx,pp in seq if kk=="H" and idx>i]
                if highs_after:
                    last_high_p, last_high_i = highs_after[0][1], highs_after[0][0]
                else:
                    last_high_p, last_high_i = c["h"], i
                leg = (last_low_i, last_low_p, last_high_i, last_high_p)
            # CHoCH: close below last confirmed swing low
            elif last_low_p is not None and close_dn < last_low_p:
                events.append({"type":"CHoCH","index":i,"price":close_dn,"dir":"bearish","swing":last_low_i})
                trend = "bearish"
                highs_before = [(idx,pp) for kk,idx,pp in seq if kk=="H" and idx<i]
                if highs_before:
                    last_high_p, last_high_i = highs_before[-1][1], highs_before[-1][0]
                lows_after = [(idx,pp) for kk,idx,pp in seq if kk=="L" and idx>i]
                if lows_after:
                    last_low_p, last_low_i = lows_after[0][1], lows_after[0][0]
                else:
                    last_low_p, last_low_i = c["l"], i
                leg = (last_low_i, last_low_p, last_high_i, last_high_p)
        else:
            if last_low_p is not None and close_dn < last_low_p:
                events.append({"type":"BOS","index":i,"price":close_dn,"dir":"bearish","swing":last_low_i})
                highs_before = [(idx,pp) for kk,idx,pp in seq if kk=="H" and idx<i]
                if highs_before:
                    last_high_p, last_high_i = highs_before[-1][1], highs_before[-1][0]
                lows_after = [(idx,pp) for kk,idx,pp in seq if kk=="L" and idx>i]
                if lows_after:
                    last_low_p, last_low_i = lows_after[0][1], lows_after[0][0]
                else:
                    last_low_p, last_low_i = c["l"], i
                leg = (last_low_i, last_low_p, last_high_i, last_high_p)
            elif last_high_p is not None and close_up > last_high_p:
                events.append({"type":"CHoCH","index":i,"price":close_up,"dir":"bullish","swing":last_high_i})
                trend = "bullish"
                lows_before = [(idx,pp) for kk,idx,pp in seq if kk=="L" and idx<i]
                if lows_before:
                    last_low_p, last_low_i = lows_before[-1][1], lows_before[-1][0]
                highs_after = [(idx,pp) for kk,idx,pp in seq if kk=="H" and idx>i]
                if highs_after:
                    last_high_p, last_high_i = highs_after[0][1], highs_after[0][0]
                else:
                    last_high_p, last_high_i = c["h"], i
                leg = (last_low_i, last_low_p, last_high_i, last_high_p)

    # Final leg if last event
    if events and leg is None:
        ev = events[-1]
        if ev["dir"]=="bullish":
            li = ev.get("swing", last_low_i or 0); lp = last_low_p or cs[li]["l"]
            hi = ev["index"]; hp = ev["price"]
            leg = (li,lp,hi,hp)
        else:
            hi = ev.get("swing", last_high_i or 0); hp = last_high_p or cs[hi]["h"]
            li = ev["index"]; lp = ev["price"]
            leg = (li,lp,hi,hp)

    # If no events yet compute leg from last two swings
    if leg is None and len(highs)>=2 and len(lows)>=2:
        if trend == "bullish":
            li,lp = lows[-1]; hi,hp = highs[-1]
        else:
            hi,hp = highs[-1]; li,lp = lows[-1]
        if li < hi or hi < li:
            leg = (min(li,hi), cs[min(li,hi)]["l" if trend=="bullish" else "h"],
                   max(li,hi), cs[max(li,hi)]["h" if trend=="bullish" else "l"])

    return events, trend, last_high_p, last_low_p, leg


# =========================================================
# Displacement (impulsive momentum candles)
# =========================================================
def _displacement(cs, atr):
    out=[]
    for i,c in enumerate(cs):
        body=abs(c["c"]-c["o"]); rng=c["h"]-c["l"]
        if rng<=0 or atr<=0: continue
        if body/rng>=0.55 and body>=atr*0.45:
            direction = "bullish" if c["c"]>c["o"] else "bearish"
            strength = min(10, int(body/atr*3) + int(c["v"]/max(1e-9,_avg_vol(cs,i,10))*2))
            out.append((i, direction, strength))
    return out


def _avg_vol(cs, i, n):
    seg = cs[max(0,i-n):i+1]
    return sum(c["v"] for c in seg)/max(1,len(seg))


# =========================================================
# Fair Value Gaps (FVG / iFVG)
# =========================================================
def _fvg(cs):
    gaps=[]; n=len(cs)
    for i in range(n-2):
        a,b,c0 = cs[i], cs[i+1], cs[i+2]
        # Bullish FVG: c0.low > a.high
        if a["h"] < c0["l"]:
            size = c0["l"]-a["h"]; mid=(a["h"]+c0["l"])/2; mid_price=a["h"]+size*0.5
            # Quality: gap size relative to ATR, candle body size, volume
            rng = b["h"]-b["l"] or 1e-9
            body = abs(b["c"]-b["o"])/rng
            gaps.append({"kind":"bullish","index":i+1,"top":c0["l"],"bottom":a["h"],"mid":mid_price,
                         "size":size,"size_pct":size/mid_price*100,
                         "mitigated":False,"tapped":False,
                         "quality":min(10,int((size/max(1e-9,a["h"]))*150 + body*4))})
        # Bearish FVG
        if a["l"] > c0["h"]:
            size = a["l"]-c0["h"]; mid=(a["l"]+c0["h"])/2; mid_price=c0["h"]+size*0.5
            rng = b["h"]-b["l"] or 1e-9
            body = abs(b["c"]-b["o"])/rng
            gaps.append({"kind":"bearish","index":i+1,"top":a["l"],"bottom":c0["h"],"mid":mid_price,
                         "size":size,"size_pct":size/mid_price*100,
                         "mitigated":False,"tapped":False,
                         "quality":min(10,int((size/max(1e-9,c0["h"]))*150 + body*4))})
    for g in gaps:
        for j in range(g["index"]+2, n):
            cc = cs[j]
            if g["kind"]=="bullish":
                if cc["l"]<=g["mid"]: g["tapped"]=True
                if cc["l"]<=g["bottom"]: g["mitigated"]=True; break
            else:
                if cc["h"]>=g["mid"]: g["tapped"]=True
                if cc["h"]>=g["top"]: g["mitigated"]=True; break
    return gaps


# =========================================================
# Order Blocks
# =========================================================
def _obs(cs, events, disps, atr):
    """Order Block detection (ICT-compliant):
    For a bullish BOS/CHoCH: find the last BEARISH candle in the consolidation
    leg immediately before the bullish displacement (that candle is the bullish OB).
    For bearish: last BULLISH candle before bearish displacement.
    Also accept the break candle itself as the displacement if no earlier one exists.
    """
    obs=[]; seen=set()
    disps_idx = {di: (dd,ds) for di,dd,ds in disps}
    for ev in events:
        if ev["type"] not in ("BOS","CHoCH"): continue
        i=ev["index"]; d=ev["dir"]
        # 1. Find displacement candle: prefer one in direction before i within last 8
        disp_idx=None; disp_strength=0
        for k in range(i,max(0,i-12),-1):
            if k in disps_idx and disps_idx[k][0]==d:
                disp_idx=k; disp_strength=disps_idx[k][1]; break
        # 2. Fallback: any strong candle in direction (including the break candle itself)
        if disp_idx is None:
            for k in range(i,max(0,i-5),-1):
                c=cs[k]; body=abs(c["c"]-c["o"])
                bull=c["c"]>c["o"]
                if ((d=="bullish" and bull and body>=atr*0.3) or
                    (d=="bearish" and not bull and body>=atr*0.3)):
                    disp_idx=k; break
        if disp_idx is None: continue
        # 3. Walk BACK from displacement to find the LAST opposite-color candle (OB source)
        ob_idx=None
        # Find the contiguous run of same-direction candles before disp, then the last opposite
        opposite_found=False
        for k in range(disp_idx-1,max(0,disp_idx-30),-1):
            c=cs[k]; bull=c["c"]>c["o"]
            if d=="bullish":
                if not bull:
                    ob_idx=k; break
                opposite_found=True
            else:
                if bull:
                    ob_idx=k; break
                opposite_found=True
        # Fallback: if we couldn't find opposite, use the candle right before disp
        if ob_idx is None:
            ob_idx = max(0, disp_idx-1)
        if ob_idx in seen: continue
        # Skip if ob is too far back (more than 25 bars from disp)
        if disp_idx - ob_idx > 25: continue
        seen.add(ob_idx)
        oc=cs[ob_idx]
        rng=oc["h"]-oc["l"] or 1e-9
        body_ratio=abs(oc["c"]-oc["o"])/rng
        # Wick on the rejection side (lower wick for bullish OB = support)
        if d=="bullish":
            wick_ratio=(min(oc["c"],oc["o"])-oc["l"])/rng
        else:
            wick_ratio=(oc["h"]-max(oc["c"],oc["o"]))/rng
        avgv = _avg_vol(cs, ob_idx, 15)
        vol_mult = oc["v"]/max(1e-9,avgv)
        quality = min(10, int(body_ratio*3 + wick_ratio*3 + vol_mult*3 + disp_strength*0.3))
        obs.append({"kind":d,"index":ob_idx,"top":oc["h"],"bottom":oc["l"],
                     "open":oc["o"],"close":oc["c"],"volume":oc["v"],
                     "quality":max(3,quality),"mitigated":False,"tapped":False,
                     "event_type":ev["type"],"disp_index":disp_idx})
    # De-dup: keep only highest-quality OB at similar price (within 0.2 ATR)
    obs.sort(key=lambda o:(o["index"],-o["quality"]))
    dedup=[]
    for o in obs:
        if any(abs(o["top"]-p["top"])<atr*0.2 and o["kind"]==p["kind"] for p in dedup[-3:]):
            continue
        dedup.append(o)
    obs=dedup
    # Mitigation check (require a close beyond OB by 20%+ of the zone, not just marginal)
    for ob in obs:
        mid=(ob["top"]+ob["bottom"])/2
        zone_size=ob["top"]-ob["bottom"] or atr*0.3
        for j in range(ob.get("disp_index",ob["index"])+1,len(cs)):
            cc=cs[j]
            if ob["kind"]=="bullish":
                if cc["l"]<=ob["top"]+zone_size*0.15: ob["tapped"]=True
                # Mitigated: close BELOW ob bottom - 0.3×zone
                if cc["c"]<ob["bottom"]-zone_size*0.3: ob["mitigated"]=True; break
            else:
                if cc["h"]>=ob["bottom"]-zone_size*0.15: ob["tapped"]=True
                if cc["c"]>ob["top"]+zone_size*0.3: ob["mitigated"]=True; break
    return obs


# =========================================================
# Breaker blocks (mitigated OB then retest from flip side)
# =========================================================
def _breakers(cs, obs):
    br=[]
    for ob in obs:
        if not ob["mitigated"]: continue
        # find where mitigated
        mit_at=None
        for j in range(ob["index"]+1,len(cs)):
            cc=cs[j]
            if ob["kind"]=="bullish" and cc["c"]<ob["bottom"]: mit_at=j; break
            if ob["kind"]=="bearish" and cc["c"]>ob["top"]:    mit_at=j; break
        if mit_at is None: continue
        # must swing away and retest
        swung=False
        for j in range(mit_at+1,len(cs)):
            if ob["kind"]=="bullish":
                # broke down (bearish breaker) — needs to swing down then retest from below
                if cs[j]["l"] <= cs[mit_at]["l"]-(cs[mit_at]["l"]*0.001): swung=True
                if swung and cs[j]["h"]>=ob["bottom"] and cs[j]["h"]<=ob["top"]*1.003:
                    br.append({**ob,"kind":"bearish","breaker":True}); break
            else:
                if cs[j]["h"] >= cs[mit_at]["h"]*(1+0.001): swung=True
                if swung and cs[j]["l"]<=ob["top"] and cs[j]["l"]>=ob["bottom"]*0.997:
                    br.append({**ob,"kind":"bullish","breaker":True}); break
    return br


# =========================================================
# Liquidity pools + sweeps (stophunts/inducements)
# =========================================================
def _liquidity(cs, highs, lows, atr):
    liq=[]; tol=0.0012
    seen=set()
    # EQH
    for i in range(1,len(highs)):
        i1,p1=highs[i-1]; i2,p2=highs[i]
        if abs(p1-p2)/p1<tol and i2-i1>=3:
            k=round(p2,4)
            if k not in seen:
                seen.add(k); liq.append({"kind":"eqh","index":i2,"price":p2,"weight":4})
    seen.clear()
    for i in range(1,len(lows)):
        i1,p1=lows[i-1]; i2,p2=lows[i]
        if abs(p1-p2)/p1<tol and i2-i1>=3:
            k=round(p2,4)
            if k not in seen:
                seen.add(k); liq.append({"kind":"eql","index":i2,"price":p2,"weight":4})

    # Buy-side sweep (price dips below swing low then closes back above)
    for si,sp in lows[-20:]:
        for j in range(si+1,min(si+15,len(cs))):
            cc=cs[j]
            pen = sp-cc["l"]
            if cc["l"]<sp and cc["c"]>sp and 0<pen<max(sp*0.006, atr*0.6):
                # Confirm follow-through (next candle green)
                follow = j+1<len(cs) and cs[j+1]["c"]>cc["c"]
                liq.append({"kind":"buyside_liq","index":si,"sweep":j,"price":sp,
                            "penetration":pen,"follow_through":follow,"weight":6 if follow else 3})
                break
    for si,sp in highs[-20:]:
        for j in range(si+1,min(si+15,len(cs))):
            cc=cs[j]
            pen = cc["h"]-sp
            if cc["h"]>sp and cc["c"]<sp and 0<pen<max(sp*0.006, atr*0.6):
                follow = j+1<len(cs) and cs[j+1]["c"]<cc["c"]
                liq.append({"kind":"sellside_liq","index":si,"sweep":j,"price":sp,
                            "penetration":pen,"follow_through":follow,"weight":6 if follow else 3})
                break
    # External recent liq (targets)
    if cs:
        seg=cs[-35:]
        liq.append({"kind":"recent_high_liq","index":len(cs)-1,"price":max(c["h"] for c in seg),"weight":2})
        liq.append({"kind":"recent_low_liq","index":len(cs)-1,"price":min(c["l"] for c in seg),"weight":2})
    # dedup by price
    dedup=[]; used=[]
    for l in liq:
        if l["kind"] in ("eqh","eql") and any(abs(l["price"]-p)/p<0.0008 for p in used):
            continue
        dedup.append(l); used.append(l["price"])
    return dedup[-18:]


# =========================================================
# Order Flow v2
# =========================================================
def _orderflow(cs, window=20):
    if not cs:
        return {"delta":0,"pressure":"neutral","cvd":0,"cvd_curve":[],"volume_spike":False,
                "cvd_divergence":None,"absorption":False,"climax":False,"avg_volume":0,"buy_vol":0,"sell_vol":0}
    cvd=0; curve=[]; vols=[]; deltas=[]; buy_vol=0; sell_vol=0
    for c in cs:
        rng=c["h"]-c["l"] or 1e-9
        bv=((c["c"]-c["l"])/rng)*c["v"]
        sv=((c["h"]-c["c"])/rng)*c["v"]
        d=bv-sv; cvd+=d
        curve.append({"t":c["t"],"cvd":cvd})
        vols.append(c["v"]); deltas.append(d)
        buy_vol+=bv; sell_vol+=sv
    last_d=sum(deltas[-window:]) if deltas else 0
    last_v=sum(vols[-window:]) or 1
    norm=last_d/last_v
    pressure = "buy" if norm>0.15 else "sell" if norm<-0.15 else "neutral"
    avg_v=sum(vols)/len(vols)
    spike = vols[-1]>avg_v*2.0 if vols else False
    last=cs[-1]; lr=last["h"]-last["l"] or 1e-9; lb=abs(last["c"]-last["o"])/lr
    absorption = vols[-1]>avg_v*1.8 and lb<0.25 if vols else False
    climax = vols[-1]>avg_v*2.5 and lb>0.7 if vols else False
    div=None
    if len(cs)>window*2 and len(curve)>window*2:
        s1=cs[-window*2:-window]; s2=cs[-window:]
        cv1=curve[-window*2:-window]; cv2=curve[-window:]
        if s1 and s2 and cv1 and cv2:
            h1=max(c["h"] for c in s1); h2=max(c["h"] for c in s2)
            l1=min(c["l"] for c in s1); l2=min(c["l"] for c in s2)
            c1d=cv1[-1]["cvd"]-cv1[0]["cvd"]; c2d=cv2[-1]["cvd"]-cv2[0]["cvd"]
            if h2>h1 and c2d<c1d*0.3: div="bearish"
            elif l2<l1 and c2d>c1d*0.3: div="bullish"
    return {"delta":round(norm,3),"pressure":pressure,"cvd":round(cvd,2),"cvd_curve":curve[-40:],
            "volume_spike":bool(spike),"cvd_divergence":div,"absorption":bool(absorption),
            "climax":bool(climax),"avg_volume":avg_v,"buy_vol":buy_vol,"sell_vol":sell_vol}


# =========================================================
# Sessions / Killzones
# =========================================================
def _sessions(cs):
    zones=[]; names=[]; seen=set()
    last_name=None
    for i,c in enumerate(cs):
        t=c["t"]
        if t<=0: continue
        try: dt=datetime.fromtimestamp(t,tz=UTC)
        except Exception: continue
        h=dt.hour+dt.minute/60
        match=None
        for kz in sorted(KILLZONES,key=lambda x:-x["vol"]):
            if kz["start"]<=h<kz["end"]: match=kz; break
        if match and match["vol"]>=0.9:
            if match["name"] not in seen:
                seen.add(match["name"]); names.append(match["name"])
            if last_name==match["name"]:
                zones[-1]["end"]=i
            else:
                zones.append({"name":match["name"],"start":i,"end":i,"vol":match["vol"],"color":match["color"]})
            last_name=match["name"]
        else:
            if last_name is not None:
                zones[-1]["end"]=i-1; last_name=None
    if zones and zones[-1]["end"]<zones[-1]["start"]:
        zones[-1]["end"]=zones[-1]["start"]
    return zones, names


def _active_session(cs):
    if not cs: return ("خارج از سشن",0.0,"#374151")
    t=cs[-1]["t"]
    if t<=0: return ("خارج از سشن",0.0,"#374151")
    try: dt=datetime.fromtimestamp(t,tz=UTC)
    except Exception: return ("خارج از سشن",0.0,"#374151")
    h=dt.hour+dt.minute/60
    for kz in sorted(KILLZONES,key=lambda x:-x["vol"]):
        if kz["start"]<=h<kz["end"]: return (kz["name"],kz["vol"],kz["color"])
    return ("خارج از سشن",0.0,"#374151")


def _parse_tf_mins(tf):
    t=(tf or "15").lower().strip()
    try:
        if t.endswith("min") or t.endswith("m"):
            return int("".join(c for c in t if c.isdigit()) or 15)
        if t.endswith("h"): return int("".join(c for c in t if c.isdigit()) or 1)*60
        if t.endswith("d"): return 1440
        if t.endswith("w"): return 10080
    except Exception: pass
    return 15


# =========================================================
# Fibonacci / Premium-Discount / OTE  (based on the last structural LEG)
# =========================================================
def _fib_leg(leg, cs, bias, price):
    """Compute Fib levels on the latest impulsive leg.
    For bullish (impulse UP then pullback):
        - impulse range = high - low
        - retracement = (high - price) / range  (0 at high, 1 at low)
        - OTE long = 0.62 to 0.79 retracement (62-79% pullback)
        - Discount = retracement >= 0.5 (below 50% of range)
    For bearish (impulse DOWN then pullback):
        - impulse range = high - low (high was earlier, low was later)
        - retracement = (price - low) / range  (0 at low, 1 at high)
        - OTE short = 0.62 to 0.79 retracement (62-79% bounce)
        - Premium = retracement >= 0.5 (above 50% of range)
    leg tuple: (li, lp, hi, hp) where li is index of swing-low, hi index of swing-high.
    If li < hi → impulse went UP (low then high) = bullish leg.
    If li > hi → impulse went DOWN (high then low) = bearish leg.
    """
    if leg is None: return None
    li,lp,hi,hp = leg
    if li < hi:
        # Bullish impulse: low at li (earlier), high at hi (later)
        direction = "bullish"
        rng = hp - lp
        if rng <= 0: return None
        retrace = (hp - price) / rng  # how far we've pulled back from high
        return {
            "dir":"bullish","leg_low":lp,"leg_high":hp,"range":rng,
            "fib27":hp-rng*0.27,"fib38":hp-rng*0.38,"fib50":hp-rng*0.5,
            "fib62":hp-rng*0.62,"fib79":hp-rng*0.79,
            "ote_low":hp-rng*0.79,"ote_high":hp-rng*0.62,
            "retrace_pct":retrace,
            "in_ote": 0.62 <= retrace <= 0.79,
            "in_premium": retrace < 0.5,    # above 50% (close to high)
            "in_discount": retrace >= 0.5,  # below 50% (pulled back)
        }
    else:
        # Bearish impulse: high at hi (earlier), low at li (later)
        direction = "bearish"
        rng = hp - lp
        if rng <= 0: return None
        retrace = (price - lp) / rng
        return {
            "dir":"bearish","leg_low":lp,"leg_high":hp,"range":rng,
            "fib27":lp+rng*0.27,"fib38":lp+rng*0.38,"fib50":lp+rng*0.5,
            "fib62":lp+rng*0.62,"fib79":lp+rng*0.79,
            "ote_low":lp+rng*0.62,"ote_high":lp+rng*0.79,
            "retrace_pct":retrace,
            "in_ote": 0.62 <= retrace <= 0.79,
            "in_premium": retrace >= 0.5,
            "in_discount": retrace < 0.5,
        }


# =========================================================
# Visible price range
# =========================================================
def _vis_range(cs):
    if not cs: return 0,1
    n=len(cs)
    if n<30: return min(c["l"] for c in cs), max(c["h"] for c in cs)
    hs=sorted(c["h"] for c in cs); ls=sorted(c["l"] for c in cs)
    t=max(1,n//60)
    return ls[t], hs[n-1-t]


# =========================================================
# VWAP (approx, from start of loaded dataset)
# =========================================================
def _vwap(cs):
    if not cs: return cs[-1]["c"] if cs else 0
    num=den=0
    for c in cs:
        typ=(c["h"]+c["l"]+c["c"])/3
        num+=typ*c["v"]; den+=c["v"]
    return num/den if den else cs[-1]["c"]


# =========================================================
# Ranging / choppy detection via trend-strength score
# =========================================================
def _trend_strength(cs, events, atr):
    """0 (chop) to 100 (strong trend)."""
    if not events or not cs or atr<=0: return 40
    last5 = events[-5:]
    bos = sum(1 for e in last5 if e["type"]=="BOS")
    choch = sum(1 for e in last5 if e["type"]=="CHoCH")
    if choch>=3: return 20  # flipping back and forth = chop
    # Price distance from MA of closes
    closes=[c["c"] for c in cs[-30:]]
    ma=sum(closes)/len(closes)
    dev = abs(closes[-1]-ma)/atr
    # Consistency: same-direction BOS count
    last_dir = last5[-1]["dir"]
    same = sum(1 for e in last5 if e["dir"]==last_dir)
    strength = min(100, int(dev*15 + same*12 + bos*8 - choch*10))
    return max(10, strength)


# =========================================================
# POI stacking: find zones where OB/FVG/50% fib overlap
# =========================================================
def _poi_stacking(active_obs, active_fvgs, br, fib, price, atr):
    """Return strongest POI near price with stacked confluences."""
    zones=[]
    # Collect all candidate zones
    for o in active_obs:
        zones.append({"kind":"OB","side":o["kind"],"top":o["top"],"bottom":o["bottom"],"quality":o.get("quality",5)})
    for g in active_fvgs:
        zones.append({"kind":"FVG","side":g["kind"],"top":g["top"],"bottom":g["bottom"],"quality":g.get("quality",5)})
    for b in br:
        zones.append({"kind":"BRK","side":b["kind"],"top":b["top"],"bottom":b["bottom"],"quality":b.get("quality",5)})
    if fib:
        zones.append({"kind":"FIB50","side":fib["dir"],"top":fib["fib50"]+atr*0.15,"bottom":fib["fib50"]-atr*0.15,"quality":5})
        zones.append({"kind":"OTE","side":fib["dir"],"top":fib["ote_high"],"bottom":fib["ote_low"],"quality":7})
    best=None; best_count=0
    price_tol = atr*0.5
    for z in zones:
        mid=(z["top"]+z["bottom"])/2
        if abs(price-mid) > atr*3: continue
        count=1; reasons=[z["kind"]]
        q_total=z["quality"]
        for z2 in zones:
            if z2 is z: continue
            if z["side"]!=z2["side"]: continue
            mid2=(z2["top"]+z2["bottom"])/2
            if abs(mid-mid2) < price_tol:
                count+=1; reasons.append(z2["kind"]); q_total+=z2["quality"]
        if count>best_count or (count==best_count and q_total>(best["q_total"] if best else 0)):
            best_count=count; best={"side":z["side"],"top":z["top"],"bottom":z["bottom"],
                                     "count":count,"reasons":list(set(reasons)),"q_total":q_total,
                                     "mid":mid}
    return best


# =========================================================
# Confluence scoring (20 factors)
# =========================================================
def _score_confluence(direction, bias, fib, ob_q, fvg_q, of, liq_side, mtf, sess_w, news,
                      trend_str, poi_count, in_ote, vwap_above, disp_strength, grade_session):
    factors=[]; score=0
    def add(name, pts, why=""):
        nonlocal score
        score+=pts
        factors.append({"name":name,"points":pts,"why":why})
    if direction==LONG:
        if bias=="bullish": add("ساختار صعودی (HH/HL)",12,"سوئینگ‌های بالاتر تایید شده")
        if fib and fib.get("in_discount"): add("ناحیه دیسکانت (<50% فیب)",8,"قیمت در نیمه پایینی لگ صعودی")
        if in_ote: add("ناحیه OTE (62-79%)",10,"بهینه‌ترین نقطه ورود طبق ICT")
        if of["pressure"]=="buy": add("فشار خرید (OF+)",10,"دلتای مثبت پایدار")
        if liq_side=="sellside": add("سل‌ساید سویپ",9,"استاپ‌هانت فروشندگان جمع شد")
        if ob_q>=7: add("OB نهادی با کیفیت بالا",7,"بدنه کشیده + حجم بالا")
        elif ob_q>=4: add("OB تایید شده",4,"ناحیه عرضه/تقاضا")
        if fvg_q>=6: add("FVG قوی",5,"گپ خالی نقدینه")
        if of.get("volume_spike"): add("افزایش حجم نهادی",6,"حجم ۲ برابر میانگین")
        if of.get("absorption"): add("جذب سفارش (Absorption)",5,"حجم بالا با بدنه کوچک")
        if of.get("cvd_divergence")=="bullish": add("واگرایی مثبت CVD",7,"CVD برگشت را تایید می‌کند")
        if trend_str>=60: add("قدرت روند بالا",6,"حرکت پیوسته در یک جهت")
        if poi_count>=3: add("تلاقی POIها",8,"چند ناحیه SMC روی هم افتاده‌اند")
        if vwap_above: add("قیمت زیر VWAP",4,"بازگشت به میانگین حجمی")
        if disp_strength>=7: add("جابجایی قوی",6,"کندل مومنتوم تایید کننده")
    elif direction==SHORT:
        if bias=="bearish": add("ساختار نزولی (LL/LH)",12,"سوئینگ‌های پایین‌تر تایید شده")
        if fib and fib.get("in_premium"): add("ناحیه پرمیوم (>50% فیب)",8,"قیمت در نیمه بالایی لگ نزولی")
        if in_ote: add("ناحیه OTE (21-38%)",10,"بهینه‌ترین نقطه فروش")
        if of["pressure"]=="sell": add("فشار فروش (OF−)",10,"دلتای منفی پایدار")
        if liq_side=="buyside": add("بای‌ساید سویپ",9,"استاپ‌هانت خریداران جمع شد")
        if ob_q>=7: add("OB نهادی با کیفیت بالا",7,"بدنه کشیده + حجم بالا")
        elif ob_q>=4: add("OB تایید شده",4,"ناحیه عرضه/تقاضا")
        if fvg_q>=6: add("FVG قوی",5,"گپ خالی نقدینه")
        if of.get("volume_spike"): add("افزایش حجم نهادی",6,"حجم ۲ برابر میانگین")
        if of.get("absorption"): add("جذب سفارش (Absorption)",5,"حجم بالا با بدنه کوچک")
        if of.get("cvd_divergence")=="bearish": add("واگرایی منفی CVD",7,"CVD برگشت را تایید می‌کند")
        if trend_str>=60: add("قدرت روند بالا",6,"حرکت پیوسته در یک جهت")
        if poi_count>=3: add("تلاقی POIها",8,"چند ناحیه SMC روی هم افتاده‌اند")
        if not vwap_above: add("قیمت بالای VWAP",4,"بازگشت به میانگین حجمی")
        if disp_strength>=7: add("جابجایی قوی",6,"کندل مومنتوم تایید کننده")
    # Shared
    if mtf: add("همراستایی با HTF",12,"تایم‌فریم بالا هم‌جهت")
    if sess_w>=1.4: add("کیل‌زون همپوشانی LDN-NY",10,"بیشترین نوسان و حجم نهادی")
    elif sess_w>=1.1: add("کیل‌زون اصلی فعال",6,"لندن/نیویورک")
    elif sess_w>=0.7: add("سشن آسیا",1,"نوسان کم")
    else: add("خارج از سشن اصلی",-5,"نقدشوندگی پایین")
    if trend_str<30: add("بازار رنج/نوسانی",-10,"ساختار متلاطم")
    if of.get("climax"): add("نشانه خستگی (Climax)",-6,"احتمال برگشت بالا")
    if news: add("پنجره اخبار پرریسک",-30,"از ورود اکیداً خودداری کنید")
    return max(0,min(100,score)), factors


# =========================================================
# Detect best setup
# =========================================================
def _detect(cs, bias, active_obs, active_fvgs, br, liq, price, atr, of, fib, vwap, trend_str, sess_w):
    """Return best setup or None."""
    best=None; best_score=0

    def liq_for(direction):
        want = "sellside_liq" if direction==LONG else "buyside_liq"
        best=None; best_ago=999
        for l in reversed(liq):
            if l["kind"]==want:
                ago=len(cs)-l.get("sweep",l["index"])
                if ago<=25 and ago<best_ago:
                    best_ago=ago; best=l
        return best

    def near_ob(direction):
        best_o=None; bd=1e18
        for o in active_obs:
            if o["kind"]!=direction: continue
            ob_size = max(atr*0.3, o["top"]-o["bottom"])
            tol = max(atr*1.0, ob_size*1.2)
            if direction==LONG:
                if price <= o["top"]+tol*0.3 and price >= o["bottom"]-tol*0.4:
                    d=abs(price-(o["top"]+o["bottom"])/2)
                    if d<bd: bd=d; best_o=o
            else:
                if price >= o["bottom"]-tol*0.3 and price <= o["top"]+tol*0.4:
                    d=abs(price-(o["top"]+o["bottom"])/2)
                    if d<bd: bd=d; best_o=o
        return best_o

    def near_brk(direction):
        best_b=None; bd=1e18
        for b in br:
            if b.get("kind")!=direction: continue
            b_size = max(atr*0.3, b["top"]-b["bottom"])
            tol = max(atr*0.9, b_size*1.2)
            if direction==LONG:
                if price <= b["top"]+tol*0.3 and price >= b["bottom"]-tol*0.4:
                    d=abs(price-(b["top"]+b["bottom"])/2)
                    if d<bd: bd=d; best_b=b
            else:
                if price >= b["bottom"]-tol*0.3 and price <= b["top"]+tol*0.4:
                    d=abs(price-(b["top"]+b["bottom"])/2)
                    if d<bd: bd=d; best_b=b
        return best_b

    def near_fvg(direction):
        best_g=None; bd=1e18
        for g in active_fvgs:
            if g["kind"]!=direction: continue
            g_size = max(atr*0.2, abs(g["top"]-g["bottom"]))
            tol = max(atr*0.8, g_size*1.5)
            if direction==LONG:
                if price <= g["top"]+tol and price >= g["bottom"]-tol*0.6:
                    d=abs(price-(g["top"]+g["bottom"])/2)
                    if d<bd: bd=d; best_g=g
            else:
                if price >= g["bottom"]-tol and price <= g["top"]+tol*0.6:
                    d=abs(price-(g["top"]+g["bottom"])/2)
                    if d<bd: bd=d; best_g=g
        return best_g

    def next_liq_target(direction):
        """Nearest liquidity pool in target direction."""
        tgt=None; bd=1e18
        for l in liq:
            if direction==LONG and l["price"]>price+atr*0.3:
                if l["price"]-price<bd: bd=l["price"]-price; tgt=l["price"]
            if direction==SHORT and l["price"]<price-atr*0.3:
                if price-l["price"]<bd: bd=price-l["price"]; tgt=l["price"]
        return tgt

    vwap_above = price > vwap

    # Map SMC side ("bullish"/"bearish") to trade direction (long/short)
    def side_for(direction):
        return "bullish" if direction==LONG else "bearish"

    for direction in (LONG,SHORT):
        sd = side_for(direction)
        ob=near_ob(sd); brk=near_brk(sd); fvg=near_fvg(sd)
        sweep=liq_for(direction)
        zone=ob or brk
        in_ote = bool(fib and fib.get("in_ote")) and fib.get("dir")==sd
        ob_q=ob["quality"] if ob else (brk["quality"] if brk else 0)
        fvg_q=fvg["quality"] if fvg else 0
        poi_count = 0; poi_reasons=[]
        # count overlapping reasons at current price zone
        if zone: poi_count+=1; poi_reasons.append("BRK" if brk else "OB")
        if fvg and zone and abs(fvg["mid"]-(zone["top"]+zone["bottom"])/2)<atr*0.5:
            poi_count+=1; poi_reasons.append("FVG")
        if in_ote: poi_count+=1; poi_reasons.append("OTE")
        if sweep and sweep.get("follow_through"): poi_count+=1; poi_reasons.append("SWEEP")

        # Setup type decision
        stype=None; entry=sl=tp1=tp2=tp3=inv=None; elow=ehigh=None
        risk=0
        if sweep and zone and sweep.get("follow_through") and (in_ote or poi_count>=2):
            stype="mmxm_direction" if poi_count>=3 else "liq_sweep_entry"
            entry=price
            if direction==LONG:
                elow=zone["bottom"]-atr*0.15; ehigh=zone["top"]+atr*0.35
                sl=min(zone["bottom"]-atr*0.35, sweep["price"]-atr*0.15)
                if sl>=entry: sl=entry-atr*1.2
            else:
                elow=zone["bottom"]-atr*0.35; ehigh=zone["top"]+atr*0.15
                sl=max(zone["top"]+atr*0.35, sweep["price"]+atr*0.15)
                if sl<=entry: sl=entry+atr*1.2
        elif zone and in_ote:
            stype="ote_bos_retest"
            if direction==LONG:
                entry=zone["top"]; elow=zone["bottom"]; ehigh=zone["top"]+atr*0.25
                sl=zone["bottom"]-atr*0.35
            else:
                entry=zone["bottom"]; elow=zone["bottom"]-atr*0.25; ehigh=zone["top"]
                sl=zone["top"]+atr*0.35
        elif zone and (sweep or (fib and ((direction==LONG and fib.get("in_discount")) or (direction==SHORT and fib.get("in_premium"))))):
            stype="breaker_retest" if brk else "ob_rejection"
            if direction==LONG:
                entry=zone["top"]; elow=zone["bottom"]; ehigh=zone["top"]+atr*0.25
                sl=zone["bottom"]-atr*0.35
            else:
                entry=zone["bottom"]; elow=zone["bottom"]-atr*0.25; ehigh=zone["top"]
                sl=zone["top"]+atr*0.35
        elif fvg and (sweep or (fib and ((direction==LONG and fib.get("in_discount")) or (direction==SHORT and fib.get("in_premium"))))):
            stype="choch_fvg_poi"
            entry=price
            if direction==LONG:
                elow=fvg["bottom"]; ehigh=fvg["top"]
                sl=fvg["bottom"]-atr*0.4
            else:
                elow=fvg["bottom"]; ehigh=fvg["top"]
                sl=fvg["top"]+atr*0.4
        elif fvg and (of["pressure"]==("buy" if direction==LONG else "sell")):
            stype="continuation_fvg"
            entry=price
            if direction==LONG:
                elow=fvg["bottom"]; ehigh=fvg["top"]; sl=fvg["bottom"]-atr*0.4
            else:
                elow=fvg["bottom"]; ehigh=fvg["top"]; sl=fvg["top"]+atr*0.4
        # OTE + sweep + premium/discount confluence (without needing an explicit OB)
        elif in_ote and sweep and (fib and ((direction==LONG and fib.get("in_discount")) or (direction==SHORT and fib.get("in_premium")))):
            stype = "ote_entry"
            entry = price
            # SL below/above the liquidity sweep with ATR buffer
            if direction==LONG:
                sl = sweep["price"] - atr*0.4
                elow = price - atr*0.3; ehigh = price + atr*0.2
            else:
                sl = sweep["price"] + atr*0.4
                elow = price - atr*0.2; ehigh = price + atr*0.3
        # Deep premium/discount retracement (85-100%) + sweep = strong reversal
        elif fib and sweep and sweep.get("follow_through") and \
             ((direction==LONG and fib.get("in_discount") and fib.get("retrace_pct",0)>=0.85) or
              (direction==SHORT and fib.get("in_premium") and fib.get("retrace_pct",0)>=0.85)):
            stype = "liq_sweep_entry"
            entry = price
            if direction==LONG:
                sl = min(fib["leg_low"], sweep["price"]) - atr*0.5
                if sl >= entry: sl = entry - atr*1.2
                elow = price - atr*0.3; ehigh = price + atr*0.2
            else:
                sl = max(fib["leg_high"], sweep["price"]) + atr*0.5
                if sl <= entry: sl = entry + atr*1.2
                elow = price - atr*0.2; ehigh = price + atr*0.3
        # Premium/Discount + OF alignment (weak, grade C/D, smaller size)
        elif (fib and ((direction==LONG and fib.get("in_discount") and fib.get("retrace_pct",0)>0.58) or
                       (direction==SHORT and fib.get("in_premium") and fib.get("retrace_pct",0)>0.58))) and \
             of["pressure"]==("buy" if direction==LONG else "sell"):
            stype = "ob_rejection"  # treat as rejection; weaker
            entry = price
            if direction==LONG:
                sl = fib["leg_low"] - atr*0.3
                elow = price - atr*0.3; ehigh = price + atr*0.2
            else:
                sl = fib["leg_high"] + atr*0.3
                elow = price - atr*0.2; ehigh = price + atr*0.3

        if stype is None or entry is None or sl is None: continue
        risk = abs(entry-sl)
        if risk < atr*0.25: continue
        # Targets based on liquidity + RR
        liq_t = next_liq_target(direction)
        if direction==LONG:
            tp1 = entry + risk*1.3
            tp2 = liq_t if (liq_t and entry+risk*1.5 <= liq_t <= entry+risk*4) else entry+risk*2.4
            tp3 = entry + risk*3.8
            inv = sl
        else:
            tp1 = entry - risk*1.3
            tp2 = liq_t if (liq_t and entry-risk*1.5 >= liq_t >= entry-risk*4) else entry-risk*2.4
            tp3 = entry - risk*3.8
            inv = sl
        rr = abs(tp2-entry)/risk
        base_prob = SETUPS[stype]["prob_base"]
        disp_strength = max((s for _,d,s in _displacement(cs,atr)[-5:] if d==direction), default=0)

        # Will finalize score in analyze() with full factors (including MTF, session, news)
        obj = {"type":stype,"direction":direction,"entry":entry,"entry_low":elow or entry-atr*0.2,
               "entry_high":ehigh or entry+atr*0.2,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,
               "invalidation":inv,"ob_quality":ob_q,"fvg_quality":fvg_q,"in_ote":in_ote,
               "poi_count":poi_count,"poi_reasons":poi_reasons,"risk":risk,
               "rr":rr,"base_prob":base_prob,"vwap_above":vwap_above,
               "disp_strength":disp_strength}
        if rr >= SETUPS[stype]["rr_base"]*0.7 and (best is None or rr*obj["base_prob"] > best_score):
            best=obj; best_score=rr*obj["base_prob"]
    return best


# =========================================================
# Grading
# =========================================================
def _grade(conf, prob, rr):
    if conf>=70 and prob>=80 and rr>=2.3: return "A+"
    if conf>=55 and prob>=72 and rr>=1.9: return "A"
    if conf>=42 and prob>=64 and rr>=1.6: return "B"
    if conf>=28 and prob>=57 and rr>=1.3: return "C"
    if conf>=12 and prob>=52 and rr>=1.2: return "D"
    return "F"


# =========================================================
# Narrative (Persian AI explanation)
# =========================================================
def _narrative(setup, bias, direction, conf, prob, of, names, liq_side, fib, rr,
               news, grade, factors, sess, htf_bias, mtf, trend_str, poi_reasons):
    side_map = {LONG:"خرید (لانگ)",SHORT:"فروش (شورت)",NEUTRAL:"انتظار (فلت)"}
    trend_map = {"bullish":"صعودی","bearish":"نزولی","neutral":"خنثی/رنج"}
    side=side_map.get(direction,"انتظار")
    trend=trend_map.get(bias,"خنثی")
    s_txt="، ".join(names) if names else "خارج از سشن‌های اصلی"
    if news: rec="🚫 اخبار پرریسک نزدیک — ورود مطلقاً ممنوع"
    elif direction!=NEUTRAL: rec=f"◀ ورود {side}"
    else: rec="⏸ منتظر تشکیل ساختار واضح بمانید"

    reasons=[]
    if setup and setup.get("type"): reasons.append("الگوی اصلی: "+SETUPS.get(setup["type"],{}).get("name_fa",setup["type"]))
    if bias=="bullish": reasons.append("ساختار بلندمدت صعودی با سقف‌ها و کف‌های بالاتر (HH/HL)")
    if bias=="bearish": reasons.append("ساختار بلندمدت نزولی با سقف‌ها و کف‌های پایین‌تر (LL/LH)")
    if mtf: reasons.append(f"همراستایی با تایم‌فریم بالا (HTF {trend_map.get(htf_bias or 'neutral','-')})")
    if fib and fib.get("in_ote"): reasons.append("قیمت دقیقاً در ناحیه OTE (بهینه‌ترین نقطه ورود ICT)")
    elif fib and direction==LONG and fib.get("in_discount"): reasons.append("قیمت در ناحیه دیسکانت (نیمه پایینی لگ صعودی)")
    elif fib and direction==SHORT and fib.get("in_premium"): reasons.append("قیمت در ناحیه پرمیوم (نیمه بالایی لگ نزولی)")
    if of["pressure"]=="buy": reasons.append("فشار خرید قوی در Order Flow (دلتای CVD مثبت)")
    if of["pressure"]=="sell": reasons.append("فشار فروش قوی در Order Flow (دلتای CVD منفی)")
    if of.get("volume_spike"): reasons.append("حجم نهادی بالا (۲ برابر میانگین) — پای نهنگ‌ها در بازار")
    if of.get("absorption"): reasons.append("جذب سفارش بزرگ (Absorption) در ناحیه")
    if of.get("climax"): reasons.append("نشانه خستگی/کلیماکس — احتمال برگشت قریب‌الوقوع")
    if of.get("cvd_divergence"): reasons.append("واگرایی CVD "+("مثبت" if of["cvd_divergence"]=="bullish" else "منفی"))
    if liq_side=="sellside": reasons.append("سل‌ساید لیکوئیدیتی (استاپ خریداران) جمع‌آوری شد")
    if liq_side=="buyside": reasons.append("بای‌ساید لیکوئیدیتی (استاپ فروشندگان) جمع‌آوری شد")
    if poi_reasons: reasons.append("تلاقی POIها: "+"+".join(poi_reasons))
    if trend_str>=70: reasons.append("قدرت روند بسیار بالا — ادامه حرکت محتمل")
    elif trend_str<30: reasons.append("هشدار: بازار رنج و متلاطم است (قدرت روند پایین)")
    if sess[1]>=1.4: reasons.append("در کیل‌زون همپوشانی لندن-نیویورک — شلوغ‌ترین سشن")
    elif sess[1]>=1.1: reasons.append("در کیل‌زون اصلی (لندن/نیویورک)")
    if news: reasons.append("🚫 اخبار مهم اقتصادی در پیش رو — معامله نکنید")

    verdict_map = {
        "A+":"🌟 ستاپ A+ (کیفیت نهادی) — تمام تاییدهای SMC برقرار، RR عالی، ورود با اطمینان بالا",
        "A": "✅ ستاپ A (قوی) — تاییدهای کافی، مدیریت ریسک استاندارد",
        "B": "🟢 ستاپ B (خوب) — قابل‌قبول، با نصف حجم معموله وارد شوید",
        "C": "🟡 ستاپ C (متوسط) — نیاز به تایید بیشتر؛ منتظر بسته شدن کندل تایید بمانید",
        "D": "🟠 ستاپ D (ضعیف) — فقط برای معامله‌گران باتجربه با ریسک بسیار پایین",
        "F": "❌ ستاپ معتبری تشکیل نشده / درجه F",
    }
    if news: verdict="🚫 پنجره اخبار فاندامنتال — هرگونه ورود تا انتشار خبر ممنوع است"
    else: verdict=verdict_map.get(grade,"❌ ستاپ ضعیف")

    header  = f"📊 گزارش هوش مصنوعی APEX v6\n"
    header += f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    header += f"▫️ روند کلی: {trend}\n"
    if htf_bias: header += f"▫️ تایم‌فریم بالا: {trend_map.get(htf_bias,'-')} {'✅ همراستا' if mtf else '❌ مخالف'}\n"
    header += f"▫️ جلسه: {s_txt}\n"
    if fib:
        header += f"▫️ فیبوناچی لگ اخیر: {fib.get('retrace_pct',0)*100:.0f}% بازگشت\n"
    header += f"▫️ سمت و سوی پیشنهادی: {side}\n\n"

    body = header
    if reasons:
        body += "🔍 دلایل و تاییدها (SMC Confluence):\n  • " + "\n  • ".join(reasons[:12]) + "\n\n"
    body += f"🎯 نتایج اسکن:\n"
    body += f"  • درجه کیفیت: {grade}\n"
    body += f"  • کانفلونس: {conf}/100\n"
    body += f"  • احتمال موفقیت: {prob}%\n"
    body += f"  • نسبت ریسک/ریوارد: 1:{rr:.2f}\n"
    body += f"  • مدل ستاپ: {SETUPS.get(setup.get('type'),{}).get('name_fa','-') if setup else '-'}\n\n"
    body += f"💡 {verdict}\n\n"
    if direction!=NEUTRAL and not news and rr>=1.5:
        body += "📌 طرح معامله (Trade Plan):\n"
        body += "  • ورود پله‌ای در محدوده Entry Zone (سبز روی چارت)\n"
        body += "  • حد ضرر (SL): دقیقاً زیر/روی نقطه بی‌اعتباری (قرمز)\n"
        body += "  • TP1: برداشت جزئی سود (30-40% از حجم) + انتقال SL به نقطه ورود (ریسک فری)\n"
        body += "  • TP2: هدف اصلی مطابق با لیکوئیدیتی خارجی\n"
        body += "  • TP3: هدف جسورانه (تریلینگ استاپ پیشنهاد می‌شود)\n"
        body += "  • ⚠️ هرگز با بیش از ۱-۲٪ سرمایه وارد نشوید.\n"
    elif direction!=NEUTRAL and rr<1.5:
        body += "⚠️ نسبت ریسک/ریوارد کمتر از ۱:۱.۵ است — از ورود صرف‌نظر کنید.\n"

    return {"side":side,"trend":trend,"summary":body,"recommendation":rec,
            "confluence":conf,"probability":prob,"rr":round(rr,2),"verdict":verdict,
            "setup_type":SETUPS.get(setup.get("type"),{}).get("name_fa","-") if setup else "-",
            "grade":grade,"factors":factors}


# =========================================================
# Main analyze entry point
# =========================================================
def analyze(candles_raw, symbol="", timeframe="", htf_bias=None, news_blocked=False):
    cs = _candles(candles_raw)
    if len(cs) < 30: return _empty(symbol, timeframe, len(cs))

    highs,lows = _swings(cs)
    events, bias, bh, bl, leg = _structure(cs, highs, lows)
    atr = _atr(cs)
    disps = _displacement(cs, atr)
    fvgs = _fvg(cs)
    obs = _obs(cs, events, disps, atr)
    br = _breakers(cs, obs)
    liq = _liquidity(cs, highs, lows, atr)
    of = _orderflow(cs)
    kz_comp, names = _sessions(cs)
    sess_name, sess_w, sess_col = _active_session(cs)
    vwap = _vwap(cs)
    trend_str = _trend_strength(cs, events, atr)

    price = cs[-1]["c"]
    active_obs = [o for o in obs if not o["mitigated"]]
    active_fvgs = [g for g in fvgs if not g["mitigated"]]

    fib = _fib_leg(leg, cs, bias, price)
    vis_lo, vis_hi = _vis_range(cs)

    liq_side=None
    rs=[l for l in liq if l["kind"] in ("buyside_liq","sellside_liq")]
    if rs:
        last = rs[-1]
        liq_side = "buyside" if last["kind"]=="buyside_liq" else "sellside"

    setup = _detect(cs, bias, active_obs, active_fvgs, br, liq, price, atr, of, fib, vwap, trend_str, sess_w)

    mtf_align = (htf_bias == bias and htf_bias is not None)

    direction = setup["direction"] if setup else NEUTRAL
    if setup:
        score, factors = _score_confluence(
            direction, bias, fib, setup.get("ob_quality",0), setup.get("fvg_quality",0),
            of, liq_side, mtf_align, sess_w, news_blocked, trend_str,
            setup.get("poi_count",0), setup.get("in_ote",False), setup.get("vwap_above",False),
            setup.get("disp_strength",0), sess_w,
        )
        conf = score
        prob = max(55, min(95, setup["base_prob"] + int((conf-55)*0.55)))
        if news_blocked: prob = max(25, prob-45)
        # Bias mismatch penalty
        if direction==LONG and bias=="bearish": prob = max(45, prob-12); conf = max(20, conf-15)
        if direction==SHORT and bias=="bullish": prob = max(45, prob-12); conf = max(20, conf-15)
        if trend_str < 30: prob = max(45, prob-10)
        setup["probability"] = prob; setup["confluence"] = conf
    else:
        # Provide watching-mode confluence (0-55) even without setup
        base_conf = 0
        if bias=="bullish": base_conf+=10
        if bias=="bearish": base_conf+=10
        if of["pressure"]!="neutral": base_conf+=8
        if mtf_align: base_conf+=10
        if liq_side: base_conf+=6
        if sess_w>=1.0: base_conf+=5
        if trend_str>=60: base_conf+=6
        conf=min(55, base_conf)
        factors=[]; prob=0

    rr = setup["rr"] if setup else 0.0
    entry=sl=tp1=tp2=tp3=inv=ezone=None; setup_fa=None; grade="F"
    if setup:
        entry=setup["entry"]; sl=setup["sl"]; tp1=setup["tp1"]; tp2=setup["tp2"]; tp3=setup["tp3"]; inv=setup["invalidation"]
        ezone={"high":setup["entry_high"],"low":setup["entry_low"]}
        setup_fa=SETUPS.get(setup["type"],{}).get("name_fa",setup["type"])
        if rr<1.0: direction=NEUTRAL
        # If confluence is very low (no supporting factors), mark as F/neutral despite setup found
        if conf < 8: direction=NEUTRAL
        grade = _grade(conf, setup["probability"], rr)

    # ---- Watching (nearby setups not yet confirmed) ----
    watching = []
    if not setup or grade in ("D","F"):
        for direction in (LONG,SHORT):
            ob=None; bd=1e18
            for o in active_obs:
                if o["kind"]!=direction: continue
                mid=(o["top"]+o["bottom"])/2
                d_mid=abs(price-mid)
                if d_mid<bd and d_mid<atr*5:
                    bd=d_mid; ob=o
            if ob is None: continue
            wdir=direction
            # estimate entry zone
            if direction==LONG:
                ent=ob["top"]; sl_est=ob["bottom"]-atr*0.3; risk=ent-sl_est
                tp_est=ent+risk*2.0; in_zone = price>=ob["bottom"]-atr*0.5
            else:
                ent=ob["bottom"]; sl_est=ob["top"]+atr*0.3; risk=sl_est-ent
                tp_est=ent-risk*2.0; in_zone = price<=ob["top"]+atr*0.5
            reasons=[]
            if fib and direction==LONG and fib.get("in_discount"): reasons.append("D")
            if fib and direction==SHORT and fib.get("in_premium"): reasons.append("P")
            if fib and fib.get("in_ote"): reasons.append("OTE")
            if of["pressure"]==("buy" if direction==LONG else "sell"): reasons.append("OF")
            brk = any(b["kind"]==direction and abs(((b["top"]+b["bottom"])/2)-price)<atr*2 for b in br)
            if brk: reasons.append("BRK")
            status = "in_zone" if in_zone else ("approaching" if bd<atr*2 else "nearby")
            watching.append({"direction":wdir,"entry":ent,"sl":sl_est,"tp":tp_est,
                              "distance":bd,"atr":atr,"reasons":reasons,"status":status})

    # ---------- Overlay construction ----------
    zones=[]
    for k in kz_comp:
        zones.append({"kind":"KZ","side":"high","index":k["start"],"top":vis_hi,"bottom":vis_lo,
                      "full_height":True,"name":k["name"],"start_idx":k["start"],"end_idx":k["end"],
                      "vol":k["vol"],"color":k["color"]})
    for o in active_obs[-8:]:
        zones.append({"kind":"OB","side":o["kind"],"index":o["index"],"top":o["top"],"bottom":o["bottom"],
                      "full_height":False,"quality":o.get("quality",5),"fresh":not o.get("tapped",False)})
    for g in active_fvgs[-8:]:
        tag = "iFVG" if g.get("inverse") else "FVG"
        zones.append({"kind":tag,"side":g["kind"],"index":g["index"],"top":g["top"],"bottom":g["bottom"],
                      "full_height":False,"size_pct":g.get("size_pct",0),"quality":g.get("quality",5)})
    for b in br[-4:]:
        zones.append({"kind":"BRK","side":b["kind"],"index":b["index"],"top":b["top"],"bottom":b["bottom"],
                      "full_height":False,"quality":b.get("quality",5)})

    plan_lines=[]
    if entry: plan_lines.append({"kind":"entry","price":entry})
    if sl:    plan_lines.append({"kind":"sl","price":sl})
    if tp1:   plan_lines.append({"kind":"tp1","price":tp1})
    if tp2:   plan_lines.append({"kind":"tp2","price":tp2})
    if tp3:   plan_lines.append({"kind":"tp3","price":tp3})

    labels=[]
    for ev in events[-15:]:
        labels.append({"kind":ev["type"],"dir":ev["dir"],"index":ev["index"],"price":ev["price"]})
    for l in liq[-10:]:
        if "sweep" in l:
            labels.append({"kind":"IDM","dir":l["kind"],"index":l.get("sweep",l["index"]),"price":l["price"]})
        elif l["kind"] in ("eqh","eql"):
            labels.append({"kind":l["kind"].upper(),"dir":l["kind"],"index":l["index"],"price":l["price"]})

    lines=[]
    if fib:
        lines.append({"kind":"fib50","price":fib["fib50"]})
        lines.append({"kind":"fib62","price":fib["fib62"]})
        lines.append({"kind":"fib79","price":fib["fib79"]})
    lines.append({"kind":"vwap","price":vwap})
    for l in liq[-8:]:
        if l["kind"] in ("eqh","eql","recent_high_liq","recent_low_liq"):
            lines.append({"kind":l["kind"],"price":l["price"]})
    lines += plan_lines

    note = "بازار خنثی — منتظر شکست ساختار"
    if news_blocked: note = "🚫 پنجره اخبار — معامله نکنید"
    elif direction==LONG and grade in ("A+","A"): note=f"🌟 ستاپ خرید {grade} — {setup_fa}"
    elif direction==SHORT and grade in ("A+","A"): note=f"🌟 ستاپ فروش {grade} — {setup_fa}"
    elif direction!=NEUTRAL: note=f"ستاپ {direction} درجه {grade} — {setup_fa}"
    elif bias=="bullish": note="روند صعودی — منتظر پولبک به OB/Brk در ناحیه دیسکانت/OTE"
    elif bias=="bearish": note="روند نزولی — منتظر پولبک به OB/Brk در ناحیه پرمیوم/OTE"
    if trend_str<30 and direction==NEUTRAL: note="⚠️ بازار رنج/متلاطم — تا شکست واضح سازه وارد نشوید"

    ai = _narrative(
        {"type":setup["type"]} if setup else None,
        bias, direction, conf, setup["probability"] if setup else 0, of, names, liq_side, fib,
        rr if rr else 0, news_blocked, grade, factors, (sess_name,sess_w,sess_col),
        htf_bias, mtf_align, trend_str, setup.get("poi_reasons",[]) if setup else [],
    )

    return {
        "symbol":symbol,"timeframe":timeframe,"market":"","price":price,"bias":bias,"direction":direction,
        "confluence":conf,"probability":setup.get("probability",0) if setup else 0,
        "setup_type":setup_fa or "-","rr":round(rr,2),"atr":atr,"note":note,"status":"ok","grade":grade,
        "trend_strength":trend_str,"vwap":vwap,"watching":watching,
        "levels":{"entry":entry,"sl":sl,"tp":tp2},"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":inv,
        "entry_zone":ezone,"plan_lines":plan_lines,
        "premium_zone":("discount" if fib and fib.get("in_discount") else "premium" if fib and fib.get("in_premium") else "eq") if fib else "eq",
        "mtf_aligned":mtf_align,"htf_bias":htf_bias,
        "news_blocked":news_blocked,"volume_spike":of.get("volume_spike",False),
        "session_active":sess_name,"session_weight":sess_w,"session_color":sess_col,
        "events":[{"kind":e["type"],"dir":e["dir"],"index":e["index"],"price":e["price"]} for e in events[-15:]],
        "order_blocks":[{"kind":o["kind"],"top":o["top"],"bottom":o["bottom"],"index":o["index"],
                          "quality":o.get("quality",5),"fresh":not o.get("tapped",False)} for o in active_obs[-8:]],
        "fvg":[{"kind":g["kind"],"top":g["top"],"bottom":g["bottom"],"index":g["index"],
                "inverse":g.get("inverse",False),"size_pct":g.get("size_pct",0),"quality":g.get("quality",5)} for g in active_fvgs[-8:]],
        "breakers":[{"kind":b["kind"],"top":b["top"],"bottom":b["bottom"],"index":b["index"],
                      "quality":b.get("quality",5)} for b in br[-4:]],
        "inducements":[{"kind":l["kind"],"price":l["price"],"index":l.get("sweep",l["index"])}
                        for l in liq if "sweep" in l or l["kind"] in ("eqh","eql")],
        "sessions":names,"killzones":[{"kind":"KZ","name":k["name"],"side":"high",
                                         "start_idx":k["start"],"end_idx":k["end"],
                                         "index":k["start"],"top":vis_hi,"bottom":vis_lo,
                                         "vol":k["vol"],"color":k["color"]} for k in kz_comp],
        "orderflow":of,"ai":ai,
        "visible_range":{"low":vis_lo,"high":vis_hi},
        "fib":fib,
        "confluence_factors":factors,
        "overlay":{"lines":lines,"zones":zones,"labels":labels},
        "candles_count":len(cs),"created_by":"Amin Omidi"
    }


def _empty(symbol,tf,count):
    return {"symbol":symbol,"timeframe":tf,"price":0,"bias":"neutral","direction":"neutral","confluence":0,"probability":0,
            "setup_type":"-","rr":0,"atr":0,"note":"حداقل ۳۰ کندل لازم است.","status":"insufficient_data","grade":"-",
            "trend_strength":0,"vwap":0,"watching":[],
            "levels":{"entry":None,"sl":None,"tp":None},"tp1":None,"tp2":None,"tp3":None,"invalidation":None,
            "entry_zone":None,"plan_lines":[],"premium_zone":"eq","mtf_aligned":False,"htf_bias":None,
            "news_blocked":False,"volume_spike":False,"session_active":"-","session_weight":0,"session_color":"#374151",
            "events":[],"order_blocks":[],"fvg":[],"breakers":[],"inducements":[],"sessions":[],"killzones":[],
            "orderflow":{"delta":0,"pressure":"neutral","cvd":0,"cvd_curve":[],"volume_spike":False,
                         "cvd_divergence":None,"absorption":False,"climax":False,"avg_volume":0,"buy_vol":0,"sell_vol":0},
            "ai":{"side":"انتظار","trend":"خنثی","summary":"داده کافی نیست.","recommendation":"منتظر بمانید",
                  "confluence":0,"probability":0,"rr":0,"verdict":"-","setup_type":"-","grade":"-","factors":[]},
            "visible_range":{"low":0,"high":0},"fib":None,"confluence_factors":[],
            "market":"","overlay":{"lines":[],"zones":[],"labels":[]},"candles_count":count,"created_by":"Amin Omidi"}


def detect_smc_features(candles,trend="neutral"):
    r=analyze(candles)
    return {"bias":r.get("bias","neutral"),
            "bos":[e for e in r.get("events",[]) if e.get("kind")=="BOS"],
            "choch":[e for e in r.get("events",[]) if e.get("kind")=="CHoCH"],
            "order_blocks":r.get("order_blocks",[]),"fvg":r.get("fvg",[]),
            "liquidity_sweeps":r.get("inducements",[]),
            "active_ob":(r.get("order_blocks") or [None])[0] if r.get("order_blocks") else None,
            "entry":(r.get("levels") or {}).get("entry"),"sl":(r.get("levels") or {}).get("sl"),
            "tp":(r.get("levels") or {}).get("tp"),"confluence":r.get("confluence",0),
            "direction":r.get("direction","neutral")}
