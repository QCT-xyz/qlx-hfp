#!/usr/bin/env python3
import sys, json, argparse, os, traceback
from pathlib import Path
from qlx_hfp_prototype import assemble_hfp
from qlx_photonic_control import photonic_map, make_envelope, sign_envelope_hmac, canonical_json

def main():
    try:
        print("[export] start", flush=True)
        ap = argparse.ArgumentParser()
        ap.add_argument("--seed", type=str, default=os.environ.get("QLX_SEED", "qlx-demo-seed-phi369"))
        ap.add_argument("--dac-bits", type=int, default=14)
        ap.add_argument("--sample-gsa", type=int, default=64)
        ap.add_argument("--key", type=str, default="test-key")
        args = ap.parse_args()

        out = Path("artifacts"); out.mkdir(exist_ok=True)
        print(f"[export] writing to {out.resolve()}", flush=True)

        hfp = assemble_hfp(args.seed, levels=5)
        print(f"[export] fingerprint: {hfp["fingerprint_hash"][:48]}...", flush=True)

        core_keys = ["version","wavelet_basis","levels","seed_harmonics","phi","chaos","mixer","band_stats"]
        hfp_core = {k: hfp[k] for k in core_keys}
        hfp_full = dict(hfp)

        params = photonic_map(hfp["band_stats"])
        env = make_envelope(hfp, params, dac_bits=args.dac_bits, sample_rate_GSa=args.sample_gsa)
        signed = sign_envelope_hmac(env, key=args.key.encode(), key_id="ctrl-01")

        (out / "hfp_core.json").write_bytes(canonical_json(hfp_core))
        print("[export] wrote hfp_core.json", flush=True)
        (out / "hfp_full.json").write_bytes(canonical_json(hfp_full))
        print("[export] wrote hfp_full.json", flush=True)
        (out / "photonic_env_signed.json").write_bytes(canonical_json(signed))
        print("[export] wrote photonic_env_signed.json", flush=True)

        print("[export] done", flush=True)
        return 0
    except Exception:
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())
