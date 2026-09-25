#!/usr/bin/env python3
"""Vocabulario de la prosa es-MX de las notas: cuatro ejes que un solo
instrumento no cubre.

Procedencia: adaptado de THYROX `src/verify/check_vocabulario_prosa.py`
(commit 792af5f29), que aporta los dos primeros ejes, la frontera de palabra y
el rechazo sin cifra; ver `tools/lang/es-mx/PROVENANCE.md`. Lo que cambia: el
corpus son notas LaTeX, no RST, así que las exenciones de cita son las de
LaTeX; y se agregan dos ejes que el pedido de traducción exige.

=============  =================================  ==========================
Eje            Que busca                          Instrumento
=============  =================================  ==========================
`inventado`    sustantivo con sufijo nominal      léxico es: AUSENTE
               que ningún corpus atestigua
`prohibido`    cliché, coloquialismo, falso       lista cerrada + formas
               amigo, spanglish enumerado         rechazadas del glosario
`spanglish`    terminación española sobre raíz    léxicos es y en
               inglesa (`deployear`)
`english`      palabra inglesa que el glosario    léxicos es y en + glosario
               no declara como termino técnico
=============  =================================  ==========================

Lo que NO puede ver: el significado. Los cuatro ejes miden la forma. Una
palabra española correcta usada con otro sentido, un calco de sintaxis o un
termino traducido cuando debía quedarse en ingles (y que no este en el
glosario como forma rechazada) pasan. Un cero es una cota inferior.
"""
from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
LANG_DIR = REPO_ROOT / "tools" / "lang" / "es-mx"
DEFAULT_BASELINE = LANG_DIR / "prose_vocabulary_baseline.txt"
DEFAULT_FORBIDDEN = LANG_DIR / "prohibited_forms.txt"
DEFAULT_GLOSSARY = LANG_DIR / "glossary.tsv"
NOTES_GLOB = "*-notes.es-mx.tex"

# Sufijos que convierten una raíz en sustantivo abstracto (de THYROX).
NOMINAL_SUFFIX = re.compile(
    r"^[a-záéíóúñü]+"
    r"(ción|ciones|sión|siones|dad|dades|miento|mientos|anza|anzas|encia|encias)$"
)
WORD = re.compile(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]+")
ACCENTED = re.compile(r"[áéíóúñü]")

# Eje spanglish. Umbrales medidos sobre los léxicos al escribir el eje: entran
# deployear, commitear, pushear, trainear, promptear, customizar y testear
# (-14.39); quedan fuera plantear, organizar, formatear, sortear, planear y
# moldear (-13.87). El margen de testear contra moldear es estrecho.
SPANGLISH_SUFFIX = re.compile(
    r"^([a-z]{4,}?)(eando|eado|eada|eados|eadas|ear|eas|ea|ean|eamos|eo|eos|izar|izado|izada|iza|izan)$"
)
SPANGLISH_STEM_EN_MIN = -13.0
SPANGLISH_STEM_MARGIN = 1.5
SPANGLISH_WORD_ES_MAX = -14.0

# Eje english: la palabra es inglesa si el léxico ingles la atestigua con
# margen sobre el español. Es el inverso de `spanish_by_corpus` de THYROX
# (`check_identifier_language.py`), con su mismo margen de 3.0.
ENGLISH_MARGIN = 3.0
ENGLISH_MIN_LENGTH = 4
CORPUS_ABSENT = -20.0

LEXICON_PKG = "spacy-lookups-data"

# Tramos de LaTeX que no son prosa: código, URLs, rutas, matemáticas,
# referencias y los propios comandos. Una palabra ahí esta transcrita, no
# escrita (el mismo argumento que THYROX aplica a los literales de RST).
ENVIRONMENT_SPANS = re.compile(
    r"\\begin\{(lstlisting|verbatim|minted|equation\*?|align\*?|tikzpicture)\}.*?\\end\{\1\}", re.S
)
INLINE_SPANS = [
    # El nombre del entorno no es prosa; el titulo de una caja que lo sigue
    # (`\begin{knowledgebox}{Lectura de la figura: ...}`) si lo es y se mide.
    re.compile(r"\\(?:begin|end)\{[^{}]*\}"),
    re.compile(r"\\verb(.).*?\1"),
    re.compile(r"\\lstinline(.).*?\1"),
    re.compile(r"\\(?:texttt|url|nolinkurl|includegraphics|input|label|ref|eqref|cite|citep|citet|"
               r"lstinputlisting|href|videofigure|lecturefigure)(?:\[[^\]]*\])?\{[^{}]*\}"),
    re.compile(r"\\\[.*?\\\]", re.S),
    re.compile(r"\$\$.*?\$\$", re.S),
    re.compile(r"\$[^$]*\$"),
    re.compile(r"(?<!\\)%.*$", re.M),
    re.compile(r"\\[A-Za-z@]+\*?"),
]


