#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-decent-surf-467802-h9}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-qlx-hfp-api}"
SA="${SA:-qlx-hfp-sa@$PROJECT.iam.gserviceaccount.com}"

echo "[smoke] project=$PROJECT region=$REGION service=$SERVICE sa=$SA"
BASE="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "[smoke] base=$BASE"

echo "[smoke] minting OIDC (impersonated) with audience=$BASE"
IDTOK="$(gcloud auth print-identity-token --impersonate-service-account="$SA" --audiences="$BASE")"

echo "[smoke] GET /"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/" | jq .

echo "[smoke] POST /hfp"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/hfp" \
  -H 'content-type: application/json' \
  -d '{"seed":"qlx-demo-seed-phi369","levels":5}' | jq .

echo "[smoke] POST /sts (200k, sha512)"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/sts" \
  -H 'content-type: application/json' \
  -d '{"seed":"qlx-demo-seed-phi369","n_bits":200000,"whiten":"sha512"}' | jq '.summary'

echo "[smoke] POST /envelope"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/envelope" \
  -H 'content-type: application/json' \
  -d '{"seed":"qlx-demo-seed-phi369","levels":5,"dac_bits":14,"sample_gsa":64,"quant":"nearest"}' | jq '.signing'
