import os, urllib.request, json, time, sys
key = os.environ.get("RENDER_KEY", "")
svc = os.environ.get("SERVICE_ID", "srv-d92g1msm0tmc73e3703g")
if not key:
    print("RENDER_KEY not set")
    sys.exit(1)
hdrs = {"Authorization": "Bearer " + key}
print("1) last 4 deploys:")
req = urllib.request.Request("https://api.render.com/v1/services/" + svc + "/deploys?limit=4", headers=hdrs)
data = json.loads(urllib.request.urlopen(req, timeout=20).read())
for d in data:
    dep = d.get("deploy", d)
    c = dep.get("commit", {})
    print("  ", dep.get("id","")[:22], "|", dep.get("status","?"), "|", c.get("id","")[:8], "|", c.get("message","")[:40])

print("\n2) triggering new deploy...")
req2 = urllib.request.Request(
    "https://api.render.com/v1/services/" + svc + "/deploys",
    data=b"{}", method="POST",
    headers={**hdrs, "Content-Type": "application/json"}
)
new = json.loads(urllib.request.urlopen(req2, timeout=20).read())
print("   deploy id:", new.get("id"), "status:", new.get("status"))

print("\n3) waiting up to 3 minutes for live...")
live = False
for _ in range(36):
    time.sleep(5)
    try:
        r = urllib.request.urlopen(
            "https://api.render.com/v1/services/" + svc + "/deploys?limit=1",
            headers=hdrs, timeout=10
        )
        ds = json.loads(r.read())
        latest = ds[0].get("deploy", ds[0])
        st = latest.get("status")
        print("   ...", st)
        if st == "live":
            live = True
            break
        if st in ("build_failed", "update_failed", "canceled"):
            print("X deploy failed:", st)
            break
    except Exception as e:
        print("   poll err:", e)

if not live:
    print("\n! deploy still not live")
else:
    print("\n4) testing /api/v1/news/health ...")
    try:
        r2 = urllib.request.urlopen("https://apex-ai-trading-assistant.onrender.com/api/v1/news/health", timeout=20)
        print("V HTTP", r2.status, "->", r2.read().decode()[:300])
    except Exception as e:
        print("X endpoint fail:", e)