def refuse(message: str) -> None:
    print(f"check_prose_vocabulary: ERROR — {message}", file=sys.stderr)
    print("NO se emite un conteo: un 0 aqui no distinguiria «limpio» de «no pude medir».", file=sys.stderr)
    raise SystemExit(2)


def load_lexicons() -> tuple[dict, dict]:
    """Los léxicos es y en de spacy-lookups-data (1 000 000 de formas cada uno)."""
    try:
        import spacy_lookups_data
    except ModuleNotFoundError:
        refuse(f"falta `{LEXICON_PKG}` en este interprete. Instalalo con `uv sync` "
               f"(grupo `lang` de pyproject.toml) y ejecuta con `uv run`.")
    data = pathlib.Path(spacy_lookups_data.__file__).parent / "data"

    def table(lang: str) -> dict:
        with gzip.open(data / f"{lang}_lexeme_prob.json.gz") as handle:
            return {k: v for k, v in json.load(handle).items() if not k.startswith("__")}

    return table("es"), table("en")


def load_lemmas() -> dict:
    """La tabla de lemas del español de spacy-lookups-data (forma -> lema).

    Una forma que la tabla conoce es una conjugación o flexión de una palabra
    española, aunque sea rara en el corpus de frecuencias.
    """
    import spacy_lookups_data
    data = pathlib.Path(spacy_lookups_data.__file__).parent / "data"
    with gzip.open(data / "es_lemma_lookup.json.gz") as handle:
        return json.load(handle)


def attested(word: str, lexicon: dict) -> bool:
    """¿La atestigua el corpus, en esta forma o en su singular? (de THYROX)."""
    if word in lexicon:
        return True
    if word.endswith("es") and word[:-2] in lexicon:
        return True
    return word.endswith("s") and word[:-1] in lexicon


# Prefijos cultos del español que se unen a una palabra atestiguada sin volverla
# inventada: `autoverificación`, `posentrenamiento`, `subexpresiones`,
# `retropropagación` (fase 2, cs329a). Lista cerrada: `re-`, `de-`, `des-` e
# `in-` quedan fuera porque casarían con demasiadas palabras inventadas.
PREFIXES = ("anti", "auto", "co", "contra", "hiper", "inter", "intra", "macro", "meta", "micro",
            "multi", "pos", "post", "pre", "retro", "semi", "sobre", "sub", "super")
PREFIX_BASE_MIN = 5


def prefixed_attested(word: str, es: dict) -> bool:
    """¿Es prefijo culto + una palabra que el corpus atestigua?"""
    for p in PREFIXES:
        if not word.startswith(p) or len(word) - len(p) < PREFIX_BASE_MIN:
            continue
        base = word[len(p):]
        # Tras un prefijo que acaba en vocal, la r inicial de la base se duplica:
        # auto + revisión → autorrevisión.
        if p[-1] in "aeiou" and base.startswith("rr"):
            base = base[1:]
        if attested(base, es):
            return True
    return False


# Construido desde las fuentes de RLA-ES (`tools/lang/build_hunspell_dictionary.sh`);
# su procedencia y su commit de origen están en `tools/lang/es-mx/PROVENANCE.md`.
HUNSPELL_DICTIONARY = LANG_DIR / "hunspell" / "es_MX"


class SpanishDictionary:
    """Pertenencia al español de México según hunspell es_MX (RLA-ES).

    Los léxicos de spaCy dan frecuencia y lema, no pertenencia: `compare`
    (de *comparar*) es más frecuente en inglés y `externalizar` no es clave de
    la tabla de lemas. El diccionario de ortografía sí responde si la forma
    existe. Se consulta en un solo proceso por escaneo (`hunspell -l`).
    """

    def __init__(self, words):
        words = sorted({w for w in words if w})
        if shutil.which("hunspell") is None:
            refuse("falta hunspell; corre `bash tools/setup.sh --install`.")
        result = subprocess.run(["hunspell", "-i", "utf-8", "-d", str(HUNSPELL_DICTIONARY), "-l"], input="\n".join(words),
                                capture_output=True, text=True, env={**os.environ, "LANG": "C.UTF-8"})
        self.rejected = set(result.stdout.split())
        self.known = set(words) - self.rejected

    def accepts(self, word: str) -> bool:
        return word in self.known


def strip_accents(word: str) -> str:
    """`traducción` → `traduccion`, `señal` → `senal`: la forma sin tildes ni eñe."""
    return unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode("ascii")


_ACCENTED: dict[int, dict] = {}
SPANISH_WORD = re.compile(r"[a-záéíóúüñ]+")
ACCENT_MIN_LENGTH = 3


