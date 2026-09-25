"""Perfil de idioma de las notas: las etiquetas que marcan cada rasgo didactico.

Los scripts de QA (`check_quality.sh`, `check_note_coverage.py`,
`full_quality_audit.py`) miden rasgos didacticos contando etiquetas: `读图`
marca la explicacion de una figura, `本章小结` el cierre de una seccion. Esas
etiquetas son el significante; el rasgo es el significado. Una nota en espanol
con los mismos rasgos no contiene ninguna etiqueta en chino, y sin este perfil
habria salido como si no los tuviera.

El idioma se decide por el nombre del archivo: `*-notes.es-mx.tex` es es-mx y
cualquier otro `*-notes.tex` es zh. El perfil zh reproduce exactamente las
etiquetas y umbrales que los scripts tenian escritos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Letras por caracter chino en texto equivalente, medido sobre README-zh.md y
# su traduccion README.md: 6 320 letras latinas agregadas por 1 444 caracteres
# Han traducidos, razon 4.38. Ciega a: la prosa didactica (el README es sobre
# todo listas y tablas) y a la variacion entre notas; es una sola muestra, y la
# calibracion se revisa cuando existan notas es-mx reales.
ES_MX_CHARS_PER_HAN = 4.38


@dataclass(frozen=True)
class NoteLanguage:
    code: str
    notes_glob: str
    # Clase de caracteres que cuenta como prosa.
    prose_class: str
    # Factor que convierte un umbral calibrado en caracteres chinos.
    char_scale: float
    # Expresiones regulares por rasgo didactico.
    markers: dict[str, str] = field(default_factory=dict)
    # Palabras de transicion al abrir una seccion.
    bridge_words: tuple[str, ...] = ()
    # Titulos de cierre que no se evaluan como apertura de seccion.
    closing_titles: tuple[str, ...] = ()
    section_summary_title: str = ""
    final_section_title: str = ""
    date_placeholder: str = ""
    missing_link_markers: tuple[str, ...] = ()
    # Terminos que exigen una explicacion en su primer uso, con sus pistas.
    first_use_terms: dict[str, list[str]] = field(default_factory=dict)

    def count(self, feature: str, text: str) -> int:
        return len(re.findall(self.markers[feature], text, flags=re.I if feature == "teacher_voice" else 0))

    def prose_chars(self, text: str) -> int:
        return len(re.findall(self.prose_class, text))

    def scaled(self, threshold: int) -> int:
        return round(threshold * self.char_scale)


ZH = NoteLanguage(
    code="zh",
    notes_glob="*-notes.tex",
    prose_class=r"[一-鿿A-Za-z0-9]",
    char_scale=1.0,
    markers={
        "summary": r"本章小结|总结与延伸",
        "readfig": r"读图|怎么看|图.*说明|图.*含义",
        "readfig_strict": r"读图",
        "term_digest": r"术语消化|术语表|背景概念|什么是|概念.*解释",
        "teacher_voice": (
            r"课堂提示|老师强调|讲者强调|讲义提醒|口头|课上|经验判断|实践经验|"
            r"这里的提醒|课程提醒|老师在这里|teacher voice|speaker note"
        ),
        "symbol_words": r"其中|符号|表示|定义为|记为",
    },
    bridge_words=(
        "本节", "前面", "上一", "接下来", "现在", "因此", "所以", "换句话说", "这意味着",
        "为了", "问题", "核心", "直觉", "回到", "进一步", "从", "下面", "这里",
    ),
    closing_titles=("本章小结", "拓展阅读", "总结与延伸"),
    section_summary_title="本章小结",
    final_section_title="总结与延伸",
    date_placeholder="[在此填写日期]",
    missing_link_markers=("视频链接：未填写", "文章链接：未填写"),
    first_use_terms={
        "ZeRO": ["ZeRO-1", "Zero Redundancy", "优化器状态", "分片", "stage"],
        "sharding": ["分片", "切分", "每张 GPU", "每卡", "只存"],
        "state sharding": ["优化器状态", "梯度", "参数", "分片"],
        "fused kernel": ["融合", "合并", "减少", "显存读写", "HBM"],
        "fused kernels": ["融合", "合并", "减少", "显存读写", "HBM"],
        "collectives": ["all-reduce", "all-gather", "reduce-scatter", "集合通信", "多 GPU"],
        "DRAM": ["Dynamic", "HBM", "显存", "全称", "memory"],
        "SRAM": ["Static", "cache", "片上", "高速缓存", "全称"],
        "HBM": ["High Bandwidth", "显存", "DRAM", "带宽"],
        "optimizer state": ["Adam", "m", "v", "一阶", "二阶", "动量"],
        "Activation checkpointing": ["重算", "激活", "显存", "gradient checkpointing"],
        "activation checkpointing": ["重算", "激活", "显存", "gradient checkpointing"],
        "perplexity": ["PPL", "交叉熵", "惊讶", "选项", "exp"],
    },
)

# Cada etiqueta se eligio por la funcion que cumple en la nota, no por la
# palabra: `本章小结` dice «resumen de este capitulo», pero cierra cada \section,
# asi que su equivalente es «Resumen de la sección».
ES_MX = NoteLanguage(
    code="es-mx",
    notes_glob="*-notes.es-mx.tex",
    prose_class=r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü0-9]",
    char_scale=ES_MX_CHARS_PER_HAN,
    markers={
        "summary": r"Resumen de la sección|Síntesis y ampliación",
        "readfig": r"Lectura de la figura|[Cc]ómo leer la figura|[Qq]ué muestra la figura",
        "readfig_strict": r"Lectura de la figura",
        "term_digest": r"Términos clave|Glosario|Concepto previo|[Qq]ué es |[Qq]ué son ",
        "teacher_voice": (
            r"Nota de clase|el docente enfatiza|el docente advierte|el ponente enfatiza|"
            r"en clase|según el docente|experiencia práctica|recordatorio del curso|"
            r"teacher voice|speaker note"
        ),
        "symbol_words": r"donde |símbolo|representa|se define como|se denota",
    },
    bridge_words=(
        "En esta sección", "Antes", "Anteriormente", "A continuación", "Ahora", "Por lo tanto",
        "Por eso", "En otras palabras", "Esto significa", "Para ", "El problema", "La idea central",
        "La intuición", "Volviendo a", "Además", "Aquí", "A partir de",
    ),
    closing_titles=("Resumen de la sección", "Lecturas adicionales", "Síntesis y ampliación"),
    section_summary_title="Resumen de la sección",
    final_section_title="Síntesis y ampliación",
    date_placeholder="[Escriba aquí la fecha]",
    missing_link_markers=("Enlace del video: pendiente", "Enlace del artículo: pendiente"),
    first_use_terms={
        "ZeRO": ["ZeRO-1", "Zero Redundancy", "estado del optimizador", "sharding", "stage"],
        "sharding": ["reparte", "divide", "cada GPU", "por GPU", "solo guarda"],
        "state sharding": ["estado del optimizador", "gradientes", "parámetros", "sharding"],
        "fused kernel": ["fusiona", "combina", "reduce", "lecturas y escrituras", "HBM"],
        "fused kernels": ["fusiona", "combina", "reduce", "lecturas y escrituras", "HBM"],
        "collectives": ["all-reduce", "all-gather", "reduce-scatter", "comunicación colectiva", "varias GPU"],
        "DRAM": ["Dynamic", "HBM", "memoria de la GPU", "nombre completo", "memory"],
        "SRAM": ["Static", "cache", "en el chip", "memoria caché", "nombre completo"],
        "HBM": ["High Bandwidth", "memoria de la GPU", "DRAM", "ancho de banda"],
        "optimizer state": ["Adam", "m", "v", "primer momento", "segundo momento", "momentum"],
        "Activation checkpointing": ["recalcula", "activaciones", "memoria", "gradient checkpointing"],
        "activation checkpointing": ["recalcula", "activaciones", "memoria", "gradient checkpointing"],
        "perplexity": ["PPL", "entropía cruzada", "sorpresa", "opciones", "exp"],
    },
)

PROFILES = (ES_MX, ZH)


def for_path(path: str | Path) -> NoteLanguage:
    """El perfil de una nota por su nombre; zh es el del corpus existente."""
    name = Path(path).name
    return ES_MX if name.endswith(".es-mx.tex") else ZH


def main(argv: list[str]) -> int:
    """`note_language.py shell <archivo>`: el perfil como asignaciones de shell."""
    import shlex
    if len(argv) != 2 or argv[0] != "shell":
        print("uso: note_language.py shell <archivo.tex>")
        return 2
    lang = for_path(argv[1])
    pairs = {
        "NOTE_LANG": lang.code,
        "SUMMARY_RE": lang.markers["summary"],
        "READFIG_RE": lang.markers["readfig_strict"],
        "PROSE_CLASS": lang.prose_class,
        "PROSE_PER_FIG_MIN": str(lang.scaled(260)),
    }
    for key, value in pairs.items():
        print(f"{key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1:]))
