"""Construcción de muestras canónicas del dataset zh→es-MX.

Convierte los chunks traducidos de las notas en muestras con texto fuente,
texto destino y procedencia trazable. Excluye, con una razón explícita, lo que
el verificador no aceptó, el material de terceros y los textos fuente
repetidos. Asigna los splits por documento completo de forma determinista.
Solo usa la biblioteca estándar.
"""
import hashlib

DATASET_ID = "kaupamex-ai-datasets-multilingual-to-es-mx"
LICENSE = "UNLICENSED"
SOURCE_LICENSE = "CC-BY-NC-SA-4.0"
REPOSITORY = "ai-course-notes"
THIRD_PARTY_KINDS = {"figure-text", "slide-copy"}
SPLIT_NAMES = ("train", "validation", "test")


def sha256_text(text: str) -> str:
    """Devuelve el sha256 hexadecimal del texto codificado en UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_for_document(document: str, seed) -> str:
    """Asigna un documento completo a train, validation o test.

    Usa sha256(seed + document): 80 % train, 10 % validation y 10 % test.
    """
    bucket = int(sha256_text(f"{seed}{document}"), 16) % 10
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def exclusion(chunk: dict, reason: str) -> dict:
    """Describe un chunk excluido y la razón de su exclusión."""
    return {
        "document": chunk.get("document"),
        "unit": chunk.get("unit"),
        "source_digest": sha256_text(chunk.get("zh", "")),
        "reason": reason,
    }


def build_samples(chunks, seed) -> dict:
    """Construye metadatos, muestras, splits y exclusiones a partir de chunks.

    Cada chunk lleva document, unit, zh, es, note_verdict, kind y translator.
    Las razones de exclusión son "verifier" (veredicto distinto de
    "accepted"), "third-party" (kind figure-text o slide-copy) y "duplicate"
    (zh ya visto; se conserva la primera aparición). El traductor se registra
    tal cual, sea local o no.
    """
    samples: list[dict] = []
    excluded: list[dict] = []
    seen: set[str] = set()
    splits: dict[str, list[str]] = {name: [] for name in SPLIT_NAMES}

    for chunk in chunks:
        if chunk.get("note_verdict") != "accepted":
            excluded.append(exclusion(chunk, "verifier"))
            continue
        if chunk.get("kind") in THIRD_PARTY_KINDS:
            excluded.append(exclusion(chunk, "third-party"))
            continue
        digest = sha256_text(chunk["zh"])
        if digest in seen:
            excluded.append(exclusion(chunk, "duplicate"))
            continue
        seen.add(digest)
        samples.append({
            "source": {"language": "zh", "script": "Hans", "text": chunk["zh"]},
            "target": {"language": "es", "locale": "es-MX", "text": chunk["es"]},
            "provenance": {
                "repository": REPOSITORY,
                "document": chunk["document"],
                "unit": chunk["unit"],
                "source_digest": digest,
                "translator": dict(chunk.get("translator") or {}),
            },
        })
        splits[split_for_document(chunk["document"], seed)].append(digest)

    metadata = {
        "dataset_id": DATASET_ID,
        "license": LICENSE,
        "source_license": SOURCE_LICENSE,
        "seed": seed,
        "sample_count": len(samples),
        "excluded_count": len(excluded),
    }
    return {"metadata": metadata, "samples": samples, "splits": splits, "excluded": excluded}