def accented_forms(es: dict) -> dict:
    """De la forma sin tildes a la forma acentuada más frecuente del léxico."""
    key = id(es)
    if key not in _ACCENTED:
        best: dict[str, tuple[float, str]] = {}
        for word, prob in es.items():
            # Solo palabras españolas bien formadas: el léxico trae basura con
            # flechas o caracteres rotos (`reading→`) y letras sueltas.
            if len(word) < ACCENT_MIN_LENGTH or not SPANISH_WORD.fullmatch(word):
                continue
            bare = strip_accents(word)
            if bare != word and (bare not in best or prob > best[bare][0]):
                best[bare] = (prob, word)
        _ACCENTED[key] = {bare: word for bare, (_p, word) in best.items()}
    return _ACCENTED[key]


def is_spanglish(word: str, es: dict, en: dict, lemmas: dict | None = None) -> bool:
    match = SPANGLISH_SUFFIX.match(word)
    if not match:
        return False
    # Si spaCy le conoce lema, es una forma de un verbo español: `horneado`
    # (hornear), `formateado` (formatear), `sorteado` (sortear). Su rareza en el
    # corpus de frecuencias y su raíz inglesa las hacían pasar por spanglish.
    if lemmas is not None and word in lemmas:
        return False
    stem = match.group(1)
    stem_en = en.get(stem, CORPUS_ABSENT)
    stem_es = es.get(stem, CORPUS_ABSENT)
    return (
        stem_en >= SPANGLISH_STEM_EN_MIN
        and stem_en - stem_es >= SPANGLISH_STEM_MARGIN
        and es.get(word, CORPUS_ABSENT) <= SPANGLISH_WORD_ES_MAX
    )


def is_english(word: str, es: dict, en: dict) -> bool:
    if len(word) < ENGLISH_MIN_LENGTH or ACCENTED.search(word):
        return False
    here = en.get(word)
    if here is None:
        return False
    return here - es.get(word, CORPUS_ABSENT) >= ENGLISH_MARGIN


def load_glossary(path: pathlib.Path) -> tuple[set[str], list[tuple[str, str | None]]]:
    """Los términos que se quedan en ingles y las formas rechazadas.

    Cada forma rechazada entra al eje `prohibido` con el termino como
    sustituto: `imbibición` por `embedding` es un falso amigo de este corpus.
    """
    if not path.is_file():
        refuse(f"no existe el glosario {path}.")
    keep: set[str] = set()
    rejected: list[tuple[str, str | None]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            term = (row.get("term_en") or "").strip().lower()
            if not term:
                continue
            if (row.get("decision") or "").strip() == "keep":
                # El texto se parte en palabras por el guion, así que `fine-tuning`
                # tiene que cubrir también `fine` y `tuning`.
                keep.update(re.split(r"[\s-]+", term))
            target = term if (row.get("decision") or "").strip() == "keep" else (row.get("es_mx") or "").strip()
            if (row.get("decision") or "").strip() == "translate" and target:
                # La forma en español que el glosario adopta esta atestiguada por
                # su fuente (IATE, FundeuRAE); no es una palabra inventada.
                keep.update(re.split(r"[\s-]+", target.lower()))
            for form in (row.get("rejected") or "").split("|"):
                if form.strip():
                    rejected.append((form.strip().lower(), target or None))
    return keep, rejected


def load_forbidden(path: pathlib.Path) -> list[tuple[str, str | None]]:
    """`forma` o `forma → sustituto`, una por linea (de THYROX)."""
    if not path.is_file():
        refuse(f"no existe la lista de formas prohibidas {path}.")
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"\s*(?:→|->)\s*", line, maxsplit=1)
        entries.append((parts[0].strip().lower(), parts[1].strip() if len(parts) > 1 else None))
    return entries


