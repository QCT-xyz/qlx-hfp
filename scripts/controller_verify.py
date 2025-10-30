#!/usr/bin/env python3
import os, sys, json, argparse, hmac, hashlib

# optional import for Ed25519 verify; requires PYTHONPATH=src
try:
    from qlx_photonic_control import verify_envelope_ed25519
except Exception:
    verify_envelope_ed25519 = None

BOUNDS = {
    "I_bias_mA":  (15.0, 50.0),
    "phi_rad":    (0.0, 3.1415926535),
    "kappa":      (0.05, 0.90),
    "tau_ps":     (50.0, 300.0),
    "delta_f_GHz":(-10.0, 10.0),
    "alpha":      (2.0, 6.0),
}

def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def open_interval_ok(vals, lo, hi, bits):
    if not vals:
        return False
    eps = (hi - lo) / ((1<<bits) - 1)
    tol = max(1e-12, eps*1e-6)
    mn = min(vals); mx = max(vals)
    return (mn >= lo + eps - tol) and (mx <= hi - eps + tol)


def verify_ed25519(env, pub_hex):
    if verify_envelope_ed25519 is None:
        return False, "Ed25519 verifier unavailable (set PYTHONPATH=src or install deps)"
    try:
        ok = verify_envelope_ed25519(env, pub_hex)
        return bool(ok), None if ok else "Ed25519 verify returned False"
    except Exception as e:
        return False, f"Ed25519 verify error: {e}"
def verify_hmac(env, key_hex):
    try:
        env2 = dict(env); signing = env2.pop("signing", {})
        sig_hex = signing.get("sig", "")
        if not sig_hex: return False, "missing HMAC signature"
        key = bytes.fromhex(key_hex)
        mac = hmac.new(key, canonical_json(env2), hashlib.sha256).hexdigest()
        return (mac == sig_hex), None if mac == sig_hex else "HMAC mismatch"
    except Exception as e:
        return False, f"HMAC verify error: {e}"

def main():
    ap = argparse.ArgumentParser(description="Controller-side envelope verifier")
    ap.add_argument("envelope_path", help="Path to photonic_env_signed.json")
    ap.add_argument("--ed25519-pub-hex", default="", help="Hex public key for Ed25519 verify (optional)")
    ap.add_argument("--hmac-key-hex", default="", help="Hex key for HMAC-SHA256 verify (optional)")
    args = ap.parse_args()

    report = {"ok": False, "errors": [], "checks": {}}

    try:
        env = json.loads(open(args.envelope_path).read())
    except Exception as e:
        print(json.dumps({"ok": False, "errors": [f"load error: {e}"]}, indent=2)); sys.exit(2)

    # basic fields
    for k in ["band_count","params","dac"]:
        if k not in env:
            report["errors"].append(f"missing field: {k}")

    if report["errors"]:
        print(json.dumps(report, indent=2)); sys.exit(2)

    L = int(env.get("band_count", 0))
    params = env["params"]
    dac_bits = int(env["dac"].get("width_bits", 14))

    # length check
    lengths_ok = True
    for k in BOUNDS.keys():
        arr = params.get(k, [])
        if len(arr) != L:
            lengths_ok = False
            report["errors"].append(f"length: {k} has {len(arr)} != band_count {L}")
    report["checks"]["lengths_ok"] = lengths_ok

    # range (open interval by 1 LSB) check
    ranges_ok = True
    for k,(lo,hi) in BOUNDS.items():
        arr = params.get(k, [])
        ok = open_interval_ok(arr, lo, hi, dac_bits)
        if not ok:
            ranges_ok = False
            report["errors"].append(f"range: {k} not in ({lo},{hi}) open by 1 LSB")
    report["checks"]["ranges_ok"] = ranges_ok

    # signature check (optional)
    sign = env.get("signing", {})
    alg  = sign.get("alg","").upper()
    sig_ok = None
    sig_err = None

    if alg == "ED25519":
        if args.ed25519_pub_hex:
            sig_ok, sig_err = verify_ed25519(env, args.ed25519_pub_hex)
        else:
            sig_ok, sig_err = None, "pub key not provided; signature check skipped"
    elif alg in ("HMAC-SHA256","HMAC_SHA256","HMAC"):
        if args.hmac_key_hex:
            sig_ok, sig_err = verify_hmac(env, args.hmac_key_hex)
        else:
            sig_ok, sig_err = None, "HMAC key not provided; signature check skipped"
    else:
        sig_ok, sig_err = None, "unknown or missing signing.alg; signature check skipped"

    report["checks"]["sig_alg"] = alg
    report["checks"]["sig_ok"]  = sig_ok
    if sig_err: report["errors"].append(f"sign: {sig_err}")

    # overall
    ok = lengths_ok and ranges_ok and (sig_ok in (True, None))
    report["ok"] = ok

    print(json.dumps(report, indent=2))
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
