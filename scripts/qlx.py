#!/usr/bin/env python3
import argparse, sys, json, os

# local imports
from qlx_hfp_prototype import (
    assemble_hfp,
    derive_key_from_hfp,
    derive_key_scrypt,
)
try:
    from qlx_hfp_prototype import derive_key_argon2id, HAVE_ARGON2
except Exception:
    HAVE_ARGON2 = False

from qlx_photonic_control import (
    photonic_map,
    make_envelope,
    sign_envelope_hmac,
    canonical_json,
)

# optional STS
try:
    from qlx_sts_min import default_stream, stream_to_bits, run_suite
    HAVE_STS = True
except Exception:
    HAVE_STS = False

def cmd_hfp(args):
    hfp = assemble_hfp(args.seed, levels=args.levels)
    if args.json_out:
        print(json.dumps(hfp, indent=2))
    else:
        print(hfp["fingerprint_hash"])

def cmd_key(args):
    hfp = assemble_hfp(args.seed, levels=args.levels)
    pw = args.pw.encode()
    if args.kdf == "hkdf":
        key = derive_key_from_hfp(pw, hfp["fingerprint_hash"], key_len=args.length)
    elif args.kdf == "scrypt":
        key = derive_key_scrypt(pw, hfp["fingerprint_hash"], key_len=args.length)
    elif args.kdf == "argon2id":
        if not HAVE_ARGON2:
            print("argon2id not available - install argon2-cffi", file=sys.stderr)
            sys.exit(2)
        key = derive_key_argon2id(
            pw, hfp["fingerprint_hash"], key_len=args.length,
            time_cost=args.time_cost, memory_cost_kib=args.memory_kib, parallelism=args.parallelism
        )
    else:
        print("unknown kdf", file=sys.stderr); sys.exit(2)
    print(key.hex())

def cmd_export(args):
    hfp = assemble_hfp(args.seed, levels=args.levels)
    params = photonic_map(hfp["band_stats"])
    env = make_envelope(hfp, params, dac_bits=args.dac_bits, sample_rate_GSa=args.sample_gsa, quant_mode=args.quant)
    if args.sig_alg == "hmac":
        signed = sign_envelope_hmac(env, key=args.key.encode(), key_id=args.key_id)
    else:
        if not args.ed25519-priv-hex:
            raise SystemExit("ed25519 requires --ed25519-priv-hex or ED25519_PRIV_HEX")
        from qlx_photonic_control import sign_envelope_ed25519
        signed = sign_envelope_ed25519(env, priv_hex=(args.ed25519-priv-hex or os.environ.get("ED25519_PRIV_HEX","")), key_id=args.key_id)

    out = args.out
    os.makedirs(out, exist_ok=True)
    core_keys = ["version","wavelet_basis","levels","seed_harmonics","phi","chaos","mixer","band_stats"]
    core = {k: hfp[k] for k in core_keys}
    open(os.path.join(out, "hfp_core.json"), "wb").write(canonical_json(core))
    open(os.path.join(out, "hfp_full.json"), "wb").write(canonical_json(hfp))
    open(os.path.join(out, "photonic_env_signed.json"), "wb").write(canonical_json(signed))
    print("wrote:", os.path.join(out, "hfp_core.json"))
    print("wrote:", os.path.join(out, "hfp_full.json"))
    print("wrote:", os.path.join(out, "photonic_env_signed.json"))

def cmd_sts(args):
    if not HAVE_STS:
        print("STS not available - ensure qlx_sts_min.py is in PYTHONPATH", file=sys.stderr)
        sys.exit(2)
    if args.whiten == "sha512":
        chunk_in, chunk_out = 4096, 512
        need_chunks = (args.n_bits + chunk_out - 1)//chunk_out
        n = need_chunks*chunk_in
    else:
        n = args.n_bits
    stream = default_stream(args.seed, n=n)
    bits = stream_to_bits(stream, whiten=args.whiten)[:args.n_bits]
    report = run_suite(bits, alpha=args.alpha, block_M=args.block)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["summary"]["all_pass"] else 2)

def main():
    p = argparse.ArgumentParser(prog="qlx")
    sub = p.add_subparsers(dest="cmd", required=True)

    ph = sub.add_parser("hfp", help="print HFP fingerprint or full JSON")
    ph.add_argument("--seed", default="qlx-demo-seed-phi369")
    ph.add_argument("--levels", type=int, default=5)
    ph.add_argument("--json-out", action="store_true")
    ph.set_defaults(func=cmd_hfp)

    pk = sub.add_parser("key", help="derive a key using hkdf, scrypt, or argon2id")
    pk.add_argument("--seed", default="qlx-demo-seed-phi369")
    pk.add_argument("--levels", type=int, default=5)
    pk.add_argument("--pw", default="demo-password")
    pk.add_argument("--length", type=int, default=32)
    pk.add_argument("--kdf", choices=["hkdf","scrypt","argon2id"], default="argon2id")
    pk.add_argument("--time-cost", type=int, default=2)
    pk.add_argument("--memory-kib", type=int, default=65536)  # 64 MiB
    pk.add_argument("--parallelism", type=int, default=1)
    pk.set_defaults(func=cmd_key)

    pe = sub.add_parser("export", help="write HFP and signed photonic envelope")
    pe.add_argument("--sig-alg", choices=["hmac","ed25519"], default="hmac")
    pe.add_argument("--ed25519-priv-hex", default="")
    pe.add_argument("--ed25519-key-id", default="ctrl-ed25519")
    pe.add_argument("--seed", default="qlx-demo-seed-phi369")
    pe.add_argument("--levels", type=int, default=5)
    pe.add_argument("--dac-bits", type=int, default=14)
    pe.add_argument("--sample-gsa", type=int, default=64)
    pe.add_argument("--quant", choices=["nearest","floor","stochastic"], default="nearest")
    pe.add_argument("--key", default="test-key")
    pe.add_argument("--key-id", default="ctrl-01")
    pe.add_argument("--out", default="artifacts")
    pe.set_defaults(func=cmd_export)

    ps = sub.add_parser("sts", help="run the mini STS battery")
    ps.add_argument("--seed", default="qlx-demo-seed-phi369")
    ps.add_argument("--n-bits", type=int, default=200000)
    ps.add_argument("--alpha", type=float, default=0.01)
    ps.add_argument("--block", type=int, default=256)
    ps.add_argument("--whiten", choices=["none","vn","sha512"], default="sha512")
    ps.set_defaults(func=cmd_sts)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
