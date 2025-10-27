import math, json, hashlib, hmac, struct, time, random
import numpy as np
import os

def _env_int(key, default):
    try:
        return int(os.environ.get(key, default))
    except Exception:
        return default

try:
    from argon2.low_level import hash_secret_raw, Type
    HAVE_ARGON2 = True
except Exception:
    HAVE_ARGON2 = False

# ---------- helpers ----------
def shannon_entropy(x, bins=64):
    x = np.asarray(x, dtype=float)
    x = (x - x.min()) / (x.max() - x.min() + 1e-15)
    hist, _ = np.histogram(x, bins=bins, range=(0.0,1.0), density=True)
    p = hist / (np.sum(hist) + 1e-15)
    p = p + 1e-12
    return float(-np.sum(p*np.log2(p)) / math.log2(bins))

def hkdf_extract(salt, ikm, hashmod=hashlib.sha512):
    return hmac.new(salt, ikm, hashmod).digest()

def hkdf_expand(prk, info, length, hashmod=hashlib.sha512):
    hlen = hashmod().digest_size
    n = math.ceil(length / hlen)
    okm, t = b"", b""
    for i in range(1, n+1):
        t = hmac.new(prk, t + info + bytes([i]), hashmod).digest()
        okm += t
    return okm[:length]

# ---------- chaos and harmonics ----------
def logistic_map(n, r=3.99, x0=0.372, burn=1024):
    x = np.empty(n+burn); x[0] = x0
    for i in range(1, n+burn):
        x[i] = r * x[i-1] * (1 - x[i-1])
    return x[burn:]

def harmonic_comb(n, freqs, fs=1.0, phi=1.61803398875, phase_seed=0xBEEF):
    rng = random.Random(phase_seed)
    t = np.arange(n)/fs
    s = np.zeros(n, dtype=float)
    w_total = 0.0
    for i, f in enumerate(freqs, start=1):
        w = phi**(-i)  # phi weighting
        w_total += w
        phase = rng.random()*2*np.pi
        s += w * np.sin(2*np.pi*f*t + phase)
    s /= (w_total + 1e-15)
    return s

# ---------- Haar DWT ----------
def dwt_haar(x, levels=4):
    a = np.array(x, dtype=float)
    details = []
    h = 1/math.sqrt(2)
    for _ in range(levels):
        if len(a) % 2 == 1:
            a = a[:-1]
        a_next = (a[0::2]*h + a[1::2]*h)
        d_next = (a[0::2]*h - a[1::2]*h)
        details.append(d_next)
        a = a_next
    return [a] + details  # [A_L, D_L, D_{L-1}, ..., D1]

def compute_band_stats(bands, phi=1.61803398875):
    names = ["A_L"] + [f"D_{i}" for i in range(len(bands)-1,0,-1)]
    stats = []
    for name, b in zip(names, bands):
        b = np.asarray(b, dtype=float) * phi
        stats.append({
            "band": name,
            "mean": float(np.mean(b)),
            "std": float(np.std(b) + 1e-15),
            "entropy": shannon_entropy(b, bins=64)
        })
    return stats

# ---------- HFP assembly ----------

