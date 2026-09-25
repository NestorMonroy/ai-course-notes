#!/usr/bin/env bash
# =============================================================================
# toolchain.sh: las herramientas del sistema que usa ai-course-notes
# =============================================================================
#
# Adaptado de THYROX (`src/lib/toolchain.sh` y `src/lib/logging.sh`, rama
# feature/ai-course-notes-l1) para que el consumer instale y compruebe lo que
# usa sin depender del proveedor. Se conservan sus tres invariantes:
#
#   1. La instalación es opt-in: `NOTES_INSTALL_<HERRAMIENTA>=1`. Sin ella, una
#      herramienta que falta rehúsa con exit 2 y dice cómo reintentar.
#   2. El éxito se prueba volviendo a buscar el binario, no leyendo el exit del
#      instalador: un instalador puede salir con cero sin instalar nada.
#   3. Cada herramienta se sondea por su conducta, no por su nombre: moreutils
#      instala otro `parallel`, y un diccionario que acepta todo no mide nada.
#
# Uso: `source tools/lib/toolchain.sh` y llamar `notes_toolchain_require_<x>`.
# =============================================================================

# --- salida con color, sin emojis (la forma de THYROX logging.sh) -------------
if [[ -t 1 ]]; then
    _R="\033[0m"; _G="\033[0;32m"; _Y="\033[0;33m"; _RED="\033[0;31m"; _C="\033[0;36m"; _B="\033[1m"
else
    _R=""; _G=""; _Y=""; _RED=""; _C=""; _B=""
fi
log_header()  { echo -e "\n${_B}${_C}==> $1${_R}"; }
log_success() { echo -e "    ${_G}[OK]${_R}  $1"; }
log_info()    { echo -e "    ${_C}[..]${_R}  $1"; }
log_warn()    { echo -e "    ${_Y}[!!]${_R}  $1" >&2; }
log_error()   { echo -e "    ${_RED}[EE]${_R}  $1" >&2; }

# --- núcleo común -------------------------------------------------------------

# Rehúsa con el nombre de la llave que habilita la instalación.
_notes_refuse_opt_in() {
    echo "notes_toolchain: falta '$1' y la instalación es opt-in." >&2
    echo "                 Reintenta con NOTES_INSTALL_$2=1." >&2
}

# `_notes_ensure <binario> <LLAVE> <comando de instalación>`: resuelve el
# binario o lo instala si la llave lo permite, y vuelve a buscarlo después.
_notes_ensure() {
    local bin="$1" key="$2" cmd="$3" flag="NOTES_INSTALL_$2"
    command -v "$bin" >/dev/null 2>&1 && return 0
    if [[ "${!flag:-}" != "1" ]]; then
        _notes_refuse_opt_in "$bin" "$key"
        return 2
    fi
    $cmd >&2 2>&1 || true
    if ! command -v "$bin" >/dev/null 2>&1; then
        echo "notes_toolchain: el instalador terminó y '$bin' sigue sin resolver." >&2
        echo "                 Se vuelve a buscar el binario; no se lee el exit del instalador." >&2
        return 2
    fi
}

# --- GNU parallel ---------------------------------------------------------------

function notes_toolchain_require_parallel() {
    local bin="${NOTES_TOOLCHAIN_PARALLEL_BIN:-parallel}"
    _notes_ensure "$bin" PARALLEL "${NOTES_TOOLCHAIN_PARALLEL_INSTALL_CMD:-sudo apt-get install -y parallel}" || return 2
    # moreutils instala otro `parallel` sin `--jobs`, que es el contrato del ciclo.
    if [[ "$("$bin" --version 2>&1)" != GNU\ parallel* ]]; then
        echo "notes_toolchain: '$bin' resuelve, pero no es GNU parallel (¿moreutils?)." >&2
        return 2
    fi
    # La primera invocación bloquea esperando el aviso de la cita; un guion no
    # interactivo no puede contestarlo, así que se escribe el marcador.
    local home="${PARALLEL_HOME:-$HOME/.parallel}"
    [[ -f "$home/will-cite" ]] || { mkdir -p "$home" && : > "$home/will-cite"; }
}

# --- gawk -------------------------------------------------------------------------

# Un intervalo seguido de un grupo revienta el compilador de expresiones de
# mawk (THYROX h-docs-1068); gawk lo compila. Se mide la conducta, no el nombre.
function notes_toolchain_require_gawk() {
    local bin="${NOTES_TOOLCHAIN_AWK_BIN:-gawk}"
    _notes_ensure "$bin" GAWK "${NOTES_TOOLCHAIN_GAWK_INSTALL_CMD:-sudo apt-get install -y gawk}" || return 2
    if [[ "$(printf 'aaax\n' | "$bin" '/a.{0,3}(x)/{print "MATCH"}' 2>/dev/null)" != "MATCH" ]]; then
        echo "notes_toolchain: '$bin' no compila un intervalo seguido de un grupo." >&2
        return 2
    fi
}

# --- poppler (pdftotext, pdftoppm) ---------------------------------------------------

