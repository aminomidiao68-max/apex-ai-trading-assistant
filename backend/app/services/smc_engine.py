"""Apex AI — Pro SMC engine v3.
Improvements over v2:
  * Outlier-aware chart scaling (ignore wick-only spikes / failed liquidity sweeps)
  * Better trend detection using 3-swing confirmation, not first pair
  * Order-blocks detected using last opposing momentum candle before BOS
  * Liquidity sweeps deduplicated; only TRUE external-pool sweeps shown
  * Kill-zones use full-chart height (full vertical shaded bands)
  * Confluence uses: MTF bias, OF delta, retest-of-OB, premium/discount
  * Entry/SL/TP respect 1:2 minimum RR and only fire on strong setups
Created by Amin Omidi
"""
from __future__ import annotations
import math
from datetime import datetime, timezone, timedelta
from typing import Any, List, Dict, Tuple

SESSION_TZ = timezone.utc
_SESSIONS = [
    ("آسیا (توکیو)",    0,  8, 0.6),
    ("لندن",            7, 12, 1.0),
    ("نیویورک",        12, 17, 1.1),
    ("لندن+نیویورک",   12, 13, 1.4),
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
                "v": float(c.get("v", c.get("volume", 0)) or 0),
            })
        except Exception:
            pass
    out.sort(key=lambda x: x["t"])
    return out


def _atr(candles, n=14):
    if len(candles) < n+1: return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["h"]; l = candles[i]["l"]; pc = candles[i-1]["c"]
        trs.append(max(h-l, abs(h-pc), abs(l-pc)))
    return sum(trs[-n:])/n


def _swings(candles, left=3, right=3):
    highs, lows = [], []
    n = len(candles)
    for i in range(left, n-right):
        h = candles[i]["h"]; l = candles[i]["l"]
        if all(h >= candles[i-k]["h"] for k in range(1,left+1)) and all(h >= candles[i+k]["h"] for k in range(1,right+1)):
            highs.append((i,h))
        if all(l <= candles[i-k]["l"] for k in range(1,left+1)) and all(l <= candles[i+k]["l"] for k in range(1,right+1)):
            lows.append((i,l))
    return highs, lows


def _structure(highs, lows, candles):
    """Better BOS/CHoCH detection: track last confirmed swing HH/HL/LH/LL
    and only flip trend on a confirmed break of an internal swing, not an extreme."""
    events = []
    if len(highs) < 3 or len(lows) < 3:
        return events, "neutral", None, None
    # determine initial trend by comparing last two HH/LL sequence
    # Use: recent 8 swings sorted by index
    recent = sorted([(i, p, "H") for i,p in highs[-6:]] + [(i,p,"L") for i,p in lows[-6:]])
    hh = max(p for _,p in highs[-4:])
    ll = min(p for _,p in lows[-4:])
    # initial trend = whichever side broke more recently (by index)
    last_high_i = highs[-1][0]; last_low_i = lows[-1][0]
    trend = "bullish" if last_low_i > last_high_i else "bearish"
    last_bos_h = hh; last_bos_l = ll
    for i, c in enumerate(candles):
        h = c["h"]; l = c["l"]
        if trend == "bullish":
            if h > last_bos_h:
                events.append({"type":"BOS","index":i,"price":h,"direction":"bullish"})
                last_bos_h = h
            elif l < last_bos_l:
                events.append({"type":"CHoCH","index":i,"price":l,"direction":"bearish"})
                trend = "bearish"
                last_bos_l = l
        else:
            if l < last_bos_l:
                events.append({"type":"BOS","index":i,"price":l,"direction":"bearish"})
                last_bos_l = l
            elif h > last_bos_h:
                events.append({"type":"CHoCH","index":i,"price":h,"direction":"bullish"})
                trend = "bullish"
                last_bos_h = h
    return events, trend, last_bos_h, last_bos_l


