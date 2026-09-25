#!/usr/bin/env python3
"""Propone una fila del glosario es-MX para un termino técnico en ingles.

Consulta IATE (la base terminologica de la Union Europea) y los léxicos de
spacy-lookups-data, e imprime una fila CANDIDATA para revisar. Nunca escribe en
`tools/lang/es-mx/glossary.tsv`: la decisión es de quien revisa.

Por que no decide sola: IATE compara la forma escrita, no el significado.
Medido al escribir este script, sin filtro de dominio `embedding` da
`imbibición` (química), `checkpoint` da `puesto fronterizo` y `transformer` da
`transformador de potencia`. El filtro de informática retira esos, pero no
basta: `transformer` sigue dando `transformador` dentro de informática, y en
estas notas Transformer es el nombre de una arquitectura.

Por eso la propuesta por defecto es `keep` (la regla de redacción: los términos
técnicos se quedan en ingles), las formas de dominios ajenos a la informática
van a `rejected`, y las de informática se muestran como comentario para que
quien revisa decida si alguna es la traducción correcta.

    uv run python tools/scripts/suggest_term.py embedding checkpoint
    uv run python tools/scripts/suggest_term.py embedding --iate-response respuesta.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

IATE_SEARCH = "https://iate.europa.eu/em-api/entries/_search?expand=true&limit=20"

# Dominios de IATE que cuentan como informática. El segundo entra porque ahí
# vive `overfitting` -> `sobreajuste`, medido al escribir el filtro.
COMPUTING_DOMAINS = (
    "information technology and data processing",
    "information and information processing",
    "artificial intelligence",
)


@dataclass(frozen=True)
class Candidate:
    code: str
    en_terms: tuple[str, ...]
    es_terms: tuple[str, ...]
    domains: tuple[str, ...]
    computing: bool


def read_response(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fetch_response(term: str) -> dict:
    body = {"query": term, "source": "en", "targets": ["es"],
            "search_in_fields": [0], "search_in_term_types": [0, 1, 2, 3, 4]}
    request = urllib.request.Request(IATE_SEARCH, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def iate_candidates(payload: dict, term: str) -> list[Candidate]:
    """Las entradas cuyo termino ingles es exactamente `term`, con su dominio."""
    wanted = term.strip().lower()
    out: list[Candidate] = []
    for item in payload.get("items", []):
        language = item.get("language", {})
        en = tuple(t.get("term_value", "") for t in language.get("en", {}).get("term_entries", []))
        if wanted not in (e.lower() for e in en):
            continue
        es = tuple(t.get("term_value", "") for t in language.get("es", {}).get("term_entries", []))
        domains = tuple(
            " > ".join([*(d.get("domain", {}).get("path") or []), d.get("domain", {}).get("name") or ""]).strip(" >")
            for d in item.get("domains", [])
        )
        computing = any(marker in domain.lower() for domain in domains for marker in COMPUTING_DOMAINS)
        out.append(Candidate(item.get("code", ""), en, es, domains, computing))
    return out


def suggest_row(term: str, candidates: list[Candidate]) -> dict[str, str]:
    """La fila candidata: `keep`, con las formas de dominios ajenos rechazadas."""
    rejected: list[str] = []
    for candidate in candidates:
        if candidate.computing:
            continue
        for form in candidate.es_terms:
            # IATE marca prestamos con HTML (`<i>token</i>`) y a veces da el
            # propio termino como forma española: rechazarlo vetaría el termino.
            plain = re.sub(r"<[^>]+>", "", form).strip()
            if plain and plain.lower() != term.strip().lower() and plain not in rejected:
                rejected.append(plain)
    codes = [c.code for c in candidates if c.code]
    return {
        "term_en": term,
        "decision": "keep",
        "es_mx": "",
        "meaning": "[escriba el significado en el curso]",
        "source": "IATE:" + ",".join(codes) if codes else "IATE: sin entrada",
        "rejected": "|".join(rejected),
    }


def lexicon_note(term: str) -> str:
    try:
        import gzip
        import spacy_lookups_data
    except ModuleNotFoundError:
        return "# lexico: no disponible en este interprete (uv sync)"
    data = Path(spacy_lookups_data.__file__).parent / "data"
    probs = {}
    for lang in ("en", "es"):
        with gzip.open(data / f"{lang}_lexeme_prob.json.gz") as handle:
            probs[lang] = json.load(handle).get(term.lower())
    fmt = lambda v: "ausente" if v is None else f"{v:.2f}"
    return f"# lexico: log-prob en={fmt(probs['en'])} es={fmt(probs['es'])}"


def render(term: str, candidates: list[Candidate]) -> str:
    row = suggest_row(term, candidates)
    lines = ["# CANDIDATO — revisar antes de copiarlo a tools/lang/es-mx/glossary.tsv", lexicon_note(term)]
    computing = [c for c in candidates if c.computing]
    if computing:
        for c in computing:
            lines.append(f"# IATE informática ({c.code}): {' | '.join(c.es_terms)}  [{'; '.join(c.domains)}]")
        lines.append("# Si alguna es la traducción correcta en el curso, cambie decision a translate y es_mx.")
    else:
        lines.append("# IATE: sin entrada de informática para este término.")
    lines.append("\t".join(row[k] for k in ("term_en", "decision", "es_mx", "meaning", "source", "rejected")))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--iate-response", type=Path, help="respuesta de IATE guardada (un solo termino)")
    args = parser.parse_args(argv)
    if args.iate_response and len(args.terms) != 1:
        parser.error("--iate-response admite un solo termino")
    for term in args.terms:
        payload = read_response(args.iate_response) if args.iate_response else fetch_response(term)
        print(render(term, iate_candidates(payload, term)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