def assemble_hfp(seed_phrase, levels=5, seed_harmonics=(3,6,9,27,54,111,216), phi=1.61803398875, carrier_gain=0.30, n=8192):
    sp_hash = hashlib.sha256(seed_phrase.encode()).digest()
    x0 = struct.unpack(">I", sp_hash[:4])[0] / 2**32
    chaos = logistic_map(n, r=3.99, x0=0.2 + 0.6*x0, burn=2048)
    chaos = (chaos - np.mean(chaos)) / (np.std(chaos) + 1e-12)

    phase_seed = struct.unpack(">I", sp_hash[4:8])[0]
    carriers = harmonic_comb(n, [float(f) for f in seed_harmonics], fs=1.0, phi=phi, phase_seed=phase_seed)

    blend = chaos + carrier_gain*carriers
    blend = (blend - np.mean(blend)) / (np.std(blend) + 1e-12)

    bands = dwt_haar(blend, levels=levels)
    stats = compute_band_stats(bands, phi=phi)

    # Build a stable core without timestamp or fingerprint
    record_core = {
        "version": "HFP-0.1",
        "wavelet_basis": "haar",
        "levels": levels,
        "seed_harmonics": list(seed_harmonics),
        "phi": phi,
        "chaos": {"type": "logistic", "params": {"r": 3.99}, "burn_in": 2048},
        "mixer": {"carrier_gain": carrier_gain},
        "band_stats": stats
    }

    # Canonical JSON for deterministic hashing
    s_core = json.dumps(record_core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    fingerprint = hashlib.sha512(s_core).hexdigest()

    # Add runtime fields after the hash is fixed
    record = dict(record_core)
    record["timestamp"] = time.time()
    record["fingerprint_hash"] = fingerprint
    return record

def derive_key_argon2id(password: bytes, hfp_hash_hex: str, key_len=32, time_cost=None, memory_cost_kib=None, parallelism=None):
    if not globals().get("HAVE_ARGON2", False):
        raise RuntimeError("argon2-cffi not installed")
    if time_cost is None: time_cost = _env_int("ARGON2_TIME_COST", 2)
    if memory_cost_kib is None: memory_cost_kib = _env_int("ARGON2_MEMORY_KIB", 65536)
    if parallelism is None: parallelism = _env_int("ARGON2_PARALLELISM", 1)
    salt = bytes.fromhex(hfp_hash_hex[:32])
    return hash_secret_raw(
        secret=password,
        salt=salt,
        time_cost=time_cost,
        memory_cost=memory_cost_kib,
        parallelism=parallelism,
        hash_len=key_len,
        type=Type.ID
    )


def derive_key_from_hfp(password: bytes, hfp_hash_hex: str, key_len=32):
    salt = bytes.fromhex(hfp_hash_hex[:32])  # 16 bytes from HFP hash prefix
    prk = hkdf_extract(salt, password)
    okm = hkdf_expand(prk, b"QLX-HFP-KDF", key_len)
    return okm

def derive_key_scrypt(password: bytes, hfp_hash_hex: str, key_len=32, n=(1<<15), r=8, p=1):
    """
    Derive a key using standard-library scrypt.
    Default params: N=2^15, r=8, p=1. Adjust for your threat model.
    Salt comes from the HFP hash prefix to bind keys to the fingerprint.
    """
    import hashlib
    salt = bytes.fromhex(hfp_hash_hex[:32])  # 16-byte salt
    return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, dklen=key_len)


def derive_key_scrypt(password: bytes, hfp_hash_hex: str, key_len=32, n=None, r=None, p=None, maxmem=None):
    """
    Scrypt KDF with safe defaults and OpenSSL maxmem guard.
    Defaults: N=2^14, r=8, p=1 which is ~16 MiB. Adjust via args if desired.
    """
    import hashlib
    if n is None: n = 1<<14
    if r is None: r = 8
    if p is None: p = 1
    salt = bytes.fromhex(hfp_hash_hex[:32])
    # Estimated memory usage is ~128 * r * N bytes
    est_mem = 128 * r * n
    mm = est_mem*2 + 1_048_576 if maxmem is None else maxmem
    try:
        return hashlib.scrypt(password, salt=salt, n=n, r=r, p=p, maxmem=mm, dklen=key_len)
    except ValueError:
        # If OpenSSL rejects the allocation, step N down by 2 until 2^12
        nn = n
        while nn >= (1<<12):
            try:
                est_mem = 128 * r * nn
                mm = est_mem*2 + 1_048_576
                return hashlib.scrypt(password, salt=salt, n=nn, r=r, p=p, maxmem=mm, dklen=key_len)
            except ValueError:
                nn //= 2
        raise

if __name__ == "__main__":
    seed = "qlx-demo-seed-phi369"
    hfp = assemble_hfp(seed)
    hkdf_key = derive_key_from_hfp(b"demo-password", hfp["fingerprint_hash"], key_len=32)
    scrypt_key = derive_key_scrypt(b"demo-password", hfp["fingerprint_hash"], key_len=32)
    print("HFP hash:", hfp["fingerprint_hash"][:48] + "...")
    print("HKDF key (32B):", hkdf_key.hex())
    print("scrypt key (32B):", scrypt_key.hex())
    try:
        arg2 = derive_key_argon2id(b"demo-password", hfp["fingerprint_hash"], key_len=32)
        print("Argon2id key (32B):", arg2.hex())
    except Exception as e:
        print("Argon2id key (skipped):", str(e))