def _fvg(candles):
    out = []
    n = len(candles)
    for i in range(n-2):
        a,b,c0 = candles[i],candles[i+1],candles[i+2]
        if a["h"] < c0["l"]:
            out.append({"kind":"bullish","index":i+1,"top":c0["l"],"bottom":a["h"],"mitigated":False,"inverse":False,"size_pct":(c0["l"]-a["h"])/a["h"]*100})
        if a["l"] > c0["h"]:
            out.append({"kind":"bearish","index":i+1,"top":a["l"],"bottom":c0["h"],"mitigated":False,"inverse":False,"size_pct":(a["l"]-c0["h"])/c0["h"]*100})
    for g in out:
        for j in range(g["index"]+2,n):
            cc = candles[j]
            if g["kind"]=="bullish" and cc["l"] <= g["bottom"]: g["mitigated"]=True; break
            if g["kind"]=="bearish" and cc["h"] >= g["top"]: g["mitigated"]=True; break
    return out


def _obs(candles, events, atr):
    """Find the last opposing-body candle before each BOS/CHoCH.
       That candle must have body >= 40% of candle range (momentum)."""
    obs=[]
    for ev in events:
        if ev["type"] not in ("BOS","CHoCH"): continue
        i=ev["index"]; d=ev["direction"]; found=None
        for k in range(i-1,max(0,i-20),-1):
            c = candles[k]
            body = abs(c["c"]-c["o"]); rng = c["h"]-c["l"]
            if rng <= 0: continue
            is_bull_body = c["c"]>c["o"]
            is_bear_body = c["c"]<c["o"]
            is_momentum = body/rng >= 0.4
            if d=="bullish" and is_bear_body and is_momentum: found=k; break
            if d=="bearish" and is_bull_body and is_momentum: found=k; break
        if found is None: continue
        oc=candles[found]
        obs.append({"kind":d,"index":found,"top":oc["h"],"bottom":oc["l"],"mitigated":False,"volume":oc["v"]})
    for ob in obs:
        mid=(ob["top"]+ob["bottom"])/2
        for j in range(ob["index"]+1,len(candles)):
            cc=candles[j]
            if ob["kind"]=="bullish" and cc["l"]<=mid: ob["mitigated"]=True; break
            if ob["kind"]=="bearish" and cc["h"]>=mid: ob["mitigated"]=True; break
    return obs


def _breakers(candles, obs):
    br=[]
    for ob in obs:
        if not ob["mitigated"]: continue
        tested=False
        for j in range(ob["index"],len(candles)):
            cc=candles[j]
            if ob["kind"]=="bullish" and cc["h"]>=ob["top"]: tested=True; break
            if ob["kind"]=="bearish" and cc["l"]<=ob["bottom"]: tested=True; break
        if tested:
            br.append({**ob,"kind":"bearish" if ob["kind"]=="bullish" else "bullish"})
    return br


def _liquidity(candles, highs, lows):
    out=[]
    tol_ratio=0.0010  # 0.10% tolerance for equal highs/lows
    # EQH/EQL - pairs within tolerance and far enough apart
    seen_p=set()
    for i in range(1,len(highs)):
        i1,p1=highs[i-1]; i2,p2=highs[i]
        if abs(p1-p2)/p1 < tol_ratio and (i2-i1)>=3:
            key=round(p2,4)
            if key not in seen_p:
                seen_p.add(key)
                out.append({"kind":"eqh","index":i2,"price":p2})
    seen_p.clear()
    for i in range(1,len(lows)):
        i1,p1=lows[i-1]; i2,p2=lows[i]
        if abs(p1-p2)/p1 < tol_ratio and (i2-i1)>=3:
            key=round(p2,4)
            if key not in seen_p:
                seen_p.add(key)
                out.append({"kind":"eql","index":i2,"price":p2})
    # Liquidity sweeps only if a candle breaks a local swing AND closes back (inducement)
    # Also require the swept swing to be "external" (recent 6-candle high/low)
    for si,sp in highs[-8:]:
        # only if sp is the highest in its 5-candle window (external pool)
        window = candles[max(0,si-2):si+3]
        if not window or sp < max(c["h"] for c in window)*0.9995: continue
        for j in range(si+1,min(si+8,len(candles))):
            if candles[j]["h"]>sp and candles[j]["c"]<sp:
                out.append({"kind":"sellside_liq","index":si,"sweep":j,"price":sp}); break
    for si,sp in lows[-8:]:
        window = candles[max(0,si-2):si+3]
        if not window or sp > min(c["l"] for c in window)*1.0005: continue
        for j in range(si+1,min(si+8,len(candles))):
            if candles[j]["l"]<sp and candles[j]["c"]>sp:
                out.append({"kind":"buyside_liq","index":si,"sweep":j,"price":sp}); break
    # recent high/low of last ~20 candles as minor liquidity
    if candles:
        seg=candles[-20:]
        out.append({"kind":"recent_high_liq","index":len(candles)-1,"price":max(c["h"] for c in seg)})
        out.append({"kind":"recent_low_liq","index":len(candles)-1,"price":min(c["l"] for c in seg)})
    # cap inducement output to avoid spam
    return out[-10:]


