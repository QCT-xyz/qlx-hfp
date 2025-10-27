import json, math, hashlib, hmac, uuid, datetime
import numpy as np

def _normalize01(x):
    x = np.asarray(x, dtype=float)
    mn, mx = x.min(), x.max()
    return (x - mn) / (mx - mn + 1e-15)

def photonic_map(band_stats):
    means = np.array([b["mean"] for b in band_stats])
    stds  = np.array([b["std"]  for b in band_stats])
    ents  = np.array([b["entropy"] for b in band_stats])

    I_bias_mA = 15.0 + _normalize01(means) * (50.0 - 15.0)
    phi_rad   = 0.0  + _normalize01(ents)  * (math.pi - 0.0)
    kappa     = 0.05 + _normalize01(stds)  * (0.90 - 0.05)
    tau_ps    = 50.0 + _normalize01(np.roll(ents,1)) * (300.0 - 50.0)
    delta_f   = -10.0 + _normalize01(np.roll(means,1)) * (10.0 - (-10.0))
    alpha     = 2.0  + _normalize01(np.roll(stds,2))  * (6.0 - 2.0)

    return {
        "I_bias_mA": I_bias_mA.tolist(),
        "phi_rad":   phi_rad.tolist(),
        "kappa":     kappa.tolist(),
        "tau_ps":    tau_ps.tolist(),
        "delta_f_GHz": delta_f.tolist(),
        "alpha":     alpha.tolist()
    }

def _quantize(arr, lo, hi, bits, mode="nearest"):
    arr = np.asarray(arr, dtype=float)
    arr = np.clip(arr, lo, hi)
    q = (arr - lo) / (hi - lo)
    levels = (1 << bits) - 1
    x = q * levels
    if mode == "nearest":
        xi = np.rint(x)
    elif mode == "floor":
        xi = np.floor(x)
    elif mode == "stochastic":
        frac = x - np.floor(x)
        rnd = np.random.random(len(arr))
        xi = np.floor(x) + (rnd < frac)
    else:
        raise ValueError("quantization mode")
    return (xi / levels) * (hi - lo) + lo

def make_envelope(hfp, photonic_params, dac_bits=14, sample_rate_GSa=64,
                  quant_mode="nearest", mode="static", ramp_ms=10, hold_ms=2000, ttl_ms=10000):
    keys = ["I_bias_mA","phi_rad","kappa","tau_ps","delta_f_GHz","alpha"]
    Ls = [len(photonic_params[k]) for k in keys]
    if len(set(Ls)) != 1:
        raise ValueError(f"photonic_params arrays must have equal length, got lengths={Ls}")
    L = Ls[0]
    qp = {
        "I_bias_mA":  _quantize(photonic_params["I_bias_mA"], 15.0, 50.0, dac_bits, quant_mode).tolist(),
        "phi_rad":    _quantize(photonic_params["phi_rad"], 0.0, math.pi, dac_bits, quant_mode).tolist(),
        "kappa":      _quantize(photonic_params["kappa"], 0.05, 0.9, dac_bits, quant_mode).tolist(),
        "tau_ps":     _quantize(photonic_params["tau_ps"], 50.0, 300.0, dac_bits, quant_mode).tolist(),
        "delta_f_GHz":_quantize(photonic_params["delta_f_GHz"], -10.0, 10.0, dac_bits, quant_mode).tolist(),
        "alpha":      _quantize(photonic_params["alpha"], 2.0, 6.0, dac_bits, quant_mode).tolist()
    }
    env = {
        "version": "P-0.2",
        "session_id": str(uuid.uuid4()),
        "hfp_hash": hfp["fingerprint_hash"],
        "band_count": L,
        "mode": mode,
        "apply": {
            "at": datetime.datetime.now(datetime.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ramp_ms": ramp_ms, "hold_ms": hold_ms, "ttl_ms": ttl_ms
        },
        "params": qp,
        "dac": {"width_bits": dac_bits, "sample_rate_GSa": sample_rate_GSa, "quantization": quant_mode}
    }
    return env

def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sign_envelope_hmac(envelope, key: bytes, key_id="ctrl-01"):
    msg = canonical_json(envelope)
    sig = hmac.new(key, msg, hashlib.sha256).hexdigest()
    envelope["signing"] = {
        "alg": "HMAC-SHA256", "key_id": key_id, "nonce": "",
        "timestamp": datetime.datetime.now(datetime.UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sig": sig
    }
    return envelope
