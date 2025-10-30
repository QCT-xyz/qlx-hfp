# QLX HFP

[![qlx-sts-v1](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/qlx_sts_v1.yml/badge.svg)](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/qlx_sts_v1.yml) [![qlx-envelope-v1](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/qlx_envelope_v1.yml/badge.svg)](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/qlx_envelope_v1.yml)


Deterministic Harmonic Fingerprint (HFP) key and control pipeline with statistical gates, signed photonic envelopes, clean APIs, CI artifacts, and Cloud Run deployment.

[![dual_sts](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/dual_sts.yml/badge.svg)](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/dual_sts.yml)
[![ci_main](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/ci_main.yml/badge.svg)](https://github.com/QCT-xyz/qlx-hfp/actions/workflows/ci_main.yml)

---

## Why this exists

- Turn a seed into a deterministic **Harmonic Fingerprint (HFP)** using chaos plus wavelet sub-band stats  
- Derive keys with **Argon2id**, **scrypt**, **HKDF** using the HFP as a stable anchor  
- Map HFP to a **device-ready photonic control envelope** (DAC-quantized, open-interval clipped)  
- **Sign** envelopes with **Ed25519** or **HMAC** over canonical JSON  
- Ship a **FastAPI** service and a minimal **UI-proxy**, with a CI mini-battery and cloud-native deployment

---

## Features

- **HFP kernel**  
  Seed → logistic map plus 3-6-9 harmonic comb → Haar wavelet stats → canonical JSON → SHA-512 fingerprint  
  Timestamp is excluded from the preimage so the fingerprint is stable

- **Keys**  
  Argon2id (preferred), scrypt, HKDF  
  Argon2id costs via env: `ARGON2_TIME_COST`, `ARGON2_MEMORY_KIB`, `ARGON2_PARALLELISM`

- **Photonic envelope**  
  Band stats → device params: `I_bias_mA`, `phi_rad`, `kappa`, `tau_ps`, `delta_f_GHz`, `alpha`  
  Open-interval clipping by one DAC LSB avoids hard pins  
  DAC quantization and canonical JSON  
  Ed25519 or HMAC signing

- **Validation**  
  JSON Schema, band length checks, open-interval ranges  
  Ed25519 signature verify

- **STS mini battery**  
  Frequency, Block frequency, Runs, CUSUM (forward), DFT spectral, Approx Entropy m=2 (df=3)  
  Two whiteners as gates: **SHA-512** and **VN**. `none` is a non-gating monitor  
  CI guard: `all_pass` and `min_p >= 0.012`

- **Services**  
  FastAPI: `/`, `/healthz`, `/hfp`, `/key`, `/envelope`, `/sts`  
  UI-proxy: a one-page form that calls the API server side using a service account token

---

## Repository layout

src/
qlx_hfp_prototype.py       # HFP + KDFs + helpers
qlx_photonic_control.py    # mapping, quantization, sign, verify
qlx_sts_min.py             # mini battery
service_app.py             # FastAPI service

schemas/
qlx_photonic_control.schema.json

scripts/
export_payloads.py         # writes hfp_core.json, hfp_full.json, photonic_env_signed.json
validate_envelope.py       # schema + bounds + signature verify
sts_summarize.py           # roll-up JSON and HTML summaries
check_bounds.py            # strict inside-bounds check for params
qlx.py                     # CLI for hfp, key, export, sts

tests/                       # all green

ui-proxy/
app.py                     # minimal UI and server-side proxy
templates/index.html
requirements.txt
Dockerfile

Dockerfile                   # API image (FastAPI)
docker-entrypoint.sh
Makefile

---

## Quickstart

Prereqs: Python 3.10+, Docker, make.

```bash
make install
make test
python src/qlx_hfp_prototype.py     # prints HFP hash and keys

Run API locally with Docker:

docker build -t qlx-hfp:local .
docker run --rm -d --name qlx-hfp-local -p 8080:8080 qlx-hfp:local
curl -s http://127.0.0.1:8080/          # {"ok": true}
curl -s http://127.0.0.1:8080/healthz   # {"ok": true}
docker stop qlx-hfp-local


⸻

Running tests and STS

make test                  # unit tests
make sts                   # 200k bits, SHA-512 whitening
make long-sts              # 2,000,000 bits, SHA-512 whitening

Typical STS results
	•	SHA-512 at 200k: min_p ~ 0.014
	•	SHA-512 at 2e6: min_p ~ 0.18
	•	VN at 200k: min_p ~ 0.018
	•	none: expected to fail (monitor only)

⸻

API reference

Base URL is the deployed Cloud Run service or local http://127.0.0.1:8080.
	•	GET / → health, returns {"ok": true}
	•	GET /healthz → health, returns {"ok": true}. Some tenants reject this path at the gateway. Prefer / for external probes
	•	POST /hfp

{"seed":"...", "levels": 5}

→ {"fingerprint_hash":"...", "version":"HFP-0.1", "levels":5}

	•	POST /key

{"seed":"...", "levels":5, "kdf":"argon2id|scrypt|hkdf", "password":"...", "length":32}

→ {"fingerprint_hash":"...", "kdf":"...", "key_hex":"..."}
Argon2id cost defaults come from env if fields are not provided

	•	POST /envelope

{"seed":"...", "levels":5, "dac_bits":14, "sample_gsa":64, "quant":"nearest"}

→ signed canonical JSON envelope
Signing options via env
	•	SIGN_ALG=ed25519 with ED25519_PRIV_HEX in Secret Manager
	•	or SIGN_ALG=hmac with SIGNING_KEY in Secret Manager

	•	POST /sts

{"seed":"...", "n_bits":200000, "whiten":"sha512|vn|none"}

→ per-test p-values and a summary

⸻

Envelope schema and validation

Generate:

python scripts/export_payloads.py --seed "qlx-demo-seed-phi369" --sig-alg ed25519 --ed25519-priv-hex "$ED25519_PRIV_HEX"

Validate:

python scripts/validate_envelope.py artifacts/photonic_env_signed.json --ed25519-pub-hex "$ED25519_PUB_HEX"

Checks
	•	JSON Schema and band lengths
	•	Open-interval ranges by one DAC LSB
	•	Ed25519 signature verify if alg is Ed25519

⸻

UI proxy

Minimal UI that calls the API server side with a service account token. The browser never holds tokens.
	•	Deploys as qlx-ui-proxy on Cloud Run
	•	Set API_BASE to your API URL
	•	Internal access via signed local tunnel:

gcloud run services proxy qlx-ui-proxy --region us-central1 --port 8090 &
open http://localhost:8090



⸻

CI and artifacts

Manual workflow dual_sts.yml uploads
	•	sts-report-sha512.json, sts-report-vn.json, sts-none.json (monitor)
	•	sts_summary.json and sts_summary.html

Guard requires all_pass and min_p >= 0.012 for SHA-512 and VN.

Download latest artifacts

REPO="QCT-xyz/qlx-hfp"
RID=$(gh run list --repo "$REPO" --workflow "dual_sts.yml" --limit 1 --json databaseId -q '.[0].databaseId')
gh run download "$RID" --repo "$REPO" -n sts-report-sha512 -D artifacts_ci
gh run download "$RID" --repo "$REPO" -n sts-report-vn -D artifacts_ci
gh run download "$RID" --repo "$REPO" -n sts-summary -D artifacts_ci


⸻

Deploy to Cloud Run

Build and push

PROJECT="decent-surf-467802-h9"
REGION="us-central1"
REPO="qlx-api"
TAG="$(date +%Y%m%d-%H%M%S)"
gcloud builds submit --region="$REGION" \
  --tag "$REGION-docker.pkg.dev/$PROJECT/$REPO/qlx-hfp:$TAG"

Secrets for signing
	•	Ed25519: SIGN_ALG=ed25519 and ED25519_PRIV_HEX in Secret Manager
	•	HMAC: SIGN_ALG=hmac and SIGNING_KEY in Secret Manager

Service account

SA="qlx-hfp-sa@$PROJECT.iam.gserviceaccount.com"
gcloud iam service-accounts create qlx-hfp-sa --display-name="QLX HFP Cloud Run SA" || true

Grant the SA access to secrets, then deploy

gcloud run deploy qlx-hfp-api \
  --image "$REGION-docker.pkg.dev/$PROJECT/$REPO/qlx-hfp:$TAG" \
  --region "$REGION" \
  --platform managed \
  --service-account "$SA" \
  --set-secrets SIGN_ALG=SIGN_ALG:latest,ED25519_PRIV_HEX=ED25519_PRIV_HEX:latest,ARGON2_TIME_COST=ARGON2_TIME_COST:latest,ARGON2_MEMORY_KIB=ARGON2_MEMORY_KIB:latest,ARGON2_PARALLELISM=ARGON2_PARALLELISM:latest


⸻

IAM patterns that work in enterprises

Use service account impersonation with an audience-bound OIDC token

BASE=$(gcloud run services describe qlx-hfp-api --region us-central1 --format='value(status.url)')
SA="qlx-hfp-sa@$PROJECT.iam.gserviceaccount.com"
IDTOK=$(gcloud auth print-identity-token --impersonate-service-account="$SA" --audiences="$BASE")
curl -sH "Authorization: Bearer $IDTOK" "$BASE/"

Or use a signed tunnel

gcloud run services proxy qlx-hfp-api --region us-central1 --port 8085 &
curl -s http://localhost:8085/

Note: some tenants reject /healthz at the gateway. Use / or add /readyz.

⸻

Security notes
	•	Canonical JSON for fingerprint preimage and envelope signing
	•	Ed25519 or HMAC signatures
	•	No plaintext keys in code
	•	Argon2id defaults are reasonable for CI. Increase memory in production
	•	Open-interval clipping avoids edge pins for device knobs
	•	Unwhitened stream is a non-gating monitor to detect drift
	•	For production, add SBOM and dependency scanning in CI

⸻

Roadmap
	•	PractRand or Dieharder soak in nightly jobs and store artifacts
	•	Device-in-the-loop: test synchronization windows and BER under masking
	•	Controller stub: Ed25519 verify plus bounds checks, ready for firmware
	•	Observability and simple SLOs: latency, error rate, artifact production
	•	Policy profiles: local, CI, and prod presets for Argon2id and envelope parameters

⸻

License

MIT. See LICENSE.

---

## Controller Handoff (Offline Verify)

Use the controller-side verifier to validate any signed envelope without the API:

```bash
PYTHONPATH=src python3 scripts/controller_verify.py artifacts/photonic_env_signed.json --ed25519-pub-hex "<ED25519_PUB_HEX>"
```

**What it checks**
- **Lengths**: each parameter array matches `band_count`
- **Ranges**: strictly inside the open interval by 1 DAC LSB (with a tiny tolerance)
- **Signature**: Ed25519 (or HMAC)

**Result**: JSON with `lengths_ok`, `ranges_ok`, `sig_ok`, and overall `ok`.