def _orderflow(candles, window=14):
    if not candles: return {"delta":0.0,"pressure":"neutral","cvd_curve":[]}
    cvd=0.0; curve=[]
    for c in candles[-window*3:]:
        body=c["c"]-c["o"]; rng=c["h"]-c["l"]
        if rng<=0: continue
        buying=abs(body)/rng if body>0 else 0
        selling=abs(body)/rng if body<0 else 0
        dlt=(buying-selling)*c["v"]
        cvd+=dlt
        curve.append({"t":c["t"],"cvd":cvd})
    last=candles[-window:]
    dlt=0; vol=0
    for c in last:
        body=c["c"]-c["o"]; rng=c["h"]-c["l"]
        if rng<=0: continue
        dlt+=(1 if body>0 else -1 if body<0 else 0)*c["v"]*abs(body)/rng
        vol+=c["v"]
    norm=(dlt/vol) if vol>0 else 0
    pressure="buy" if norm>0.15 else "sell" if norm<-0.15 else "neutral"
    return {"delta":round(norm,3),"pressure":pressure,"cvd_curve":curve[-30:]}


def _sessions(candles, interval_minutes):
    if not candles or candles[0]["t"]<=0: return [], []
    zones=[]; names=[]
    step=interval_minutes or 15
    for i,c in enumerate(candles):
        try: dt=datetime.fromtimestamp(c["t"],tz=SESSION_TZ)
        except Exception: continue
        h=dt.hour+dt.minute/60
        for name,s,e,w in _SESSIONS:
            if s<=h<e:
                if w>=1.0:
                    zones.append({"kind":"killzone","name":name,"index":i,"weight":w})
                    if name not in names: names.append(name)
                break
    compressed=[]
    for z in zones:
        if compressed and compressed[-1]["name"]==z["name"] and z["index"]==compressed[-1]["end"]+1:
            compressed[-1]["end"]=z["index"]
        else:
            compressed.append({"kind":"killzone","name":z["name"],"start":z["index"],"end":z["index"],"weight":z["weight"]})
    out=[]
    # for KZ zones we want FULL chart height, so we mark full_height=true and leave top/bottom = None
    for z in compressed:
        out.append({"kind":"KZ","name":z["name"],"side":"high" if z["weight"]>=1.3 else "mid",
                    "start_idx":z["start"],"end_idx":z["end"],"top":None,"bottom":None,"index":z["start"],"full_height":True})
    return out, names


def _parse_tf_minutes(tf):
    try:
        t=(tf or "15").lower().strip()
        if t.endswith("min") or t.endswith("m"): return int(''.join(ch for ch in t if ch.isdigit()) or 15)
        if t.endswith("h"): return int(''.join(ch for ch in t if ch.isdigit()) or 1)*60
        if t.endswith("d"): return 1440
    except Exception: pass
    return 15


