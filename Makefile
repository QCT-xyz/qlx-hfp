PY := python3
export PYTHONPATH := src
SEED ?= qlx-demo-seed-phi369

.PHONY: install test demo sts export verify

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
