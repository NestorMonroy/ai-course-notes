#!/usr/bin/env python3
"""Check new-standard teaching coverage heuristics for a note."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from note_language import ZH, NoteLanguage, for_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check note coverage and pedagogy heuristics.")
    parser.add_argument("tex", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on warnings as well as errors.")
    return parser.parse_args()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


FIGURE_MACRO_RE = re.compile(r"\\(?:videofigure|lecturefigure)\{")


def figure_count(text: str) -> int:
    """Count raw figures or common repository figure macros without expansion."""
    return max(
        len(re.findall(r"\\includegraphics", text)),
        len(re.findall(r"\\begin\{figure\}", text)),
        len(FIGURE_MACRO_RE.findall(text)),
    )


def is_visual_line(line: str, prefer_macros: bool = False) -> bool:
    if FIGURE_MACRO_RE.search(line):
        return True
    if prefer_macros:
        return False
    return "\\includegraphics" in line or line.strip().startswith(r"\begin{figure}")


def extract_manifest_required(manifest: Path) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if not manifest or not manifest.exists():
        return rows
    for line in read(manifest).splitlines():
        if not line.startswith("| "):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0] in {"ID", "---"}:
            continue
        node_id, kind, required, _source, title = parts[:5]
        if required == "yes":
            rows.append((node_id, kind, title.replace("\\|", "|")))
    return rows


def extract_manifest_rows(manifest: Path | None) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    if not manifest or not manifest.exists():
        return rows
    for line in read(manifest).splitlines():
        if not line.startswith("| "):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 5 or parts[0] in {"ID", "---"}:
            continue
        node_id, kind, required, _source, title = parts[:5]
        rows.append((node_id, kind, required, title.replace("\\|", "|")))
    return rows


def strip_latex(line: str) -> str:
    """Return a rough prose-only version of a LaTeX line for heuristic checks."""
    line = re.sub(r"%.*$", "", line)
    line = re.sub(r"\\(?:section|subsection|caption|figsource|label)\*?(?:\[[^\]]*\])?\{[^}]*\}", " ", line)
    line = re.sub(r"\\(?:begin|end)\{[^}]*\}", " ", line)
    line = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", line)
    line = re.sub(r"[{}$^_]", " ", line)
    return re.sub(r"\s+", " ", line).strip()


def prose_char_count(lines: list[str], lang: NoteLanguage = ZH) -> int:
    chars = 0
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        if is_visual_line(line) or "\\caption" in line or "\\figsource" in line:
            continue
        if any(cmd in line for cmd in [r"\toprule", r"\midrule", r"\bottomrule", r"\endhead"]):
            continue
        # Wide tables can contain teaching information, but they are not
        # narrative prose. Count them elsewhere via boxes/term digestion.
        if "&" in line and r"\\" in line:
            continue
        cleaned = strip_latex(line)
        chars += lang.prose_chars(cleaned)
    return chars


def figure_local_explanation_counts(lines: list[str], lang: NoteLanguage = ZH) -> list[tuple[int, int]]:
    counts: list[tuple[int, int]] = []
    body_start = next(
        (idx + 1 for idx, line in enumerate(lines) if r"\begin{document}" in line),
        0,
    )
    body = lines[body_start:]
    prefer_macros = any(FIGURE_MACRO_RE.search(line) for line in body)
    prefer_graphics = not prefer_macros and any(r"\includegraphics" in line for line in body)
    for idx in range(body_start, len(lines)):
        line = lines[idx]
        if prefer_macros:
            is_visual = FIGURE_MACRO_RE.search(line) is not None
        elif prefer_graphics:
            is_visual = r"\includegraphics" in line
        else:
            is_visual = line.strip().startswith(r"\begin{figure}")
        if not is_visual:
            continue
        window = lines[max(body_start, idx - 10) : min(len(lines), idx + 24)]
        counts.append((idx + 1, prose_char_count(window, lang)))
    return counts


# Las palabras de transición viven en el perfil de idioma; el nombre se
# conserva porque es la forma en que se citaban.
BRIDGE_WORDS = ZH.bridge_words


def weak_section_openers(lines: list[str], lang: NoteLanguage = ZH) -> list[tuple[int, str]]:
    weak: list[tuple[int, str]] = []
    heading_re = re.compile(r"\\(?:section|subsection)\{([^}]*)\}")
    for idx, line in enumerate(lines):
        match = heading_re.search(line)
        if not match:
            continue
        title = match.group(1)
        if any(skip in title for skip in lang.closing_titles):
            continue
        opener_lines: list[str] = []
        first_meaningful = ""
        for raw in lines[idx + 1 : min(len(lines), idx + 12)]:
            stripped = raw.strip()
            if not stripped or stripped.startswith("%"):
                continue
            if not first_meaningful:
                first_meaningful = stripped
            if is_visual_line(stripped):
                break
            opener_lines.append(stripped)
            if prose_char_count(opener_lines, lang) >= lang.scaled(120):
                break
        opener_text = " ".join(strip_latex(x) for x in opener_lines)
        opener_chars = lang.prose_chars(opener_text)
        starts_with_visual = is_visual_line(first_meaningful)
        has_bridge = any(word in opener_text for word in lang.bridge_words)
        # A substantial prose opener is already a valid transition even when it
        # does not contain one of the small hand-written bridge-word probes.
        # Keep requiring an explicit bridge for shorter openers, and continue
        # rejecting sections that start directly with a visual.
        if starts_with_visual or opener_chars < lang.scaled(90) or (opener_chars < lang.scaled(120) and not has_bridge):
            weak.append((idx + 1, title))
    return weak


def find_first_use(text: str, term: str) -> re.Match[str] | None:
    flags = 0 if term == "ZeRO" else re.I
    pattern = rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=flags)


def main() -> None:
    args = parse_args()
    tex = args.tex
    text = read(tex)
    lang = for_path(tex)
    errors: list[str] = []
    warnings: list[str] = []
    lines = text.splitlines()

    figs = figure_count(text)
    readfig = lang.count("readfig", text)
    boxes = len(re.findall(r"\\begin\{(?:importantbox|knowledgebox|warningbox)\}", text))
    term_digest = lang.count("term_digest", text)
    teacher_voice = max(
        len(re.findall(r"\\teachervoice\{", text)),
        lang.count("teacher_voice", text),
    )
    formulas = len(re.findall(r"\\\[|\\\]|\$\$", text)) // 2 + len(re.findall(r"\\begin\{(?:align|equation)\*?\}", text))
    symbol_words = lang.count("symbol_words", text)
    code_blocks = len(re.findall(r"\\begin\{lstlisting\}", text))
    summary = lang.count("summary", text)
    prose_chars = prose_char_count(lines, lang)
    fig_local_counts = figure_local_explanation_counts(lines, lang)

    if figs >= 3 and readfig == 0:
        errors.append("figures-present-but-no-readfig-explanation")
    if figs >= 8 and readfig < 3:
        warnings.append("many-figures-but-few-readfig-explanations")
    if figs >= 12:
        prose_per_fig = prose_chars / max(1, figs)
        if prose_per_fig < lang.scaled(260):
            warnings.append(f"figure-heavy-prose-thin=chars_per_figure:{prose_per_fig:.0f}<{lang.scaled(260)}")
    if fig_local_counts:
        thin_figs = [(line_no, count) for line_no, count in fig_local_counts if count < lang.scaled(220)]
        if figs >= 8 and len(thin_figs) >= max(3, int(figs * 0.15)):
            preview = ",".join(f"L{line}:{count}" for line, count in thin_figs[:8])
            warnings.append(f"thin-local-figure-explanations={len(thin_figs)}/{figs} ({preview})")
    if boxes < 5:
        errors.append("too-few-teaching-boxes")
    if term_digest == 0:
        warnings.append("no-terminology-digestion-detected")
    manifest_rows = extract_manifest_rows(args.manifest)
    optional_text_nodes = [row for row in manifest_rows if row[1] == "text" and row[2] == "optional"]
    if len(optional_text_nodes) >= 20 and teacher_voice < 3:
        warnings.append(
            f"teacher-voice-underrepresented=markers:{teacher_voice}<3 optional_text_nodes:{len(optional_text_nodes)}"
        )
    if formulas >= 3 and symbol_words < 3:
        warnings.append("formulas-present-but-symbol-explanation-looks-thin")
    if summary < 2:
        errors.append("missing-section-or-final-summary")
    if code_blocks and "caption=" not in text:
        errors.append("code-blocks-without-captions")
    weak_openers = weak_section_openers(lines, lang)
    if weak_openers:
        preview = ",".join(f"L{line}:{title[:24]}" for line, title in weak_openers[:8])
        warnings.append(f"weak-section-openers={len(weak_openers)} ({preview})")

    first_use_terms = lang.first_use_terms
    unexplained_terms: list[str] = []
    for term, clues in first_use_terms.items():
        match = find_first_use(text, term)
        if not match:
            continue
        window = text[max(0, match.start() - 450) : min(len(text), match.end() + 700)]
        if not any(clue in window for clue in clues):
            unexplained_terms.append(term)
    if unexplained_terms:
        warnings.append("terms-appear-without-obvious-first-use-explanation=" + ",".join(sorted(set(unexplained_terms))))

    required = extract_manifest_required(args.manifest) if args.manifest else []
    if required:
        searchable_text = re.sub(r"(?m)^\s*%.*$", "", text)
        missing = []
        for node_id, kind, title in required:
            probe = title.strip("` ")
            if kind in {"slide", "figure"}:
                path = Path(probe)
                candidates = [probe, path.name, path.stem]
            else:
                candidates = [probe[:40]]
            if not any(c and c in searchable_text for c in candidates):
                missing.append((node_id, kind, title))
        if missing:
            warnings.append(f"manifest-required-nodes-not-obviously-covered={len(missing)}")
            for node_id, kind, title in missing[:20]:
                warnings.append(f"  missing? {node_id} {kind}: {title[:80]}")

    print(f"note={tex}")
    print(
        f"figs={figs} readfig={readfig} boxes={boxes} term_digest={term_digest} "
        f"teacher_voice={teacher_voice} formulas={formulas} code={code_blocks} "
        f"summaries={summary} prose_chars={prose_chars}"
    )
    for item in errors:
        print(f"ERROR {item}")
    for item in warnings:
        print(f"WARN {item}")

    if errors or (args.strict and warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
