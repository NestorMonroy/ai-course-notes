"""El glosario es-MX y su sugeridor de terminos.

El glosario decide, por termino tecnico, si se queda en ingles (`keep`) o se
traduce (`translate`), con su significado y las formas rechazadas. IATE propone
candidatos, pero compara la forma escrita, no el significado: `embedding` da
`imbibición` (quimica) y `transformer` da un transformador electrico. Por eso
el sugeridor filtra por dominio de informatica, propone y nunca escribe.

Las respuestas de IATE de `tests/fixtures/iate/` son reales, recortadas a los
campos que se leen.
"""
import csv
import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "tools" / "scripts" / "suggest_term.py"
GLOSSARY = REPO_ROOT / "tools" / "lang" / "es-mx" / "glossary.tsv"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "iate"
COLUMNS = ["term_en", "decision", "es_mx", "meaning", "source", "rejected"]


def load():
    spec = importlib.util.spec_from_file_location("suggest_term", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["suggest_term"] = module
    spec.loader.exec_module(module)
    return module


def test_embedding_has_no_computing_entry_and_its_chemistry_sense_is_rejected() -> None:
    st = load()
    candidates = st.iate_candidates(st.read_response(FIXTURES / "embedding.json"), "embedding")
    assert candidates, "la entrada exacta de embedding existe en la respuesta real"
    assert not [c for c in candidates if c.computing]
    row = st.suggest_row("embedding", candidates)
    assert row["decision"] == "keep"
    assert "imbibición" in row["rejected"].split("|")


def test_checkpoint_keeps_the_computing_sense_only() -> None:
    st = load()
    candidates = st.iate_candidates(st.read_response(FIXTURES / "checkpoint.json"), "checkpoint")
    computing = [c for c in candidates if c.computing]
    assert computing and "punto de control" in computing[0].es_terms
    row = st.suggest_row("checkpoint", candidates)
    assert "puesto fronterizo" in row["rejected"].split("|")
    assert row["source"].startswith("IATE:")


def test_transformer_electrical_sense_is_not_a_computing_candidate() -> None:
    st = load()
    candidates = st.iate_candidates(st.read_response(FIXTURES / "transformer.json"), "transformer")
    for c in candidates:
        if "transformador de potencia" in c.es_terms:
            assert not c.computing, c


def test_cli_prints_a_candidate_and_never_writes_the_glossary(tmp_path: Path) -> None:
    before = hashlib.sha256(GLOSSARY.read_bytes()).hexdigest()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "embedding", "--iate-response", str(FIXTURES / "embedding.json")],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("# CANDIDATO")
    assert "embedding\tkeep\t" in result.stdout
    assert hashlib.sha256(GLOSSARY.read_bytes()).hexdigest() == before


def test_glossary_is_well_formed() -> None:
    with GLOSSARY.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames == COLUMNS
        rows = list(reader)
    assert rows, "el glosario no tiene terminos"
    terms = [r["term_en"].strip().lower() for r in rows]
    assert len(terms) == len(set(terms)), "terminos duplicados"
    for r in rows:
        assert r["decision"] in {"keep", "translate"}, r
        assert r["meaning"].strip(), f"{r['term_en']}: falta el significado"
        if r["decision"] == "translate":
            assert r["es_mx"].strip(), f"{r['term_en']}: translate sin forma es-MX"
        # La ultima columna vacia puede omitirse: un tabulador final lo rechaza
        # `git diff --check`, y el lector del revisor de prosa ya lo acepta.
        rejected = [f for f in (r["rejected"] or "").split("|") if f]
        assert r["es_mx"] not in rejected, r


def test_prose_check_rejects_the_glossary_forms_in_a_note(tmp_path: Path) -> None:
    note = tmp_path / "lecture01-notes.es-mx.tex"
    note.write_text("\\documentclass{article}\n\\begin{document}\nLa imbibición de cada token tras el fine-tuning.\n\\end{document}\n",
                    encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / "scripts" / "check_prose_vocabulary.py"), "--no-baseline", str(note)],
        capture_output=True, text=True,
    )
    assert "::imbibición" in result.stdout, result.stdout
    assert "english:token" not in result.stdout
    # Un termino con guion cubre sus partes: el texto se parte en palabras por el guion.
    assert "english:fine" not in result.stdout, result.stdout


def test_suggestion_never_rejects_the_term_itself() -> None:
    """IATE registra `token` como forma espanola de `token`: rechazarla vetaria el termino."""
    st = load()
    candidates = [
        st.Candidate("x", ("token",), ("token", "<i>token</i>", "testigo"), ("TRANSPORT",), False),
    ]
    rejected = st.suggest_row("token", candidates)["rejected"].split("|")
    assert "token" not in rejected
    assert "<i>token</i>" not in rejected
    assert "testigo" in rejected
