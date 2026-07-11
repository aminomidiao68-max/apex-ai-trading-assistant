"""Apex AI — Pro SMC engine v4.
Multi-timeframe confluence, setup classifier, probability score,
full trade plan (entry zone / TP1-3 / invalidation), news block,
volume spike detection, premium/discount alignment.
Created by Amin Omidi
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Any, List, Dict

SESSION_TZ = timezone.utc
_SESSIONS = [
    ("آسیا (توکیو)", 0, 8, 0.6),
    ("لندن", 7, 12, 1.0),
    ("نیویورک", 12, 17, 1.1),
    ("لندن+نیویورک", 12, 13, 1.4),
    ("آمریکا پایانی", 17, 21, 0.7),
]

SETUP_TYPES = {
    "bos_retest":  {"name_fa": "پولبک به BOS",        "weight": 20},
    "choch_fvg":   {"name_fa": "CHoCH + FVG",          "weight": 22},
    "liq_sweep":   {"name_fa": "لیکوئیدیتی سویپ",      "weight": 25},
    "breaker":     {"name_fa": "بریکر بلاک",           "weight": 18},
    "orb":         {"name_fa": "محدوده باز شدن ORB",   "weight": 15},
}


def _candles(raw):
    out = []
    for c in (raw or []):
        if not isinstance(c, dict):
            try: c = dict(c)
            except Exception: continue
        try:
            out.append({"t": float(c.get("t", c.get("time",0))),
                "o": float(c.get("o",c.get("open",0))),"h":float(c.get("h",c.get("high",0))),
                "l":float(c.get("l",c.get("low",0))),"c":float(c.get("c",c.get("close",0))),
                "v":float(c.get("v",c.get("volume",0)) or 0)})
        except Exception: pass
    out.sort(key=lambda x:x["t"])
    return out


def _atr(candles,n=14):
    if len(candles)<n+1: return 0.0
    trs=[]
    for i in range(1,len(candles)):
        h=candles[i]["h"]; l=candles[i]["l"]; pc=candles[i-1]["c"]
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(trs[-n:])/n


def _swings(candles,left=3,right=3):
    highs=[];lows=[];n=len(candles)
    for i in range(left,n-right):
        h=candles[i]["h"];l=candles[i]["l"]
        if all(h>=candles[i-k]["h"] for k in range(1,left+1)) and all(h>=candles[i+k]["h"] for k in range(1,right+1)):
            highs.append((i,h))
        if all(l<=candles[i-k]["l"] for k in range(1,left+1)) and all(l<=candles[i+k]["l"] for k in range(1,right+1)):
            lows.append((i,l))
    return highs,lows


def _structure(highs,lows,candles):
    events=[]
    if len(highs)<3 or len(lows)<3: return events,"neutral",None,None
    last_high_i=highs[-1][0];last_low_i=lows[-1][0]
    trend="bullish" if last_low_i>last_high_i else "bearish"
    last_bos_h=max(p for _,p in highs[-4:]);last_bos_l=min(p for _,p in lows[-4:])
    for i,c in enumerate(candles):
        h=c["h"];l=c["l"]
        if trend=="bullish":
            if h>last_bos_h:
                events.append({"type":"BOS","index":i,"price":h,"direction":"bullish"}); last_bos_h=h
            elif l<last_bos_l:
                events.append({"type":"CHoCH","index":i,"price":l,"direction":"bearish"}); trend="bearish"; last_bos_l=l
        else:
            if l<last_bos_l:
                events.append({"type":"BOS","index":i,"price":l,"direction":"bearish"}); last_bos_l=l
            elif h>last_bos_h:
                events.append({"type":"CHoCH","index":i,"price":h,"direction":"bullish"}); trend="bullish"; last_bos_h=h
    return events,trend,last_bos_h,last_bos_l


def _fvg(candles):
    out=[];n=len(candles)
    for i in range(n-2):
        a,b,c0=candles[i],candles[i+1],candles[i+2]
        if a["h"]<c0["l"]:
            out.append({"kind":"bullish","index":i+1,"top":c0["l"],"bottom":a["h"],"mitigated":False,"inverse":False,"size_pct":(c0["l"]-a["h"])/a["h"]*100})
        if a["l"]>c0["h"]:
            out.append({"kind":"bearish","index":i+1,"top":a["l"],"bottom":c0["h"],"mitigated":False,"inverse":False,"size_pct":(a["l"]-c0["h"])/c0["h"]*100})
    for g in out:
        for j in range(g["index"]+2,n):
            cc=candles[j]
            if g["kind"]=="bullish" and cc["l"]<=g["bottom"]: g["mitigated"]=True; break
            if g["kind"]=="bearish" and cc["h"]>=g["top"]: g["mitigated"]=True; break
    return out


def _obs(candles,events,atr):
    obs=[]
    for ev in events:
        if ev["type"] not in ("BOS","CHoCH"): continue
        i=ev["index"];d=ev["direction"];found=None
        for k in range(i-1,max(0,i-20),-1):
            c=candles[k];body=abs(c["c"]-c["o"]);rng=c["h"]-c["l"]
            if rng<=0: continue
            bull=c["c"]>c["o"]; mom=body/rng>=0.4
            if d=="bullish" and not bull and mom: found=k; break
            if d=="bearish" and bull and mom: found=k; break
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


def _breakers(candles,obs):
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


def _liquidity(candles,highs,lows):
    out=[];tol=0.0010
    seen=set()
    for i in range(1,len(highs)):
        i1,p1=highs[i-1];i2,p2=highs[i]
        if abs(p1-p2)/p1<tol and (i2-i1)>=3:
            k=round(p2,4)
            if k not in seen:
                seen.add(k); out.append({"kind":"eqh","index":i2,"price":p2})
    seen.clear()
    for i in range(1,len(lows)):
        i1,p1=lows[i-1];i2,p2=lows[i]
        if abs(p1-p2)/p1<tol and (i2-i1)>=3:
            k=round(p2,4)
            if k not in seen:
                seen.add(k); out.append({"kind":"eql","index":i2,"price":p2})
    for si,sp in highs[-10:]:
        win=candles[max(0,si-2):si+3]
        if win and sp<max(c["h"] for c in win)*0.9995: continue
        for j in range(si+1,min(si+8,len(candles))):
            if candles[j]["h"]>sp and candles[j]["c"]<sp:
                out.append({"kind":"sellside_liq","index":si,"sweep":j,"price":sp}); break
    for si,sp in lows[-10:]:
        win=candles[max(0,si-2):si+3]
        if win and sp>min(c["l"] for c in win)*1.0005: continue
        for j in range(si+1,min(si+8,len(candles))):
            if candles[j]["l"]<sp and candles[j]["c"]>sp:
                out.append({"kind":"buyside_liq","index":si,"sweep":j,"price":sp}); break
    if candles:
        seg=candles[-20:]
        out.append({"kind":"recent_high_liq","index":len(candles)-1,"price":max(c["h"] for c in seg)})
        out.append({"kind":"recent_low_liq","index":len(candles)-1,"price":min(c["l"] for c in seg)})
    return out[-12:]


def _orderflow(candles,window=14):
    if not candles: return {"delta":0.0,"pressure":"neutral","cvd_curve":[],"volume_spike":False}
    cvd=0.0;curve=[];vols=[]
    for c in candles[-window*3:]:
        body=c["c"]-c["o"];rng=c["h"]-c["l"]
        if rng<=0: continue
        buy=abs(body)/rng if body>0 else 0;sell=abs(body)/rng if body<0 else 0
        dlt=(buy-sell)*c["v"];cvd+=dlt
        curve.append({"t":c["t"],"cvd":cvd})
        vols.append(c["v"])
    last=candles[-window:];dlt=0;vol=0
    for c in last:
        body=c["c"]-c["o"];rng=c["h"]-c["l"]
        if rng<=0: continue
        dlt+=(1 if body>0 else -1 if body<0 else 0)*c["v"]*abs(body)/rng
        vol+=c["v"]
    norm=dlt/vol if vol>0 else 0
    pressure="buy" if norm>0.15 else "sell" if norm<-0.15 else "neutral"
    avg_v=sum(vols)/max(1,len(vols))
    spike = vols[-1] > avg_v*1.8 if vols else False
    return {"delta":round(norm,3),"pressure":pressure,"cvd_curve":curve[-30:],"volume_spike":bool(spike)}


def _sessions(candles, interval_minutes):
    if not candles or candles[0]["t"]<=0: return [],[]
    zones=[];names=[]
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
    comp=[]
    for z in zones:
        if comp and comp[-1]["name"]==z["name"] and z["index"]==comp[-1]["end"]+1:
            comp[-1]["end"]=z["index"]
        else:
            comp.append({"kind":"killzone","name":z["name"],"start":z["index"],"end":z["index"],"weight":z["weight"]})
    return comp,names


def _parse_tf_minutes(tf):
    try:
        t=(tf or "15").lower().strip()
        if t.endswith("min") or t.endswith("m"): return int(''.join(ch for ch in t if ch.isdigit()) or 15)
        if t.endswith("h"): return int(''.join(ch for ch in t if ch.isdigit()) or 1)*60
        if t.endswith("d"): return 1440
    except Exception: pass
    return 15


def _premium_discount(price,hi,lo):
    rng=hi-lo
    if rng<=0: return "eq"
    rel=(price-lo)/rng
    if rel>=0.7: return "premium"
    if rel<=0.3: return "discount"
    return "eq"


def _visible_range(candles):
    if not candles: return 0,1
    hs=sorted(c["h"] for c in candles);ls=sorted((c["l"] for c in candles),reverse=True)
    n=len(hs);t=max(1,n//50)
    return ls[n-1-t],hs[n-1-t]


def _narrative(setup,bias,direction,conf,prob,oflow,sessions,liq_side,pd,rr,news_block):
    side={"long":"خرید (لانگ)","short":"فروش (شورت)","neutral":"انتظار"}[direction]
    trend={"bullish":"صعودی","bearish":"نزولی","neutral":"خنثی"}[bias]
    s_txt="، ".join(sessions) if sessions else "خارج از سشن اصلی"
    reasons=[]
    if setup and setup.get("type"):
        reasons.append("ستاپ: "+SETUP_TYPES.get(setup["type"],{}).get("name_fa",setup["type"]))
    if bias=="bullish": reasons.append("ساختار صعودی (HH/HL)")
    if bias=="bearish": reasons.append("ساختار نزولی (LL/LH)")
    if pd=="discount" and direction=="long": reasons.append("قیمت در ناحیه دیسکانت")
    if pd=="premium" and direction=="short": reasons.append("قیمت در ناحیه پرمیوم")
    if oflow["pressure"]=="buy": reasons.append("فشار خرید (OF+)")
    if oflow["pressure"]=="sell": reasons.append("فشار فروش (OF-)")
    if oflow.get("volume_spike"): reasons.append("افزایش حجم")
    if liq_side=="sellside": reasons.append("سل‌ساید لیکوئیدیتی جمع شد")
    if liq_side=="buyside": reasons.append("بای‌ساید لیکوئیدیتی جمع شد")
    if news_block: reasons.append("⚠️ اخبار پرریسک نزدیک")
    rec="◀ "+side
    if prob>=75 and rr>=2: v="✅ ستاپ قوی با احتمال بالا"
    elif prob>=60 and rr>=1.5: v="⚠️ ستاپ قابل‌قبول — حجم کم"
    elif prob<60: v="❌ ستاپ ضعیف — منتظر تایید"
    else: v="⏸ ستاپ در حال تشکیل"
    body="روند "+trend+". "
    if reasons: body+="دلایل: "+"؛ ".join(reasons[:6])+". "
    body+="سشن: "+s_txt+". کانفلونس "+str(conf)+"/100 • احتمال "+str(prob)+"% • RR 1:"+str(round(rr,1) if rr else 0)+". "+v
    return {"side":side,"trend":trend,"summary":body,"recommendation":rec,"confluence":conf,"probability":prob,"rr":round(rr,2) if rr else 0,
            "verdict":v,"setup_type":(setup or {}).get("name_fa","-")}


def _detect_setups(candles, bias, active_obs, active_fvg, br, liq, price, atr, oflow, pd):
    """Return best setup candidate (or None) with score/probability/entry/sl/tps."""
    best=None; best_score=0
    atr = atr or (price*0.001)
    # 1. BOS retest on OB
    if bias=="bullish":
        for o in active_obs:
            if o["kind"]!="bullish" or o["top"]>=price: continue
            # price retest within 1.5 ATR of OB top
            if price-o["top"] <= atr*1.8 and price>=o["bottom"]-atr*0.5:
                entry=o["top"]; sl=o["bottom"]-atr*0.4; risk=entry-sl
                if risk<=0: continue
                tp1=price+risk*1.2; tp2=price+risk*2; tp3=price+risk*3.2
                score=SETUP_TYPES["bos_retest"]["weight"]
                if oflow["pressure"]=="buy": score+=15
                if pd=="discount": score+=12
                if oflow.get("volume_spike"): score+=8
                if liq=="buyside": score+=15
                if score>best_score:
                    best_score=score
                    best={"type":"bos_retest","direction":"long","entry":entry,"entry_high":o["top"]+atr*0.2,"entry_low":o["bottom"],
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,
                          "score":score,"probability":min(95,50+score)}
        for b in br:
            if b["kind"]!="bullish" or b["top"]>=price: continue
            if price-b["top"]<=atr*1.8:
                entry=b["top"]; sl=b["bottom"]-atr*0.4; risk=entry-sl
                if risk<=0: continue
                tp1=price+risk*1.2; tp2=price+risk*2; tp3=price+risk*3.2
                score=SETUP_TYPES["breaker"]["weight"]
                if oflow["pressure"]=="buy": score+=15
                if pd=="discount": score+=10
                if liq=="buyside": score+=12
                if score>best_score:
                    best_score=score
                    best={"type":"breaker","direction":"long","entry":entry,"entry_high":b["top"]+atr*0.2,"entry_low":b["bottom"],
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,"score":score,
                          "probability":min(95,50+score)}
        # CHoCH + bullish FVG formation
        for g in active_fvg:
            if g["kind"]!="bullish": continue
            if g["bottom"]<=price<=g["top"]+atr*0.3:
                entry=price; sl=g["bottom"]-atr*0.4; risk=entry-sl
                if risk<=0: continue
                tp1=price+risk*1.2; tp2=price+risk*2; tp3=price+risk*3.2
                score=SETUP_TYPES["choch_fvg"]["weight"]
                if oflow["pressure"]=="buy": score+=15
                if liq=="buyside": score+=18
                if score>best_score:
                    best_score=score
                    best={"type":"choch_fvg","direction":"long","entry":entry,"entry_high":g["top"],"entry_low":g["bottom"],
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,"score":score,
                          "probability":min(95,50+score)}
    elif bias=="bearish":
        for o in active_obs:
            if o["kind"]!="bearish" or o["bottom"]<=price: continue
            if o["bottom"]-price <= atr*1.8 and price<=o["top"]+atr*0.5:
                entry=o["bottom"]; sl=o["top"]+atr*0.4; risk=sl-entry
                if risk<=0: continue
                tp1=price-risk*1.2; tp2=price-risk*2; tp3=price-risk*3.2
                score=SETUP_TYPES["bos_retest"]["weight"]
                if oflow["pressure"]=="sell": score+=15
                if pd=="premium": score+=12
                if oflow.get("volume_spike"): score+=8
                if liq=="sellside": score+=15
                if score>best_score:
                    best_score=score
                    best={"type":"bos_retest","direction":"short","entry":entry,"entry_high":o["top"],"entry_low":o["bottom"]-atr*0.2,
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,"score":score,
                          "probability":min(95,50+score)}
        for b in br:
            if b["kind"]!="bearish" or b["bottom"]<=price: continue
            if b["bottom"]-price <= atr*1.8:
                entry=b["bottom"]; sl=b["top"]+atr*0.4; risk=sl-entry
                if risk<=0: continue
                tp1=price-risk*1.2; tp2=price-risk*2; tp3=price-risk*3.2
                score=SETUP_TYPES["breaker"]["weight"]
                if oflow["pressure"]=="sell": score+=15
                if pd=="premium": score+=10
                if liq=="sellside": score+=12
                if score>best_score:
                    best_score=score
                    best={"type":"breaker","direction":"short","entry":entry,"entry_high":b["top"],"entry_low":b["bottom"]-atr*0.2,
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,"score":score,
                          "probability":min(95,50+score)}
        for g in active_fvg:
            if g["kind"]!="bearish": continue
            if g["bottom"]-atr*0.3 <= price <= g["top"]:
                entry=price; sl=g["top"]+atr*0.4; risk=sl-entry
                if risk<=0: continue
                tp1=price-risk*1.2; tp2=price-risk*2; tp3=price-risk*3.2
                score=SETUP_TYPES["choch_fvg"]["weight"]
                if oflow["pressure"]=="sell": score+=15
                if liq=="sellside": score+=18
                if score>best_score:
                    best_score=score
                    best={"type":"choch_fvg","direction":"short","entry":entry,"entry_high":g["top"],"entry_low":g["bottom"],
                          "sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":sl,"score":score,
                          "probability":min(95,50+score)}
    # Liq sweep bonus (any bias)
    recent_sweeps=[l for l in liq if l.get("kind","").endswith("_liq")]
    if recent_sweeps:
        sw=recent_sweeps[-1]
        # Already covered above; if no setup yet, mark it as watching
        if not best:
            # weaker "watching" signal only — don't open, just monitor
            best=None  # leave null; confluence low
    return best


def analyze(candles_raw, symbol="", timeframe="", htf_bias=None, news_blocked=False):
    candles=_candles(candles_raw)
    if len(candles)<30: return _empty(symbol,timeframe,len(candles))
    highs,lows=_swings(candles)
    events,bias,bh,bl=_structure(highs,lows,candles)
    atr=_atr(candles)
    fvgs=_fvg(candles);obs=_obs(candles,events,atr);br=_breakers(candles,obs)
    liq=_liquidity(candles,highs,lows);oflow=_orderflow(candles)
    kz_comp,session_names=_sessions(candles,_parse_tf_minutes(timeframe))
    price=candles[-1]["c"]
    active_obs=[o for o in obs if not o["mitigated"]]
    active_fvg=[g for g in fvgs if not g["mitigated"]]
    seg=candles[-60:] if len(candles)>=60 else candles
    r_hi=max(c["h"] for c in seg); r_lo=min(c["l"] for c in seg)
    pd=_premium_discount(price,r_hi,r_lo)
    vis_lo,vis_hi=_visible_range(candles)

    # liq side
    liq_side=None
    rs=[l for l in liq if l.get("kind","").endswith("_liq")]
    if rs: liq_side="buyside" if rs[-1]["kind"]=="buyside_liq" else "sellside"

    # Detect best setup
    setup=_detect_setups(candles,bias,active_obs,active_fvg,br,liq,price,atr,oflow,pd)

    # MTF alignment bonus
    mtf_align = (htf_bias==bias and htf_bias is not None)
    if setup and mtf_align: setup["score"]+=12; setup["probability"]=min(95,setup["probability"]+7)
    if setup and news_blocked: setup["probability"]=max(30,setup["probability"]-25); setup["news_block"]=True

    direction = setup["direction"] if setup else "neutral"
    conf = min(100, int(setup["score"]) if setup else 0)
    rr = 0.0
    entry=sl=tp=None; entry_zone=None; tp1=tp2=tp3=None; inv=None; setup_name_fa=None
    if setup:
        entry=setup["entry"]; sl=setup["sl"]; tp=setup["tp2"]
        tp1=setup["tp1"]; tp2=setup["tp2"]; tp3=setup["tp3"]; inv=setup["invalidation"]
        entry_zone={"high":setup["entry_high"],"low":setup["entry_low"]}
        rr=(abs((tp2-entry)/(entry-sl))) if entry and sl and entry!=sl else 0
        setup_name_fa=SETUP_TYPES.get(setup["type"],{}).get("name_fa",setup["type"])
        if rr<1: direction="neutral"  # too risky

    # Build zones
    zones=[]
    for k in kz_comp:
        zones.append({"kind":"KZ","side":"high","index":k["start"],"top":vis_hi,"bottom":vis_lo,"full_height":True,
                      "name":k["name"],"start_idx":k["start"],"end_idx":k["end"]})
    for o in active_obs[-6:]:
        zones.append({"kind":"OB","side":o["kind"],"index":o["index"],"top":o["top"],"bottom":o["bottom"],"full_height":False})
    for g in active_fvg[-6:]:
        tag="FVG" if not g.get("inverse") else "iFVG"
        zones.append({"kind":tag,"side":g["kind"],"index":g["index"],"top":g["top"],"bottom":g["bottom"],"full_height":False,"size_pct":g.get("size_pct",0)})
    for b in br[-4:]:
        zones.append({"kind":"BRK","side":b["kind"],"index":b["index"],"top":b["top"],"bottom":b["bottom"],"full_height":False})

    # Trade plan lines (entry/sl/tp) added as overlay lines on chart
    plan_lines=[]
    if entry: plan_lines.append({"kind":"entry","price":entry})
    if sl:    plan_lines.append({"kind":"sl","price":sl})
    if tp1:   plan_lines.append({"kind":"tp1","price":tp1})
    if tp2:   plan_lines.append({"kind":"tp2","price":tp2})
    if tp3:   plan_lines.append({"kind":"tp3","price":tp3})

    labels=[]
    for ev in events[-12:]: labels.append({"kind":ev["type"],"dir":ev["direction"],"index":ev["index"],"price":ev["price"]})
    for l in liq[-8:]: labels.append({"kind":"LIQ","dir":l["kind"],"index":l.get("sweep",l["index"]),"price":l["price"]})

    lines=[]
    if bh is not None: lines.append({"kind":"high","price":bh})
    if bl is not None: lines.append({"kind":"low","price":bl})
    for l in liq[-6:]:
        if l["kind"] in ("eqh","eql","recent_high_liq","recent_low_liq"):
            lines.append({"kind":l["kind"],"price":l["price"]})
    lines += plan_lines

    note="روند خنثی — منتظر تایید"
    if direction=="long" and (setup.get("probability") or 0)>=70: note="ستاپ خرید معتبر ◀"+setup_name_fa
    elif direction=="short" and (setup.get("probability") or 0)>=70: note="ستاپ فروش معتبر ◀"+setup_name_fa
    elif direction!="neutral": note="ناحیه زیر نظر — "+(setup_name_fa or "-")
    elif bias=="bullish": note="روند صعودی، منتظر پولبک به OB"
    elif bias=="bearish": note="روند نزولی، منتظر پولبک به OB"

    ai=_narrative({"type":setup.get("type"),"name_fa":setup_name_fa} if setup else None,
                  bias,direction,conf,setup.get("probability",0) if setup else 0,oflow,session_names,liq_side,pd,rr,news_blocked)

    return {
        "symbol":symbol,"timeframe":timeframe,"market":"","price":price,"bias":bias,"direction":direction,
        "confluence":conf,"probability":setup.get("probability",0) if setup else 0,
        "setup_type":setup_name_fa or "-","rr":round(rr,2),"atr":atr,"note":note,"status":"ok",
        "levels":{"entry":entry,"sl":sl,"tp":tp},"tp1":tp1,"tp2":tp2,"tp3":tp3,"invalidation":inv,
        "entry_zone":entry_zone,"plan_lines":plan_lines,
        "premium_zone":pd,"mtf_aligned":mtf_align,"htf_bias":htf_bias,
        "news_blocked":news_blocked,"volume_spike":oflow.get("volume_spike",False),
        "events":[{"kind":e["type"],"dir":e["direction"],"index":e["index"],"price":e["price"]} for e in events[-10:]],
        "order_blocks":[{"kind":o["kind"],"top":o["top"],"bottom":o["bottom"],"index":o["index"]} for o in active_obs[-6:]],
        "fvg":[{"kind":g["kind"],"top":g["top"],"bottom":g["bottom"],"index":g["index"],"inverse":g.get("inverse",False),"size_pct":g.get("size_pct",0)} for g in active_fvg[-6:]],
        "breakers":[{"kind":b["kind"],"top":b["top"],"bottom":b["bottom"],"index":b["index"]} for b in br[-4:]],
        "inducements":[{"kind":l["kind"],"price":l["price"],"index":l.get("sweep",l["index"])} for l in liq if "sweep" in l or l["kind"] in ("eqh","eql")],
        "sessions":session_names,"killzones":[{"kind":"KZ","name":k["name"],"side":"high","start_idx":k["start"],"end_idx":k["end"],
                                              "index":k["start"],"top":vis_hi,"bottom":vis_lo} for k in kz_comp],
        "orderflow":oflow,"ai":ai,
        "visible_range":{"low":vis_lo,"high":vis_hi},
        "overlay":{"lines":lines,"zones":zones,"labels":labels},
        "candles_count":len(candles),"created_by":"Amin Omidi"
    }


def _empty(symbol,tf,count):
    return {"symbol":symbol,"timeframe":tf,"price":0,"bias":"neutral","direction":"neutral","confluence":0,"probability":0,
            "setup_type":"-","rr":0,"atr":0,"note":"حداقل ۳۰ کندل لازم است.","status":"insufficient_data",
            "levels":{"entry":None,"sl":None,"tp":None},"tp1":None,"tp2":None,"tp3":None,"invalidation":None,
            "entry_zone":None,"plan_lines":[],"premium_zone":"eq","mtf_aligned":False,"htf_bias":None,
            "news_blocked":False,"volume_spike":False,
            "events":[],"order_blocks":[],"fvg":[],"breakers":[],"inducements":[],"sessions":[],"killzones":[],
            "orderflow":{"delta":0,"pressure":"neutral","cvd_curve":[],"volume_spike":False},
            "ai":{"side":"انتظار","trend":"خنثی","summary":"داده کافی نیست.","recommendation":"منتظر بمانید","confluence":0,"probability":0,"rr":0,"verdict":"-","setup_type":"-"}
            ,"visible_range":{"low":0,"high":0},"atr":0,"market":"",
            "overlay":{"lines":[],"zones":[],"labels":[]},"candles_count":count,"created_by":"Amin Omidi"}


def detect_smc_features(candles,trend="neutral"):
    r=analyze(candles)
    return {"bias":r.get("bias","neutral"),"bos":[e for e in r.get("events",[]) if e.get("kind")=="BOS"],
            "choch":[e for e in r.get("events",[]) if e.get("kind")=="CHoCH"],
            "order_blocks":r.get("order_blocks",[]),"fvg":r.get("fvg",[]),"liquidity_sweeps":r.get("inducements",[]),
            "active_ob":None,"entry":(r.get("levels") or {}).get("entry"),"sl":(r.get("levels") or {}).get("sl"),
            "tp":(r.get("levels") or {}).get("tp"),"confluence":r.get("confluence",0),"direction":r.get("direction","neutral")}
