#!/usr/bin/env python3
import json, pathlib, sys

ART = pathlib.Path("artifacts")
sha_p = ART / "sts_sha512.json"
vn_p  = ART / "sts_vn.json"
none_p = ART / "sts_none.json"

def load(p):
    if p.exists():
        with open(p) as f: return json.load(f)
    return {"summary":{"all_pass":None,"min_p":None}}

sha = load(sha_p)["summary"]
vn  = load(vn_p)["summary"]
nne = load(none_p)["summary"]

summary = {"sha512": sha, "vn": vn, "none": nne}
with open(ART / "sts_summary.json", "w") as f:
    json.dump(summary, f, indent=2)

html = f"""
<!doctype html><meta charset="utf-8"><title>STS Summary</title>
<h2>STS Summary</h2>
<table border="1" cellpadding="6" cellspacing="0">
<tr><th>whitener</th><th>all_pass</th><th>min_p</th></tr>
<tr><td>sha512</td><td>{sha["all_pass"]}</td><td>{sha["min_p"]}</td></tr>
<tr><td>vn</td><td>{vn["all_pass"]}</td><td>{vn["min_p"]}</td></tr>
<tr><td>none (monitor)</td><td>{nne["all_pass"]}</td><td>{nne["min_p"]}</td></tr>
</table>
"""
(ART / "sts_summary.html").write_text(html)
print("wrote:", ART / "sts_summary.json")
print("wrote:", ART / "sts_summary.html")
