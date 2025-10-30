#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-decent-surf-467802-h9}"
REGION="${REGION:-us-central1}"
SERVICE="${SERVICE:-qlx-hfp-api}"
SA="${SA:-qlx-hfp-sa@${PROJECT}.iam.gserviceaccount.com}"
BASE="$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
IDTOK="$(gcloud auth print-identity-token --impersonate-service-account="$SA" --audiences="$BASE")"
echo "PROJECT: $PROJECT"
echo "REGION:  $REGION"
echo "SERVICE: $SERVICE"
echo "SA:      $SA"
echo "BASE:    $BASE"
echo "GET /"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/" | python3 -m json.tool || true
echo "GET /readyz"
curl -sS -H "Authorization: Bearer $IDTOK" "$BASE/readyz" | python3 -m json.tool || true
echo "POST /hfp"
curl -sS -H "Authorization: Bearer $IDTOK" -H 'content-type: application/json' "$BASE/hfp" -d '{"seed":"qlx-demo-seed-phi369","levels":5}' | python3 -m json.tool || true
echo "POST /sts"
curl -sS -H "Authorization: Bearer $IDTOK" -H 'content-type: application/json' "$BASE/sts" -d '{"seed":"qlx-demo-seed-phi369","n_bits":200000,"whiten":"sha512"}' | python3 -m json.tool || true
echo "POST /envelope"
curl -sS -H "Authorization: Bearer $IDTOK" -H 'content-type: application/json' "$BASE/envelope" -d '{"seed":"qlx-demo-seed-phi369","levels":5,"dac_bits":14,"sample_gsa":64,"quant":"nearest"}' | python3 -m json.tool || true
