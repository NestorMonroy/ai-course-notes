#!/usr/bin/env bash
# HEAD de manifiesto por digest en docker.io, anónimo y con la credencial de
# LECTURA (THYROX_REGISTRY_READER_*). No descarga capas ni imprime secretos:
# sólo el código HTTP, el Docker-Content-Digest devuelto y si coincide.
# Uso: manifest-head.sh <repositorio> <sha256:...> [<blob-sha256:...>]
set -u
repo="$1" digest="$2" blob="${3:-}"
accept='application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.list.v2+json,application/vnd.docker.distribution.manifest.v2+json'
token_for() {
  local auth=()
  if [[ "$1" == reader ]]; then
    [[ -n "${THYROX_REGISTRY_READER_USERNAME:-}" && -n "${THYROX_REGISTRY_READER_TOKEN:-}" ]] || { echo ""; return; }
    auth=(-u "${THYROX_REGISTRY_READER_USERNAME}:${THYROX_REGISTRY_READER_TOKEN}")
  fi
  curl -s "${auth[@]}" "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${repo}:pull" \
    | python3 -I -c 'import sys,json;print(json.load(sys.stdin).get("token",""))'
}
for mode in anonymous reader; do
  tok="$(token_for "$mode")"
  if [[ -z "$tok" ]]; then printf '%s\t%s\tmanifest\tNO_TOKEN\t-\t-\n' "$repo" "$mode"; continue; fi
  hdr="$(curl -s -I -H "Authorization: Bearer $tok" -H "Accept: $accept" "https://registry-1.docker.io/v2/${repo}/manifests/${digest}")"
  code="$(printf '%s' "$hdr" | awk 'NR==1{print $2}')"
  got="$(printf '%s' "$hdr" | tr -d '\r' | awk -F': ' 'tolower($1)=="docker-content-digest"{print $2}')"
  match=$([[ "$got" == "$digest" ]] && echo MATCH || echo NO_MATCH)
  printf '%s\t%s\tmanifest\t%s\t%s\t%s\n' "$repo" "$mode" "$code" "${got:--}" "$match"
  if [[ -n "$blob" ]]; then
    # HEAD del blob: sin -L, sólo el código (307 = existe y redirige al almacén).
    bcode="$(curl -s -o /dev/null -I -w '%{http_code}' -H "Authorization: Bearer $tok" "https://registry-1.docker.io/v2/${repo}/blobs/${blob}")"
    printf '%s\t%s\tblob\t%s\t%s\t-\n' "$repo" "$mode" "$bcode" "$blob"
  fi
done
