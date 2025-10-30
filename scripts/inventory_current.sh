#!/usr/bin/env bash
set -euo pipefail
PROJECT="${PROJECT:-decent-surf-467802-h9}"
REGION="${REGION:-us-central1}"
echo "project=$PROJECT region=$REGION"
svcs=$(gcloud run services list --platform=managed --project "$PROJECT" --region "$REGION" --format="value(metadata.name)")
if [ -z "$svcs" ]; then echo "no services found"; exit 0; fi
for name in $svcs; do
  echo "=== $name ==="
  svc=$(gcloud run services describe "$name" --project "$PROJECT" --region "$REGION" --format=json)
  url=$(echo "$svc" | jq -r ".status.url // empty")
  img=$(echo "$svc" | jq -r ".spec.template.spec.containers[0].image // empty")
  traffic=$(echo "$svc" | jq -r "[.status.traffic[]?|{rev:.revisionName,pct:.percent}] // []")
  envkeys=$(echo "$svc" | jq -r "[.spec.template.spec.containers[0].env[]?|.name] // []")
  secrets_env=$(echo "$svc" | jq -r "[.spec.template.spec.containers[0].env[]?|select(.valueFrom.secretKeyRef)|.valueFrom.secretKeyRef.name] // []")
  secrets_vol=$(echo "$svc" | jq -r "[.spec.template.spec.volumes[]?|select(.secret)|.secret.secretName] // []")
  echo "url:      $url"
  echo "image:    $img"
  echo "traffic:  $traffic"
  echo "env:      $envkeys"
  echo "secrets:  {env: $secrets_env, volumes: $secrets_vol}"
  echo
done
