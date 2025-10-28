import argparse
#!/usr/bin/env python3
import json, sys, math, pathlib, os
from jsonschema import validate, ValidationError
from qlx_photonic_control import verify_envelope_ed25519

SCHEMA_PATH = pathlib.Path("schemas/qlx_photonic_control.schema.json")
OUT_DIR = pathlib.Path("artifacts")
OUT_DIR.mkdir(exist_ok=True)

def open_interval_ok(vals, lo, hi, bits):
    if not vals:
        return False
    eps = (hi - lo) / ((1<<bits) - 1)
    return min(vals) >= lo + eps and max(vals) <= hi - eps

def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("env_path", nargs="?", default="artifacts/photonic_env_signed.json")
    ap.add_argument("--ed25519-pub-hex", default=os.environ.get("ED25519_PUB_HEX",""))
    args = ap.parse_args()
    env_path = pathlib.Path(args.env_path)

    env = json.loads(env_path.read_text())
    schema = json.loads(SCHEMA_PATH.read_text())
    ok = True
    errors = []
    try:
        validate(env, schema)
    except ValidationError as e:
        ok = False
        errors.append(f"schema: {e.message}")

    # band length checks
    L = env.get("band_count", 0)
    for k in ["I_bias_mA","phi_rad","kappa","tau_ps","delta_f_GHz","alpha"]:
        arr = env["params"].get(k, [])
        if len(arr) != L:
            ok = False
            errors.append(f"length: {k} has {len(arr)} != band_count {L}")

    # range checks - open interval by 1 LSB
    bits = int(env.get("dac",{}).get("width_bits", 14))
    ranges = {
        "I_bias_mA": (15.0, 50.0),
        "phi_rad": (0.0, math.pi),
        "kappa": (0.05, 0.90),
        "tau_ps": (50.0, 300.0),
        "delta_f_GHz": (-10.0, 10.0),
        "alpha": (2.0, 6.0)
    }
    for k,(lo,hi) in ranges.items():
        if not open_interval_ok(env["params"][k], lo, hi, bits):
            ok = False
            errors.append(f"range: {k} not strictly inside ({lo},{hi})")

    # optional Ed25519 verify
    alg = env.get("signing",{}).get("alg","")
    if alg == "Ed25519":
        pub_hex = args.ed25519_pub_hex
        if not pub_hex:
            ok = False; errors.append("sign: missing --ed25519-pub-hex for Ed25519 verify")
        else:
            try:
                if not verify_envelope_ed25519(env, pub_hex):
                    ok = False; errors.append("sign: Ed25519 verify returned False")
            except Exception as e:
                ok = False; errors.append(f"sign: Ed25519 verify error: {e}")

    report = {"ok": ok, "errors": errors}
    (OUT_DIR/"env_validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    sys.exit(0 if ok else 2)

if __name__ == "__main__":
    main()