def load_baseline(path: pathlib.Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.is_file():
        refuse(f"no existe el baseline {path}; sin el, la deuda heredada se publicaria como nueva.")
    return {l.strip() for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def prose(text: str) -> str:
    """El cuerpo del documento con los tramos que no son prosa en blanco.

    Se sustituyen por espacios del mismo largo, no se borran, para que dos
    palabras separadas por un comando no se fundan en una sola.
    """
    begin = text.find("\\begin{document}")
    body = text[begin:] if begin >= 0 else text
    blank = lambda m: " " * (m.end() - m.start())
    body = ENVIRONMENT_SPANS.sub(blank, body)
    for pattern in INLINE_SPANS:
        body = pattern.sub(blank, body)
    return body


def canonical_path(path: pathlib.Path, root: pathlib.Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(resolved)


def singular(word: str) -> str:
    """El singular ingles regular: `prompts` es el mismo termino que `prompt`."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def scan(files, es, en, forbidden, keep, root, lemmas=None):
    hits: collections.Counter = collections.Counter()
    compiled = [(form, sub, re.compile(rf"\b{re.escape(form)}\b", re.I)) for form, sub in forbidden]
    texts = [(path, prose(path.read_text(encoding="utf-8"))) for path in files]
    accented = accented_forms(es)
    words = {m.group(0).lower() for _p, t in texts for m in WORD.finditer(t)}
    dictionary = SpanishDictionary(words | {accented[w] for w in words if w in accented})
    for path, text in texts:
        key_path = canonical_path(path, root)
        for match in WORD.finditer(text):
            raw = match.group(0)
            word = raw.lower()
            if word in accented and not dictionary.accepts(word) and dictionary.accepts(accented[word]):
                hits[f"unaccented:{word}"] += 1
            elif (len(word) >= 6 and NOMINAL_SUFFIX.match(word) and word not in keep and not attested(word, es)
                    and not prefixed_attested(word, es) and not dictionary.accepts(word)):
                hits[word] += 1
            elif not dictionary.accepts(word) and is_spanglish(word, es, en, lemmas):
                hits[f"spanglish:{word}"] += 1
            elif (raw[0].islower() and singular(word) not in keep and word not in keep
                  and not dictionary.accepts(word) and is_english(word, es, en)):
                hits[f"english:{word}"] += 1
        for form, _sub, pattern in compiled:
            found = len(pattern.findall(text))
            if found:
                hits[f"{key_path}::{form}"] += found
    return hits


def git_lines(root: pathlib.Path, *args: str) -> list[str]:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        refuse(f"git {' '.join(args)} fallo: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def changed_notes(root: pathlib.Path, base: str) -> list[pathlib.Path]:
    """Las notas es-MX nuevas o modificadas contra `base`, incluidas las no versionadas."""
    git_lines(root, "rev-parse", "--verify", "-q", f"{base}^{{commit}}")
    names = set(git_lines(root, "diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD", "--", NOTES_GLOB))
    names |= set(git_lines(root, "diff", "--name-only", "--diff-filter=AMR", "HEAD", "--", NOTES_GLOB))
    names |= set(git_lines(root, "ls-files", "--others", "--exclude-standard", "--", NOTES_GLOB))
    return sorted(root / n for n in names)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="archivos concretos (default: notas es-MX cambiadas)")
    parser.add_argument("--base", default=os.environ.get("PROSE_BASE_REF", "es-mx"),
                        help="rama base para derivar el alcance (default: es-mx)")
    parser.add_argument("--baseline", type=pathlib.Path, default=DEFAULT_BASELINE)
    parser.add_argument("--no-baseline", action="store_true", help="mide el detector, no la politica")
    parser.add_argument("--forbidden", type=pathlib.Path, default=DEFAULT_FORBIDDEN)
    parser.add_argument("--glossary", type=pathlib.Path, default=DEFAULT_GLOSSARY)
    args = parser.parse_args(argv)

    es, en = load_lexicons()
    keep, rejected = load_glossary(args.glossary)
    forbidden = load_forbidden(args.forbidden) + rejected
    baseline = set() if args.no_baseline else load_baseline(args.baseline)

    if args.files:
        root = pathlib.Path.cwd().resolve()
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if top.returncode == 0:
            root = pathlib.Path(top.stdout.strip())
        files = [pathlib.Path(f) for f in args.files if pathlib.Path(f).is_file()]
    else:
        root = pathlib.Path(git_lines(pathlib.Path.cwd(), "rev-parse", "--show-toplevel")[0])
        files = changed_notes(root, args.base)
        if not files:
            print(f"check_prose_vocabulary: alcance medido: 0 archivo(s) es-MX nuevos o modificados "
                  f"contra {args.base}; no hay prosa que medir.")
            return 0

    hits = scan(files, es, en, forbidden, keep, root, load_lemmas())
    new = {k: n for k, n in hits.items() if k not in baseline}
    frozen = len(hits) - len(new)
    for key in sorted(new):
        print(f"{new[key]:6}  {key}")
    kinds = collections.Counter(
        "spanglish" if k.startswith("spanglish:") else "english" if k.startswith("english:")
        else "sin tildes" if k.startswith("unaccented:") else "prohibido" if "::" in k else "inventado"
        for k in new
    )
    print(f"{len(new)} hallazgo(s) nuevo(s): {kinds['inventado']} inventado(s) · {kinds['prohibido']} prohibido(s) · "
          f"{kinds['spanglish']} spanglish · {kinds['sin tildes']} sin tildes o eñe · {kinds['english']} en inglés sin glosario "
          f"(alcance medido: {len(files)} archivo(s); {frozen} en baseline; léxico: {len(es)} formas es, "
          f"{len(en)} en; prohibidas: {len(forbidden)}; glosario: {len(keep)} término(s) en inglés)")
    return 1 if new else 0


if __name__ == "__main__":
    raise SystemExit(main())
