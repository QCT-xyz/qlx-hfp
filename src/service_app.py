import os, json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal, Optional
from qlx_hfp_prototype import assemble_hfp, derive_key_from_hfp, derive_key_scrypt
try:
    from qlx_hfp_prototype import derive_key_argon2id, HAVE_ARGON2
except Exception:
    HAVE_ARGON2 = False
from qlx_photonic_control import photonic_map, make_envelope, sign_envelope_hmac, sign_envelope_ed25519, canonical_json
from qlx_sts_min import default_stream, stream_to_bits, run_suite

app = FastAPI(title="QLX HFP API", version="0.1.1")

def _env_int(key: str, default: int) -> int:
    try: return int(os.environ.get(key, default))
    except Exception: return default

# ---------- Schemas ----------
class HFPReq(BaseModel):
    seed: str = Field(default="qlx-demo-seed-phi369")
    levels: int = Field(default=5, ge=1, le=10)

class KeyReq(HFPReq):
    kdf: Literal["argon2id","scrypt","hkdf"] = "argon2id"
    length: int = Field(default=32, ge=16, le=64)
    time_cost: Optional[int] = None
    memory_kib: Optional[int] = None
    parallelism: Optional[int] = None
    password: str = Field(default="demo-password")

class EnvReq(HFPReq):
    dac_bits: int = Field(default=14, ge=10, le=16)
    sample_gsa: int = Field(default=64, ge=1, le=256)
    quant: Literal["nearest","floor","stochastic"] = "nearest"
    key_id: str = "ctrl-01"

class STSReq(BaseModel):
    seed: str = "qlx-demo-seed-phi369"
    n_bits: int = Field(default=200_000, ge=10_000)
    alpha: float = Field(default=0.01, ge=0.0001, le=0.1)
    block_M: int = Field(default=256, ge=8)
    whiten: Literal["none","vn","sha512"] = "sha512"

# ---------- Routes ----------
@app.get("/")
def root():
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/hfp")
def hfp(req: HFPReq):
    h = assemble_hfp(req.seed, levels=req.levels)
    return {"fingerprint_hash": h["fingerprint_hash"], "version": h["version"], "levels": h["levels"]}

@app.post("/key")
def key(req: KeyReq):
    h = assemble_hfp(req.seed, levels=req.levels)
    pw = req.password.encode()
    if req.kdf == "hkdf":
        k = derive_key_from_hfp(pw, h["fingerprint_hash"], key_len=req.length)
    elif req.kdf == "scrypt":
        k = derive_key_scrypt(pw, h["fingerprint_hash"], key_len=req.length)
    else:
        if not HAVE_ARGON2:
            raise HTTPException(status_code=400, detail="argon2-cffi not installed")
        # Env defaults if fields are None
        tc = req.time_cost if req.time_cost is not None else _env_int("ARGON2_TIME_COST", 2)
        mk = req.memory_kib if req.memory_kib is not None else _env_int("ARGON2_MEMORY_KIB", 65536)
        pl = req.parallelism if req.parallelism is not None else _env_int("ARGON2_PARALLELISM", 1)
        k = derive_key_argon2id(pw, h["fingerprint_hash"], key_len=req.length, time_cost=tc, memory_cost_kib=mk, parallelism=pl)
    return {"fingerprint_hash": h["fingerprint_hash"], "kdf": req.kdf, "key_hex": k.hex()}

@app.post("/envelope")
def envelope(req: EnvReq):
    h = assemble_hfp(req.seed, levels=req.levels)
    params = photonic_map(h["band_stats"])
    env = make_envelope(h, params, dac_bits=req.dac_bits, sample_rate_GSa=req.sample_gsa, quant_mode=req.quant)
    alg = os.environ.get("SIGN_ALG","hmac").lower()
    if alg == "ed25519":
        priv_hex = os.environ.get("ED25519_PRIV_HEX","")
        if not priv_hex:
            raise HTTPException(status_code=500, detail="ED25519_PRIV_HEX not set")
        signed = sign_envelope_ed25519(env, priv_hex=priv_hex, key_id=req.key_id)
    else:
        sign_key = os.environ.get("SIGNING_KEY", "test-key").encode()
        signed = sign_envelope_hmac(env, key=sign_key, key_id=req.key_id)
    return json.loads(canonical_json(signed).decode())

@app.post("/sts")
def sts(req: STSReq):
    if req.whiten == "sha512":
        chunk_in, chunk_out = 4096, 512
        need_chunks = (req.n_bits + chunk_out - 1)//chunk_out
        n_stream = need_chunks*chunk_in
    else:
        n_stream = req.n_bits
    stream = default_stream(req.seed, n=n_stream)
    bits = stream_to_bits(stream, whiten=req.whiten)[:req.n_bits]
    report = run_suite(bits, alpha=req.alpha, block_M=req.block_M)
    return report
