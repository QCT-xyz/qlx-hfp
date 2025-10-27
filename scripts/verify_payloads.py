#!/usr/bin/env python3
import json, hmac, hashlib, sys
from pathlib import Path
from qlx_photonic_control import canonical_json

ART = Path("artifacts")
core_p  = ART / "hfp_core.json"
full_p  = ART / "hfp_full.json"
env_p   = ART / "photonic_env_signed.json"

def load(p): return json.loads(p.read_text())

def main():
    # 1) fingerprint determinism
    core = load(core_p)
    full = load(full_p)
    fp = hashlib.sha512(canonical_json(core)).hexdigest()
    fp_ok = (fp == full["fingerprint_hash"])

    # 2) photonic envelope structure and HMAC
    env = load(env_p)
    sig = env.get("signing", {}).get("sig", "")
    key_id = env.get("signing", {}).get("key_id", "")
    # remove signing to recreate signed message
    bare = dict(env)
    bare.pop("signing", None)
    mac = hmac.new(b"test-key", canonical_json(bare), hashlib.sha256).hexdigest()
    hmac_ok = (sig == mac)

    # 3) array lengths
    L = env["band_count"]
    keys = ["I_bias_mA","phi_rad","kappa","tau_ps","delta_f_GHz","alpha"]
    len_ok = all(len(env["params"][k]) == L for k in keys)

    print("fingerprint_ok:", fp_ok)
    print("hmac_ok:", hmac_ok, "key_id:", key_id)
    print("lengths_ok:", len_ok)
    print("fingerprint:", fp[:48] + "...")
    return 0 if (fp_ok and hmac_ok and len_ok) else 2

if __name__ == "__main__":
    sys.exit(main())