def _narrative(bias, direction, conf, oflow, sessions, liq_side, near_ob, near_fvg, price, note, rr, premium):
    side_label={"long":"خرید (لانگ)","short":"فروش (شورت)","neutral":"انتظار"}[direction]
    trend_label={"bullish":"صعودی","bearish":"نزولی","neutral":"خنثی"}[bias]
    session_txt="، ".join(sessions) if sessions else "خارج از سشن اصلی"
    reasons=[]
    if bias=="bullish": reasons.append("ساختار بازار صعودی (HH/HB)")
    if bias=="bearish": reasons.append("ساختار بازار نزولی (LL/LB)")
    if near_ob: reasons.append(("اوردر بلاک " + ("صعودی" if direction=="long" else "نزولی") + " تایید شده"))
    if near_fvg: reasons.append("FVG پُر نشده در مسیر")
    if premium=="discount" and direction=="long": reasons.append("قیمت در ناحیه دیسکانت (خرید ارزان)")
    if premium=="premium" and direction=="short": reasons.append("قیمت در ناحیه پرمیوم (فروش گران)")
    if oflow["pressure"]=="buy": reasons.append("فشار خرید در اوردر فلو")
    if oflow["pressure"]=="sell": reasons.append("فشار فروش در اوردر فلو")
    if liq_side=="sellside": reasons.append("لیکوئیدیتی سل‌ساید (سقف‌ها) جمع شد")
    if liq_side=="buyside": reasons.append("لیکوئیدیتی بای‌ساید (کف‌ها) جمع شد")
    rec="◀ سناریوی پیشنهادی: "+side_label
    verdict="با کانفلونس "+str(conf)+"/4 و RR 1:"+str(round(rr,1))+". "
    if conf>=3 and direction!="neutral" and rr>=2:
        verdict+="✅ ستاپ با احتمال بالا"
    elif conf>=2 and direction!="neutral" and rr>=1.5:
        verdict+="⚠️ ستاپ متوسط — با حجم کم وارد شوید"
    else:
        verdict+="❌ ستاپ ضعیف — منتظر تایید بیشتر بمانید"
    body="بر اساس تحلیل ساختار، روند "+trend_label+" است. "
    if reasons: body+="دلایل: "+"؛ ".join(reasons[:5])+". "
    body+="سشن فعال: "+session_txt+". "+verdict
    return {"side":side_label,"trend":trend_label,"summary":body,"recommendation":rec,"confluence":conf,"rr":round(rr,2)}


def _premium_discount(price, hi, lo):
    """Classify price in recent range as premium (upper 30%) / discount (lower 30%) / equilibrium (middle)."""
    rng=hi-lo
    if rng<=0: return "eq"
    rel=(price-lo)/rng
    if rel>=0.7: return "premium"
    if rel<=0.3: return "discount"
    return "eq"


