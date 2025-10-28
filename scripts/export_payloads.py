#!/usr/bin/env python3
import json, argparse, os
from pathlib import Path
from qlx_hfp_prototype import assemble_hfp
from qlx_photonic_control import (
    photonic_map, make_envelope,
    sign_envelope_hmac, sign_envelope_ed25519,
    canonical_json,
)

def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=str, default=os.environ.get("QLX_SEED", "qlx-demo-seed-phi369"))
    ap.add_argument("--levels", type=int, default=5)
    ap.add_argument("--dac-bits", type=int, default=14)
    ap.add_argument("--sample-gsa", type=int, default=64)
    ap.add_argument("--quant", choices=["nearest","floor","stochastic"], default="nearest")
    ap.add_argument("--out", type=str, default="artifacts")

    # signing options
    ap.add_argument("--sig-alg", choices=["hmac","ed25519"], default="hmac")
    ap.add_argument("--key", type=str, default="test-key")  # HMAC
    ap.add_argument("--ed25519-priv-hex", type=str, default=os.environ.get("ED25519_PRIV_HEX",""))
    ap.add_argument("--ed25519-key-id", type=str, default="ctrl-ed25519")
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(exist_ok=True)

    # build HFP and envelope
    hfp = assemble_hfp(args.seed, levels=args.levels)
    params = photonic_map(hfp["band_stats"])
    env = make_envelope(hfp, params, dac_bits=args.dac_bits, sample_rate_GSa=args.sample_gsa, quant_mode=args.quant)

    # sign
    if args.sig_alg == "hmac":
        signed = sign_envelope_hmac(env, key=args.key.encode(), key_id="ctrl-01")
    else:
        if not args.ed25519_priv_hex:
            raise SystemExit("ed25519 requires --ed25519-priv-hex or ED25519_PRIV_HEX")
        signed = sign_envelope_ed25519(env, priv_hex=args.ed25519_priv_hex, key_id=args.ed25519_key_id)

    # write artifacts (canonical)
    core_keys = ["version","wavelet_basis","levels","seed_harmonics","phi","chaos","mixer","band_stats"]
    (out/"hfp_core.json").write_bytes(canonical({k: hfp[k] for k in core_keys}))
    (out/"hfp_full.json").write_bytes(canonical(hfp))
    (out/"photonic_env_signed.json").write_bytes(canonical(signed))

    print("wrote:", out/"hfp_core.json")
    print("wrote:", out/"hfp_full.json")
    print("wrote:", out/"photonic_env_signed.json")

if __name__ == "__main__":
    main()
