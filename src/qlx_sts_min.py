import json, math, argparse, hashlib, struct, random, numpy as np

SQRT2 = math.sqrt(2.0)
def normal_cdf(z): return 0.5*(1.0 + math.erf(z/SQRT2))
def erfc(x): return math.erfc(x)

def wilson_hilferty_p_upper_chi2(x, k):
    if k <= 0 or x < 0: return 1.0
    z = ((x/k)**(1.0/3.0) - (1 - 2.0/(9.0*k))) / math.sqrt(2.0/(9.0*k))
    return 0.5*erfc(z/SQRT2)

# stream
def logistic_map(n, r=3.99, x0=0.372, burn=1024):
    x = np.empty(n+burn); x[0] = x0
    for i in range(1, n+burn):
        x[i] = r*x[i-1]*(1 - x[i-1])
    return x[burn:]

def harmonic_comb(n, freqs, fs=1.0, phi=1.61803398875, phase_seed=0xBEEF):
    rng = random.Random(phase_seed)
    t = np.arange(n)/fs
    s = np.zeros(n, dtype=float); wtot = 0.0
    for i, f in enumerate(freqs, start=1):
        w = phi**(-i); wtot += w
        phase = rng.random()*2*np.pi
        s += w*np.sin(2*np.pi*f*t + phase)
    s /= (wtot + 1e-15)
    return s

def default_stream(seed_phrase, n):
    h = hashlib.sha256(seed_phrase.encode()).digest()
    x0 = struct.unpack(">I", h[:4])[0] / 2**32
    chaos = logistic_map(n, r=3.99, x0=0.2 + 0.6*x0, burn=2048)
    chaos = (chaos - np.mean(chaos)); chaos /= (np.std(chaos) + 1e-12)
    carriers = harmonic_comb(n, [3,6,9,27,54,111,216], phi=1.61803398875,
                             phase_seed=struct.unpack(">I", h[4:8])[0])
    blend = chaos + 0.30*carriers
    return (blend - np.mean(blend)) / (np.std(blend) + 1e-12)