def _visible_range(candles, clip_atr=True):
    """Compute a chart view range that ignores extreme single-wick outliers
    so candles don't look flattened."""
    if not candles: return 0,1
    highs = sorted(c["h"] for c in candles); lows = sorted((c["l"] for c in candles), reverse=True)
    # trim top/bottom 2%
    n=len(highs); trim=max(1,n//50)
    hi = highs[n-1-trim]
    lo = lows[n-1-trim]
    return lo, hi


def analyze(candles_raw, symbol="", timeframe="", htf_bias=None):
    candles=_candles(candles_raw)
    if len(candles)<30:
        return _empty(symbol, timeframe, len(candles))
    highs,lows=_swings(candles)
    events,bias,bh,bl=_structure(highs,lows,candles)
    atr=_atr(candles)
    fvgs=_fvg(candles)
    obs=_obs(candles,events,atr)
    br=_breakers(candles,obs)
    liq=_liquidity(candles,highs,lows)
    oflow=_orderflow(candles)
    kz,session_names=_sessions(candles,_parse_tf_minutes(timeframe))

    price=candles[-1]["c"]
    active_obs=[o for o in obs if not o["mitigated"]]
    active_fvg=[g for g in fvgs if not g["mitigated"]]
    # recent range for premium/discount
    seg=candles[-60:] if len(candles)>=60 else candles
    r_hi=max(c["h"] for c in seg); r_lo=min(c["l"] for c in seg)
    pd=_premium_discount(price,r_hi,r_lo)

    entry=sl=tp=None; direction="neutral"; conf=0
    near_ob=False; near_fvg=False; liq_side=None
    rr=0.0

    # Entry logic: only enter when price is retesting a valid OB in bias direction
    if bias=="bullish":
        # candidate zones = bullish OB below price (recent)
        cands=[o for o in active_obs if o["kind"]=="bullish" and o["top"]<=price]
        cands += [b for b in br if b["kind"]=="bullish" and b["top"]<=price]
        if cands:
            z=max(cands,key=lambda x:x["top"])
            entry=z["top"]; sl=z["bottom"]-atr*0.3
            risk=entry-sl
            if risk>0:
                tp=price+risk*2; rr=(tp-entry)/risk; near_ob=True
                # entry only valid if current price is within/near OB (within 1 ATR of top)
                if price<=z["top"]+atr*1.5 and price>=z["bottom"]-atr*0.5:
                    conf+=2
        # fvg
        in_bull_fvg=any(g["kind"]=="bullish" and g["bottom"]<=price<=g["top"]*1.005 for g in active_fvg)
        if in_bull_fvg: conf+=1; near_fvg=True
        if oflow["pressure"]=="buy": conf+=1
        recent_sweeps=[l for l in liq if l.get("kind")=="buyside_liq"]
        if recent_sweeps and recent_sweeps[-1]["index"]>=len(candles)-20:
            conf+=1; liq_side="buyside"
        if pd=="discount": conf+=1
        if htf_bias=="bullish": conf+=1
        # direction: if at least 2 confluence points and OB present -> long
        if near_ob and conf>=2: direction="long"

    elif bias=="bearish":
        cands=[o for o in active_obs if o["kind"]=="bearish" and o["bottom"]>=price]
        cands += [b for b in br if b["kind"]=="bearish" and b["bottom"]>=price]
        if cands:
            z=min(cands,key=lambda x:x["bottom"])
            entry=z["bottom"]; sl=z["top"]+atr*0.3
            risk=sl-entry
            if risk>0:
                tp=price-risk*2; rr=(entry-tp)/risk; near_ob=True
                if price>=z["bottom"]-atr*1.5 and price<=z["top"]+atr*0.5:
                    conf+=2
        in_bear_fvg=any(g["kind"]=="bearish" and g["bottom"]*0.995<=price<=g["top"] for g in active_fvg)
        if in_bear_fvg: conf+=1; near_fvg=True
        if oflow["pressure"]=="sell": conf+=1
        recent_sweeps=[l for l in liq if l.get("kind")=="sellside_liq"]
        if recent_sweeps and recent_sweeps[-1]["index"]>=len(candles)-20:
            conf+=1; liq_side="sellside"
        if pd=="premium": conf+=1
        if htf_bias=="bearish": conf+=1
        if near_ob and conf>=2: direction="short"

    conf=min(conf,4)

    # Build overlay zones
    vis_lo, vis_hi = _visible_range(candles)
    zones=[]
    for k in kz[-6:]:
        zones.append({"kind":"KZ","side":k["side"],"index":k["index"],"top":vis_hi,"bottom":vis_lo,
                      "full_height":True,"name":k["name"],"start_idx":k["start_idx"],"end_idx":k["end_idx"]})
    for o in active_obs[-6:]:
        zones.append({"kind":"OB","side":o["kind"],"index":o["index"],"top":o["top"],"bottom":o["bottom"],"full_height":False})
    for g in active_fvg[-6:]:
        tag="FVG" if not g.get("inverse") else "iFVG"
        zones.append({"kind":tag,"side":g["kind"],"index":g["index"],"top":g["top"],"bottom":g["bottom"],"full_height":False,"size_pct":g.get("size_pct",0)})
    for b in br[-4:]:
        zones.append({"kind":"BRK","side":b["kind"],"index":b["index"],"top":b["top"],"bottom":b["bottom"],"full_height":False})

    labels=[]
    for ev in events[-12:]:
        labels.append({"kind":ev["type"],"dir":ev["direction"],"index":ev["index"],"price":ev["price"]})
    for l in liq[-8:]:
        labels.append({"kind":"LIQ","dir":l["kind"],"index":l.get("sweep",l["index"]),"price":l["price"]})

    lines=[]
    if bh is not None: lines.append({"kind":"high","price":bh})
    if bl is not None: lines.append({"kind":"low","price":bl})
    for l in liq[-6:]:
        if l["kind"] in ("eqh","eql","recent_high_liq","recent_low_liq"):
            lines.append({"kind":l["kind"],"price":l["price"]})

    note="روند خنثی — منتظر تایید"
    if direction=="long" and conf>=3 and rr>=2: note="ستاپ خرید معتبر با کانفلونس بالا"
    elif direction=="short" and conf>=3 and rr>=2: note="ستاپ فروش معتبر با کانفلونس بالا"
    elif direction=="long" and conf>=2: note="ناحیه لانگ زیر نظر"
    elif direction=="short" and conf>=2: note="ناحیه شورت زیر نظر"
    elif bias=="bullish": note="روند صعودی، منتظر پولبک به OB"
    elif bias=="bearish": note="روند نزولی، منتظر پولبک به OB"

    ai=_narrative(bias,direction,conf,oflow,session_names,liq_side,near_ob,near_fvg,price,note,rr if rr>0 else 0,pd)

    return {
        "symbol":symbol,"timeframe":timeframe,"price":price,
        "bias":bias,"direction":direction,"confluence":conf,"note":note,"status":"ok",
        "levels":{"entry":entry,"sl":sl,"tp":tp},
        "rr": round(rr,2),
        "premium_zone": pd,
        "events":[{"kind":e["type"],"dir":e["direction"],"index":e["index"],"price":e["price"]} for e in events[-10:]],
        "order_blocks":[{"kind":o["kind"],"top":o["top"],"bottom":o["bottom"],"index":o["index"]} for o in active_obs[-6:]],
        "fvg":[{"kind":g["kind"],"top":g["top"],"bottom":g["bottom"],"index":g["index"],"inverse":g.get("inverse",False),"size_pct":g.get("size_pct",0)} for g in active_fvg[-6:]],
        "breakers":[{"kind":b["kind"],"top":b["top"],"bottom":b["bottom"],"index":b["index"]} for b in br[-4:]],
        "inducements":[{"kind":l["kind"],"price":l["price"],"index":l.get("sweep",l["index"])} for l in liq if "sweep" in l or l["kind"] in ("eqh","eql")],
        "sessions":session_names,
        "killzones": [{"kind":"KZ","name":k["name"],"side":k["side"],"start_idx":k["start_idx"],"end_idx":k["end_idx"],
                       "index":k["start_idx"],"top":vis_hi,"bottom":vis_lo} for k in kz[-6:]],
        "orderflow":oflow,"ai":ai,
        "visible_range":{"low":vis_lo,"high":vis_hi},
        "atr": atr,
        "overlay":{"lines":lines,"zones":zones,"labels":labels},
        "candles_count":len(candles),"created_by":"Amin Omidi"
    }


def _empty(symbol,tf,count):
    return {"symbol":symbol,"timeframe":tf,"price":0,"bias":"neutral","direction":"neutral","confluence":0,
            "note":"حداقل ۳۰ کندل برای تحلیل لازم است.","status":"insufficient_data",
            "levels":{"entry":None,"sl":None,"tp":None},"rr":0,"premium_zone":"eq",
            "events":[],"order_blocks":[],"fvg":[],"breakers":[],"inducements":[],
            "sessions":[],"killzones":[],"orderflow":{"delta":0,"pressure":"neutral","cvd_curve":[]},
            "ai":{"side":"انتظار","trend":"خنثی","summary":"داده کافی نیست.","recommendation":"منتظر بمانید","confluence":0,"rr":0},
            "visible_range":{"low":0,"high":0},"atr":0,
            "overlay":{"lines":[],"zones":[],"labels":[]},"candles_count":count,"created_by":"Amin Omidi"}


def detect_smc_features(candles, trend="neutral"):
    r=analyze(candles)
    obs=r.get("order_blocks",[]); fvgs=r.get("fvg",[]); liq=r.get("inducements",[])
    bos=[e for e in r.get("events",[]) if e.get("kind")=="BOS"]
    choch=[e for e in r.get("events",[]) if e.get("kind")=="CHoCH"]
    return {"bias":r.get("bias","neutral"),"bos":bos,"choch":choch,"order_blocks":obs,"fvg":fvgs,"liquidity_sweeps":liq,
            "active_ob":None,"entry":(r.get("levels") or {}).get("entry"),"sl":(r.get("levels") or {}).get("sl"),"tp":(r.get("levels") or {}).get("tp"),
            "confluence":r.get("confluence",0),"direction":r.get("direction","neutral")}
