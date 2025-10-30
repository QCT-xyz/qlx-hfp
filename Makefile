PY := python3
export PYTHONPATH := src
SEED ?= qlx-demo-seed-phi369
LEVELS ?= 5
# KDF params
KDF ?= argon2id
PW ?= demo-password
LEN ?= 32
# Export params
DAC ?= 14
GSA ?= 64
QUANT ?= nearest
KEY ?= test-key
KEY_ID ?= ctrl-01
OUT ?= artifacts_cli
.PHONY: install test demo sts export verify ci-local long-sts key export-cli
install:
	$(PY) -m pip install -r requirements.txt
test:
	$(PY) -m pytest
demo:
	$(PY) src/qlx_hfp_prototype.py
sts:
	$(PY) src/qlx_sts_min.py --n-bits 200000 --whiten sha512
export:
	$(PY) scripts/export_payloads.py --seed "$(SEED)"
verify:
	$(PY) scripts/verify_payloads.py
ci-local: test sts
long-sts:
	./scripts/fetch_weekly.sh
bounds:
	$(PY) scripts/check_bounds.py
	$(PY) src/qlx_sts_min.py --n-bits 2000000 --whiten sha512
# Convenience
key:
	$(PY) scripts/qlx.py key --kdf $(KDF) --pw "$(PW)" --length $(LEN) --seed "$(SEED)" --levels $(LEVELS)
export-cli:
	$(PY) scripts/qlx.py export --seed "$(SEED)" --levels $(LEVELS) --dac-bits $(DAC) --sample-gsa $(GSA) --quant $(QUANT) --key "$(KEY)" --key-id "$(KEY_ID)" --out "$(OUT)"
# Run controller-side envelope verification (lengths, ranges, signature)
# Usage: make controller-verify ENV=artifacts/photonic_env_signed.json PUB=<ED25519_PUB_HEX>
controller-verify:
	PYTHONPATH=src python3 scripts/controller_verify.py "$(ENV)" --ed25519-pub-hex "$(PUB)"
# One-command Cloud Run smoke test (requires gcloud auth & SA impersonation)
fetch-weekly:
	./scripts/smoke_cloud_run.sh

smoke-cloud:
	./scripts/smoke_cloud_run.sh
