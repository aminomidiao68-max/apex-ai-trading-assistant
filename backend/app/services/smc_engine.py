"""Apex AI — SMC engine (BOS, CHoCH, OB, FVG, Breaker, Inducement).
Created by Amin Omidi"""
from __future__ import annotations
from typing import Any, List, Dict

def _candles(raw):
    out=[]
    for c in (raw or []):
        if isinstance(c,dict):
            try:
                out.append({"t":float(c.get("t",c.get("time",0))),"o":float(c.get("o",c.get("open",0))),"h":float(c.get("h",c.get("high",0))),"l":float(c.get("l",c.get("low",0))),"c":float(c.get("c",c.get("close",0))),"v":float(c.get("v",c.get("volume",0)))})
            except Exception: pass
    out.sort(key=lambda x:x["t"])
    return out

def _swings(candles, left=2, right=2):
    highs=[]; lows=[]; n=len(candles)
    for i in range(left, n-right):
        h=candles[i]["h"]; l=candles[i]["l"]
        if all(h>candles[i-k]["h"] for k in range(1,left+1)) and all(h>candles[i+k]["h"] for k in range(1,right+1)):
            highs.append((i,h))
        if all(l<candles[i-k]["l"] for k in range(1,left+1)) and all(l<candles[i+k]["l"] for k in range(1,right+1)):
            lows.append((i,l))
    return highs,lows

def _structure(highs,lows,candles):
    events=[]
    if not highs or not lows:
        return events,"neutral",None,None
    bos_hh=max(p for _,p in highs); bos_ll=min(p for _,p in lows)
    trend="bullish" if highs[0][0]>lows[0][0] else "bearish"
    for i,c in enumerate(candles):
        h=c["h"]; l=c["l"]
        if trend=="bullish":
            if l<bos_ll:
                events.append({"type":"CHoCH","index":i,"price":l,"direction":"bearish"}); trend="bearish"; bos_ll=l
            elif h>bos_hh:
                events.append({"type":"BOS","index":i,"price":h,"direction":"bullish"}); bos_hh=h
        else:
            if h>bos_hh:
                events.append({"type":"CHoCH","index":i,"price":h,"direction":"bullish"}); trend="bullish"; bos_hh=h
            elif l<bos_ll:
                events.append({"type":"BOS","index":i,"price":l,"direction":"bearish"}); bos_ll=l
    return events,trend,bos_hh,bos_ll

def _fvg(candles):
    out=[]
    for i in range(len(candles)-2):
        a,b,c0=candles[i],candles[i+1],candles[i+2]
        if a["h"]<c0["l"]: out.append({"kind":"bullish","index":i+1,"top":c0["l"],"bottom":a["h"],"mitigated":False})
        if a["l"]>c0["h"]: out.append({"kind":"bearish","index":i+1,"top":a["l"],"bottom":c0["h"],"mitigated":False})
    for g in out:
        for j in range(g["index"]+2,len(candles)):
            cc=candles[j]
            if g["kind"]=="bullish" and cc["l"]<=g["bottom"]: g["mitigated"]=True; break
            if g["kind"]=="bearish" and cc["h"]>=g["top"]: g["mitigated"]=True; break
    return out

def _obs(candles,events):
    obs=[]
    for ev in events:
        if ev["type"] not in ("BOS","CHoCH"): continue
        i=ev["index"]; d=ev["direction"]; found=None
        for k in range(i-1,max(0,i-20),-1):
            c=candles[k]; bull=c["c"]>c["o"]
            if d=="bullish" and not bull: found=k; break
            if d=="bearish" and bull: found=k; break
        if found is None: continue
        oc=candles[found]
        obs.append({"kind":d,"index":found,"top":oc["h"],"bottom":oc["l"],"mitigated":False})
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

def _induce(candles,highs,lows):
    out=[]
    for si,sp in highs:
        for j in range(si+1,min(si+6,len(candles))):
            if candles[j]["h"]>sp and candles[j]["c"]<sp:
                out.append({"kind":"sellside_liq","index":si,"price":sp,"sweep":j}); break
    for si,sp in lows:
        for j in range(si+1,min(si+6,len(candles))):
            if candles[j]["l"]<sp and candles[j]["c"]>sp:
                out.append({"kind":"buyside_liq","index":si,"price":sp,"sweep":j}); break
    return out

