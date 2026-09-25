#!/usr/bin/env bash
# =============================================================================
# build_hunspell_dictionary.sh: construye el diccionario hunspell de una
# localización desde las fuentes de RLA-ES
# =============================================================================
#
#   bash tools/lang/build_hunspell_dictionary.sh <checkout de rla-es> es_MX <destino>
#
# Reproduce los pasos de `herramientas/make_dict.sh` de RLA-ES (Santiago Bosio
# e Ismael Olea, GPL-3+ / LGPL-3+ / MPL-1.1+) para una sola localización, sin
# las preguntas de publicación que ese guion hace a mano:
#
#   - el .aff son los afijos de la localización (o los generales si no tiene),
#     sin comentarios;
#   - el .dic es la lista única y ordenada de las palabras de la RAE comunes y
#     de la localización, las no RAE comunes y de la localización y los
#     topónimos, con el conteo en la primera línea.
#
# El filtro de comentarios es el de `herramientas/remover_comentarios.sh`.
# =============================================================================
set -euo pipefail

src="${1:-}" locale="${2:-}" out="${3:-}"
if [[ -z "$src" || -z "$locale" || -z "$out" ]]; then
    echo "uso: $0 <checkout de rla-es> <localización> <destino>" >&2
    exit 2
fi
if [[ ! -d "$src/ortografia/palabras/RAE" ]]; then
    echo "build_hunspell_dictionary: '$src' no es un checkout de RLA-ES (falta ortografia/palabras/RAE)." >&2
    exit 2
fi

strip_comments() {
    sed -n '/^\#.*/ { d; }; /^$/ { d; }; /^[^\#]*\#.*/! { p; };
            /^[^\#]*\ [\ ]*\#.*/ { s/\ [\ ]*\#.*//; p; };
            /^[^\#]*\t[\t]*\#.*/ { s/\t[\t]*\#.*//; p; }' | \
    sed -n '/  /! { p; }; /  \( \)*/ { s// /g; p; }'
}

# Concatena los .txt de un directorio si existe; en silencio si no.
lists() { local d="$1" pattern="${2:-*.txt}"; [[ -d "$d" ]] && find "$d" -maxdepth 1 -name "$pattern" -print0 | sort -z | xargs -0 -r cat; true; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
words="$src/ortografia/palabras"
affixes="$src/ortografia/afijos/l10n/$locale/afijos.txt"
[[ -f "$affixes" ]] || affixes="$src/ortografia/afijos/afijos.txt"

strip_comments < "$affixes" > "$tmp/$locale.aff"
{
    lists "$words/RAE"
    lists "$words/RAE/l10n/$locale"
    lists "$words/noRAE"
    lists "$words/toponimos" "toponimos-*.txt"
    lists "$words/noRAE/l10n/$locale"
    lists "$words/toponimos/l10n/$locale" "toponimos-*.txt"
} | strip_comments | LC_ALL=C.UTF-8 sort -u > "$tmp/words"
{ wc -l < "$tmp/words" | tr -d ' '; cat "$tmp/words"; } > "$tmp/$locale.dic"

mkdir -p "$out"
mv "$tmp/$locale.aff" "$tmp/$locale.dic" "$out/"
echo "build_hunspell_dictionary: $locale con $(head -1 "$out/$locale.dic") entradas en $out"
