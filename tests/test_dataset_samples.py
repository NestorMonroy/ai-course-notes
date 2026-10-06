"""Muestras canónicas del dataset es-MX a partir de traducciones locales aceptadas.

Cada chunk aceptado por el verificador se convierte en una muestra con fuente,
destino y procedencia trazable. Lo rechazado, lo de terceros y lo duplicado se
excluye con una razón explícita, y los splits se asignan por documento.
"""
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools" / "scripts"))

import dataset_samples  # noqa: E402

TRANSLATOR = {
    "model": "qwen3-14b-instruct",
    "artifact_sha256": "a" * 64,
    "profile": "notes-es-mx",
    "local": True,
}


def chunk(document="cs329a/lecture01", unit="u001", zh="模型在推理时进行搜索。",
          es="El modelo hace búsqueda durante la inferencia.", note_verdict="accepted",
          kind="prose", translator=None) -> dict:
    return {
        "document": document,
        "unit": unit,
        "zh": zh,
        "es": es,
        "note_verdict": note_verdict,
        "kind": kind,
        "translator": dict(translator if translator is not None else TRANSLATOR),
    }


def reasons(result: dict) -> list[str]:
    return [e["reason"] for e in result["excluded"]]


def test_accepted_local_prose_chunk_gives_one_sample():
    c = chunk()
    result = dataset_samples.build_samples([c], seed=7)
    assert len(result["samples"]) == 1
    sample = result["samples"][0]
    assert sample["source"] == {"language": "zh", "script": "Hans", "text": c["zh"]}
    assert sample["target"] == {"language": "es", "locale": "es-MX", "text": c["es"]}
    prov = sample["provenance"]
    assert prov["repository"] == "ai-course-notes"
    assert prov["document"] == c["document"]
    assert prov["unit"] == c["unit"]
    assert prov["source_digest"] == hashlib.sha256(c["zh"].encode()).hexdigest()
    assert prov["translator"] == TRANSLATOR
    assert result["excluded"] == []


def test_rejected_chunk_is_excluded_by_verifier():
    result = dataset_samples.build_samples([chunk(note_verdict="rejected")], seed=7)
    assert result["samples"] == []
    assert reasons(result) == ["verifier"]


def test_non_local_translator_is_kept_and_recorded():
    remote = dict(TRANSLATOR, local=False)
    result = dataset_samples.build_samples([chunk(translator=remote)], seed=7)
    assert result["excluded"] == []
    assert len(result["samples"]) == 1
    assert result["samples"][0]["provenance"]["translator"]["local"] is False


def test_figure_text_and_slide_copy_are_third_party():
    chunks = [
        chunk(unit="u001", zh="图一：搜索树", kind="figure-text"),
        chunk(unit="u002", zh="幻灯片标题", kind="slide-copy"),
    ]
    result = dataset_samples.build_samples(chunks, seed=7)
    assert result["samples"] == []
    assert reasons(result) == ["third-party", "third-party"]


def test_duplicate_zh_keeps_first_only():
    first = chunk(unit="u001", es="Primera traducción.")
    second = chunk(document="cs329a/lecture02", unit="u009", es="Segunda traducción.")
    result = dataset_samples.build_samples([first, second], seed=7)
    assert len(result["samples"]) == 1
    assert result["samples"][0]["target"]["text"] == "Primera traducción."
    assert reasons(result) == ["duplicate"]


def test_splits_are_grouped_by_document_and_deterministic():
    chunks = [
        chunk(document=f"doc{d}", unit=f"u{u}", zh=f"文档{d}的第{u}段。", es=f"Documento {d}, párrafo {u}.")
        for d in range(3)
        for u in range(4)
    ]
    result = dataset_samples.build_samples(chunks, seed=11)
    splits = result["splits"]
    assert set(splits) <= {"train", "validation", "test"}

    by_digest = {s["provenance"]["source_digest"]: s["provenance"]["document"] for s in result["samples"]}
    split_of_document: dict[str, set[str]] = {}
    for name, members in splits.items():
        for member in members:
            digest = member if isinstance(member, str) else member["provenance"]["source_digest"]
            split_of_document.setdefault(by_digest.get(digest, digest), set()).add(name)
    for document in {f"doc{d}" for d in range(3)}:
        assert len(split_of_document.get(document, set())) == 1, document

    again = dataset_samples.build_samples(chunks, seed=11)
    assert again["splits"] == splits


def test_metadata_declares_dataset_and_licenses():
    meta = dataset_samples.build_samples([chunk()], seed=7)["metadata"]
    assert meta["dataset_id"] == "kaupamex-ai-datasets-multilingual-to-es-mx"
    assert meta["license"] == "UNLICENSED"
    assert meta["source_license"] == "CC-BY-NC-SA-4.0"
