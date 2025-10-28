#!/usr/bin/env bash
set -euo pipefail
docker build -t qlx-hfp:local .
docker rm -f qlx-hfp-local 2>/dev/null || true
docker run --rm -p 8080:8080 \
  -e SIGN_ALG="${SIGN_ALG:-hmac}" \
  -e SIGNING_KEY="${SIGNING_KEY:-test-key}" \
  -e ED25519_PRIV_HEX="${ED25519_PRIV_HEX:-}" \
  -e ARGON2_TIME_COST="${ARGON2_TIME_COST:-2}" \
  -e ARGON2_MEMORY_KIB="${ARGON2_MEMORY_KIB:-65536}" \
  -e ARGON2_PARALLELISM="${ARGON2_PARALLELISM:-1}" \
  --name qlx-hfp-local qlx-hfp:local