# PDF mínimo de la sonda de THYROX, con el texto THYROX-PDF-PROBE.
NOTES_POPPLER_PROBE_PDF_B64='JVBERi0xLjQKMSAwIG9iago8PCAvVHlwZSAvQ2F0YWxvZyAvUGFnZXMgMiAwIFIgPj4KZW5kb2JqCjIgMCBvYmoKPDwgL1R5cGUgL1BhZ2VzIC9LaWRzIFszIDAgUl0gL0NvdW50IDEgPj4KZW5kb2JqCjMgMCBvYmoKPDwgL1R5cGUgL1BhZ2UgL1BhcmVudCAyIDAgUiAvTWVkaWFCb3ggWzAgMCAyMDAgNTBdIC9Db250ZW50cyA0IDAgUiAvUmVzb3VyY2VzIDw8IC9Gb250IDw8IC9GMSA1IDAgUiA+PiA+PiA+PgplbmRvYmoKNCAwIG9iago8PCAvTGVuZ3RoIDQ2ID4+CnN0cmVhbQpCVCAvRjEgMTIgVGYgMTAgMjAgVGQgKFRIWVJPWC1QREYtUFJPQkUpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKNSAwIG9iago8PCAvVHlwZSAvRm9udCAvU3VidHlwZSAvVHlwZTEgL0Jhc2VGb250IC9IZWx2ZXRpY2EgPj4KZW5kb2JqCnhyZWYKMCA2CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAwOSAwMDAwMCBuIAowMDAwMDAwMDU4IDAwMDAwIG4gCjAwMDAwMDAxMTUgMDAwMDAgbiAKMDAwMDAwMDI0MCAwMDAwMCBuIAowMDAwMDAwMzM2IDAwMDAwIG4gCnRyYWlsZXIKPDwgL1NpemUgNiAvUm9vdCAxIDAgUiA+PgpzdGFydHhyZWYKNDA2CiUlRU9GCg=='

function notes_toolchain_require_poppler() {
    local cmd="${NOTES_TOOLCHAIN_POPPLER_INSTALL_CMD:-sudo apt-get install -y poppler-utils}" dir rc=0
    _notes_ensure pdftotext POPPLER "$cmd" || return 2
    _notes_ensure pdftoppm POPPLER "$cmd" || return 2
    dir="$(mktemp -d)" || return 2
    printf '%s' "$NOTES_POPPLER_PROBE_PDF_B64" | base64 -d > "$dir/probe.pdf"
    pdftotext "$dir/probe.pdf" - 2>/dev/null | grep -q THYROX-PDF-PROBE \
        || { echo "notes_toolchain: pdftotext no extrae el texto de la sonda." >&2; rc=2; }
    pdftoppm -png -r 20 "$dir/probe.pdf" "$dir/page" >/dev/null 2>&1
    compgen -G "$dir/page*.png" >/dev/null \
        || { echo "notes_toolchain: pdftoppm no escribió la imagen de la sonda." >&2; rc=2; }
    rm -rf "$dir"
    return "$rc"
}

# --- TeX Live para las notas zh y es-MX ------------------------------------------------

NOTES_TEXLIVE_PACKAGES="texlive-xetex texlive-latex-extra texlive-pictures texlive-fonts-recommended texlive-lang-chinese texlive-lang-spanish lmodern"

# La sonda compila la plantilla es-MX real: un `xelatex` que resuelve pero no
# tiene polyglossia en español no sirve para este ciclo.
function notes_toolchain_require_texlive() {
    local root; root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    local probe="${NOTES_TOOLCHAIN_TEXLIVE_PROBE_FILE:-$root/tools/templates/notes-template.es-mx.tex}"
    _notes_ensure xelatex TEXLIVE "${NOTES_TOOLCHAIN_TEXLIVE_INSTALL_CMD:-sudo apt-get install -y --no-install-recommends $NOTES_TEXLIVE_PACKAGES}" || return 2
    local dir; dir="$(mktemp -d)" || return 2
    (cd "$(dirname "$probe")" && timeout 300 xelatex -interaction=nonstopmode -halt-on-error \
        -output-directory "$dir" "$probe") >/dev/null 2>&1
    if [[ ! -s "$dir/$(basename "$probe" .tex).pdf" ]]; then
        echo "notes_toolchain: xelatex no compiló $(basename "$probe")." >&2
        grep -m1 -E '^! ' "$dir/$(basename "$probe" .tex).log" >&2 2>/dev/null
        rm -rf "$dir"
        return 2
    fi
    rm -rf "$dir"
}

# --- hunspell con el diccionario es_MX ------------------------------------------------

# El diccionario de ortografía (LibreOffice / RLA-ES) mide pertenencia al
# español de México, que los léxicos de spaCy no miden: ellos dan frecuencia y
# lema. La sonda exige las dos mitades: aceptar `español` y rechazar `espanol`.
function notes_toolchain_require_hunspell() {
    _notes_ensure hunspell HUNSPELL "${NOTES_TOOLCHAIN_HUNSPELL_INSTALL_CMD:-sudo apt-get install -y hunspell hunspell-es}" || return 2
    local rejected
    rejected="$(printf 'español\nespanol\n' | LANG=C.UTF-8 hunspell -i utf-8 -d es_MX -l 2>/dev/null)"
    if [[ "$rejected" != "espanol" ]]; then
        echo "notes_toolchain: hunspell es_MX no separa 'español' (válida) de 'espanol' (sin ñ)." >&2
        echo "                 Rechazó: '${rejected//$'\n'/, }'. ¿Falta hunspell-es?" >&2
        return 2
    fi
}