def analyze(candles_raw,symbol="",timeframe=""):
    candles=_candles(candles_raw)
    if len(candles)<30:
        return {"symbol":symbol,"timeframe":timeframe,"bias":"neutral","status":"insufficient_data","need_candles":30,"events":[],"order_blocks":[],"fvg":[],"breakers":[],"inducements":[],"levels":{},"direction":"neutral","confluence":0,"note":"حداقل ۳۰ کندل لازم است.","overlay":{"lines":[],"zones":[],"labels":[]},"created_by":"Amin Omidi"}
    highs,lows=_swings(candles)
    events,bias,bh,bl=_structure(highs,lows,candles)
    fvgs=_fvg(candles); obs=_obs(candles,events); br=_breakers(candles,obs); ind=_induce(candles,highs,lows)
    price=candles[-1]["c"]
    active_obs=[o for o in obs if not o["mitigated"]]
    active_fvg=[g for g in fvgs if not g["mitigated"]]
    entry=sl=tp=None; direction="neutral"; conf=0
    if bias=="bullish":
        cands=[o for o in active_obs if o["kind"]=="bullish" and o["top"]<price]
        cands += [b for b in br if b["kind"]=="bullish" and b["top"]<price]
        if cands:
            z=max(cands,key=lambda x:x["top"]); entry=z["top"]; sl=z["bottom"]-0.0003*z["bottom"]; tp=price+(price-sl)*2; direction="long"; conf+=2
        if any(g["kind"]=="bullish" and g["bottom"]<price<g["top"]*1.01 for g in active_fvg): conf+=1
    elif bias=="bearish":
        cands=[o for o in active_obs if o["kind"]=="bearish" and o["bottom"]>price]
        cands += [b for b in br if b["kind"]=="bearish" and b["bottom"]>price]
        if cands:
            z=min(cands,key=lambda x:x["bottom"]); entry=z["bottom"]; sl=z["top"]+0.0003*z["top"]; tp=price-(sl-price)*2; direction="short"; conf+=2
        if any(g["kind"]=="bearish" and g["top"]>price>g["bottom"]*0.99 for g in active_fvg): conf+=1
    zones=[]
    for o in active_obs[-10:]: zones.append({"kind":"OB","side":o["kind"],"index":o["index"],"top":o["top"],"bottom":o["bottom"]})
    for g in active_fvg[-10:]: zones.append({"kind":"FVG","side":g["kind"],"index":g["index"],"top":g["top"],"bottom":g["bottom"]})
    for b in br[-5:]: zones.append({"kind":"BRK","side":b["kind"],"index":b["index"],"top":b["top"],"bottom":b["bottom"]})
    labels=[]
    for ev in events[-20:]: labels.append({"kind":ev["type"],"dir":ev["direction"],"index":ev["index"],"price":ev["price"]})
    for i2 in ind[-10:]: labels.append({"kind":"LIQ","dir":i2["kind"],"index":i2["sweep"],"price":i2["price"]})
    lines=[]
    if bh is not None: lines.append({"kind":"high","price":bh})
    if bl is not None: lines.append({"kind":"low","price":bl})
    note="روند خنثی — منتظر تایید"
    if direction=="long" and conf>=2: note="ناحیه لانگ بالقوه با تایید روند"
    if direction=="short" and conf>=2: note="ناحیه شورت بالقوه با تایید روند"
    if bias=="bullish" and not entry: note="روند صعودی، منتظر پولبک به OB"
    if bias=="bearish" and not entry: note="روند نزولی، منتظر پولبک به OB"
    return {"symbol":symbol,"timeframe":timeframe,"price":price,"bias":bias,"direction":direction,"confluence":conf,"note":note,"levels":{"entry":entry,"sl":sl,"tp":tp},"events":[{"kind":e["type"],"dir":e["direction"],"index":e["index"],"price":e["price"]} for e in events[-10:]],"order_blocks":[{"kind":o["kind"],"top":o["top"],"bottom":o["bottom"],"index":o["index"]} for o in active_obs[-8:]],"fvg":[{"kind":g["kind"],"top":g["top"],"bottom":g["bottom"],"index":g["index"]} for g in active_fvg[-8:]],"breakers":[{"kind":b["kind"],"top":b["top"],"bottom":b["bottom"],"index":b["index"]} for b in br[-5:]],"inducements":[{"kind":i["kind"],"price":i["price"],"index":i["sweep"]} for i in ind[-8:]],"overlay":{"lines":lines,"zones":zones,"labels":labels},"candles_count":len(candles),"created_by":"Amin Omidi"}

def detect_smc_features(candles, trend="neutral"):
    """Backward-compat wrapper used by signal_engine.
    Returns a dict shaped like the old API expected."""
    r = analyze(candles)
    obs = r.get("order_blocks", [])
    fvgs = r.get("fvg", [])
    liq = r.get("inducements", [])
    bos = [e for e in r.get("events", []) if e.get("kind") == "BOS"]
    choch = [e for e in r.get("events", []) if e.get("kind") == "CHoCH"]
    return {
        "bias": r.get("bias", "neutral"),
        "bos": bos,
        "choch": choch,
        "order_blocks": obs,
        "fvg": fvgs,
        "liquidity_sweeps": liq,
        "active_ob": None,
        "entry": (r.get("levels") or {}).get("entry"),
        "sl": (r.get("levels") or {}).get("sl"),
        "tp": (r.get("levels") or {}).get("tp"),
    }