def stream_to_bits(x, thresh=0.0, whiten="none"):
    raw = (x > thresh).astype(np.uint8)
    if whiten == "none": return raw
    if whiten == "vn":
        even = raw[0:len(raw)//2*2:2]; odd = raw[1:len(raw)//2*2:2]
        keep10 = (even == 1) & (odd == 0)
        keep01 = (even == 0) & (odd == 1)
        out = np.concatenate([np.ones(np.sum(keep10), dtype=np.uint8),
                              np.zeros(np.sum(keep01), dtype=np.uint8)])
        if out.size:
            np.random.default_rng(12345).shuffle(out)
        return out
    if whiten == "sha512":
        chunk_in, out_blocks, cnt = 4096, [], 0
        for i in range(0, len(raw), chunk_in):
            b = raw[i:i+chunk_in]
            if b.size == 0: break
            by = np.packbits(b, bitorder="big").tobytes()
            h = hashlib.sha512(cnt.to_bytes(8, "big") + by).digest()
            hb = np.unpackbits(np.frombuffer(h, dtype=np.uint8), bitorder="big")
            out_blocks.append(hb); cnt += 1
        return np.concatenate(out_blocks) if out_blocks else np.zeros(0, dtype=np.uint8)
    raise ValueError("unknown whitening")

# tests
def freq_monobit(bits):
    n = len(bits)
    if n == 0: return {"p": 0.0, "stat": 0.0}
    y = bits.astype(np.int64)*2 - 1
    s = int(np.sum(y))
    sobs = abs(s)/math.sqrt(n)
    p = erfc(sobs/SQRT2)
    return {"p": float(p), "stat": float(sobs)}

def block_frequency(bits, M=256):
    n = len(bits); N = n//M
    if N == 0: return {"p": 0.0, "stat": 0.0, "note": "short"}
    x = bits[:N*M].reshape(N, M)
    pis = x.mean(axis=1)
    chi2 = 4.0*M*float(np.sum((pis - 0.5)**2))
    p = wilson_hilferty_p_upper_chi2(chi2, N)
    return {"p": float(p), "stat": float(chi2), "N": int(N), "M": int(M)}

def runs_test(bits):
    n = len(bits)
    if n < 2: return {"p": 0.0, "stat": 0.0, "note": "short"}
    pi = float(np.mean(bits))
    tau = 2.0/math.sqrt(n)
    if abs(pi - 0.5) >= tau:
        return {"p": 0.0, "stat": float(pi), "note": "pi off 0.5"}
    v = 1 + int(np.sum(bits[1:] != bits[:-1]))
    num = abs(v - 2.0*n*pi*(1.0 - pi))
    den = 2.0*math.sqrt(2.0*n)*pi*(1.0 - pi)
    p = erfc(num/den)
    return {"p": float(p), "stat": int(v), "pi": pi}

def cusum_forward(bits):
    n = len(bits)
    if n == 0: return {"p": 0.0, "stat": 0.0}
    y = bits.astype(np.int64)*2 - 1
    s = np.cumsum(y)
    z = float(np.max(np.abs(s)))
    if z == 0.0: return {"p": 1.0, "stat": 0.0}
    t = z/math.sqrt(n)
    kmin1 = int(math.ceil((-n/z + 1.0)/4.0))
    kmax1 = int(math.floor(( n/z - 1.0)/4.0))
    kmin2 = int(math.ceil((-n/z - 3.0)/4.0))
    kmax2 = int(math.floor(( n/z - 3.0)/4.0))
    sum1 = sum(normal_cdf((4*k+1)*t) - normal_cdf((4*k-1)*t) for k in range(kmin1, kmax1+1))
    sum2 = sum(normal_cdf((4*k+3)*t) - normal_cdf((4*k+1)*t) for k in range(kmin2, kmax2+1))
    p = 1.0 - sum1 + sum2
    p = max(0.0, min(1.0, p))
    return {"p": float(p), "stat": z}

def dft_spectral(bits):
    n = len(bits)
    if n < 64: return {"p": 0.0, "stat": 0.0, "note": "short"}
    x = bits.astype(np.int64)*2 - 1
    s = np.fft.fft(x)
    mags = np.abs(s)[1:(n//2)]
    T = math.sqrt(math.log(1.0/0.05) * n)
    N1 = int(np.sum(mags < T))
    N0 = 0.95*n/2.0
    var = n*0.95*0.05/4.0
    d = (N1 - N0)/math.sqrt(var)
    p = erfc(abs(d)/SQRT2)
    return {"p": float(p), "stat": float(d), "N1": int(N1), "T": float(T)}


def approx_entropy(bits, m=2):
    n = len(bits)
    if n < (m+1):
        return {"p": 0.0, "stat": 0.0, "note": "short"}
    def phi(mm):
        k = 1 << mm
        counts = np.zeros(k, dtype=np.int64)
        mask = k - 1
        val = 0
        # extend by mm to allow b[i+mm] up to i = n-1
        b = np.concatenate([bits, bits[:mm]])
        # init window
        for i in range(mm):
            val = ((val << 1) & mask) | int(b[i])
        # slide over n positions
        for i in range(n):
            val = ((val << 1) & mask) | int(b[i + mm])
            counts[val] += 1
        probs = counts / float(n)
        nz = probs > 0
        return float(np.sum(probs[nz] * np.log(probs[nz])))
    phi_m  = phi(m)
    phi_m1 = phi(m + 1)
    ApEn = phi_m - phi_m1
    chi2 = 2.0 * n * (math.log(2) - ApEn)
    df = (1 << m) - 1
    p = wilson_hilferty_p_upper_chi2(chi2, df)
    return {"p": float(p), "stat": float(chi2), "ApEn": float(ApEn), "df": int(df)}


def run_suite(bits, alpha=0.01, block_M=256):
    results, fails = {}, []
    r = freq_monobit(bits); results["frequency_monobit"] = r
    if r["p"] < alpha: fails.append("frequency_monobit")
    r = block_frequency(bits, M=block_M); results["block_frequency"] = r
    if r["p"] < alpha: fails.append("block_frequency")
    r = runs_test(bits); results["runs_test"] = r
    if r["p"] < alpha: fails.append("runs_test")
    r = cusum_forward(bits); results["cusum_forward"] = r
    if r["p"] < alpha: fails.append("cusum_forward")
    r = dft_spectral(bits); results["dft_spectral"] = r
    if r["p"] < alpha: fails.append("dft_spectral")
    r = approx_entropy(bits, m=2); results["approx_entropy_m2"] = r
    if r["p"] < alpha: fails.append("approx_entropy_m2")
    min_p = min((results[k]["p"] for k in results if "p" in results[k]), default=1.0)
    return {
        "suite": "qlx-sts-min",
        "alpha": alpha,
        "n_bits": int(len(bits)),
        "block_M": block_M,
        "results": results,
        "summary": {"all_pass": len(fails)==0, "min_p": float(min_p), "failures": fails}
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=str, default="qlx-demo-seed-phi369")
    ap.add_argument("--n-bits", type=int, default=200000)
    ap.add_argument("--alpha", type=float, default=0.01)
    ap.add_argument("--block-M", type=int, default=256)
    ap.add_argument("--whiten", type=str, default="sha512", choices=["none","vn","sha512"])
    ap.add_argument("--json-out", type=str, default="")
    args = ap.parse_args()

    if args.whiten == "sha512":
        chunk_in, chunk_out = 4096, 512
        need_chunks = (args.n_bits + chunk_out - 1)//chunk_out
        n_stream = need_chunks*chunk_in
    else:
        n_stream = args.n_bits

    stream = default_stream(args.seed, n=n_stream)
    bits = stream_to_bits(stream, whiten=args.whiten)[:args.n_bits]
    report = run_suite(bits, alpha=args.alpha, block_M=args.block_M)
    js = json.dumps(report, indent=2)
    if args.json_out:
        with open(args.json_out, "w") as f: f.write(js)
    print(js)
    raise SystemExit(0 if report["summary"]["all_pass"] else 2)

if __name__ == "__main__":
    main()
