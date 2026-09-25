#!/usr/bin/env bash
# =============================================================================
# setup.sh: prepara un clon de ai-course-notes
# =============================================================================
#
#   bash tools/setup.sh            comprueba; no instala nada del sistema
#   bash tools/setup.sh --install  instala lo que falte (apt y uv)
#
# Pasos: dependencias de Python con uv, herramientas del sistema que usan las
# notas y el ciclo de traducción es-MX (tools/lib/toolchain.sh) y las skills de
# Claude Code con sus plantillas zh y es-MX. Sin emojis: el estado va con las
# marcas [OK], [..], [!!], [EE] de THYROX, en color solo si la salida es una
# terminal.
# =============================================================================
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"
# shellcheck source=lib/toolchain.sh
source "$SCRIPT_DIR/lib/toolchain.sh"

if [[ "${1:-}" == "--install" ]]; then
    export NOTES_INSTALL_PARALLEL=1 NOTES_INSTALL_GAWK=1 NOTES_INSTALL_POPPLER=1
    export NOTES_INSTALL_TEXLIVE=1 NOTES_INSTALL_HUNSPELL=1
fi

failures=0
check() {
    local label="$1"; shift
    if "$@"; then log_success "$label"; else log_error "$label"; failures=$((failures + 1)); fi
}

log_header "Dependencias de Python (uv)"
if command -v uv >/dev/null 2>&1; then
    check "uv sync --locked" uv sync --locked --project "$REPO_ROOT" --quiet
else
    log_error "uv no está instalado: https://docs.astral.sh/uv/"
    failures=$((failures + 1))
fi

log_header "Herramientas del sistema"
check "GNU parallel" notes_toolchain_require_parallel
check "gawk" notes_toolchain_require_gawk
check "poppler (pdftotext, pdftoppm)" notes_toolchain_require_poppler
check "TeX Live con la plantilla es-MX" notes_toolchain_require_texlive
check "hunspell es_MX (RLA-ES)" notes_toolchain_require_hunspell
if ! command -v ffmpeg >/dev/null 2>&1; then
    log_warn "ffmpeg no está instalado; solo lo usan los guiones de video"
fi

log_header "Skills de Claude Code en $SKILLS_DIR"
for skill_dir in "$SCRIPT_DIR/skills"/*/; do
    skill_name="$(basename "$skill_dir")"
    target="$SKILLS_DIR/$skill_name"
    if [[ -d "$target" ]]; then
        log_warn "$skill_name ya existe; se omite (respáldalo a mano si hace falta)"
        continue
    fi
    mkdir -p "$target/assets"
    cp -r "$skill_dir"* "$target/"
    cp "$SCRIPT_DIR/templates/notes-template.tex" "$SCRIPT_DIR/templates/notes-template.es-mx.tex" "$target/assets/"
    log_success "$skill_name"
done

if (( failures > 0 )); then
    log_error "$failures paso(s) sin cumplir; con --install se instala lo que falte"
    exit 1
fi
log_success "listo"
