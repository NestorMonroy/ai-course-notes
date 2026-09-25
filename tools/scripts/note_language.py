"""Perfil de idioma de las notas: las etiquetas que marcan cada rasgo didáctico.

Los scripts de QA (`check_quality.sh`, `check_note_coverage.py`,
`full_quality_audit.py`) miden rasgos didácticos contando etiquetas: `读图`
marca la explicación de una figura, `本章小结` el cierre de una sección. Esas
etiquetas son el significante; el rasgo es el significado. Una nota en español
con los mismos rasgos no contiene ninguna etiqueta en chino, y sin este perfil
habría salido como si no los tuviera.

El idioma se decide por el nombre del archivo: `*-notes.es-mx.tex` es es-mx y
cualquier otro `*-notes.tex` es zh. El perfil zh reproduce exactamente las
etiquetas y umbrales que los scripts tenían escritos.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Letras por carácter chino en texto equivalente, medido sobre README-zh.md y
# su traducción README.md: 6 320 letras latinas agregadas por 1 444 caracteres
# Han traducidos, razón 4.38. Ciega a: la prosa didáctica (el README es sobre
# todo listas y tablas) y a la variación entre notas; es una sola muestra, y la
# calibración se revisa cuando existan notas es-mx reales.
ES_MX_CHARS_PER_HAN = 4.38


@dataclass(frozen=True)
class NoteLanguage:
    code: str
    notes_glob: str
    # Clase de caracteres que cuenta como prosa.
    prose_class: str
    # Factor que convierte un umbral calibrado en caracteres chinos.
    char_scale: float
    # Expresiones regulares por rasgo didáctico.
    markers: dict[str, str] = field(default_factory=dict)
    # Palabras de transición al abrir una sección.
    bridge_words: tuple[str, ...] = ()
    # Títulos de cierre que no se evalúan como apertura de sección.
    closing_titles: tuple[str, ...] = ()
    section_summary_title: str = ""
    final_section_title: str = ""
    date_placeholder: str = ""
    missing_link_markers: tuple[str, ...] = ()
    # Términos que exigen una explicación en su primer uso, con sus pistas.
    first_use_terms: dict[str, list[str]] = field(default_factory=dict)
    # Sitio de lectura: el README del que sale el catalogo, el idioma de
    # MkDocs y las etiquetas de la interfaz. Las claves `dir:<nombre>` son los
    # nombres visibles de los directorios que no se derivan del nombre.
    site_readme: str = "README.md"
    site_language: str = "zh"
    site_labels: dict[str, str] = field(default_factory=dict)

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
    site_readme="README-zh.md",
    site_language="zh",
    site_labels={
        "footnote_interval": "视频讲解区间：{interval}。",
        "pdf_asset_title": "PDF 图示资源",
        "open_pdf": "打开 PDF 图示",
        "view_original": "查看原图",
        "missing_image": "图片资源缺失",
        "term_default": "说明",
        "tikz_title": "TikZ 图暂未渲染",
        "tikz_body": "当前构建环境没有成功生成 SVG，保留原始 TikZ 源码。",
        "unconverted_env": "未转换的 LaTeX 环境：{env}",
        "source_quote": "来源：",
        "category_default": "课程",
        "category_articles": "📝 技术文章笔记",
        "category_talks": "🎤 演讲与访谈",
        "category_other": "其他",
        "latex_source": "LaTeX 源码",
        "backup_pdf": "备用 PDF",
        "watch_video": "观看视频",
        "meta_authors": "作者/整理",
        "meta_channel": "来源",
        "meta_date": "日期",
        "meta_field": "字段",
        "meta_content": "内容",
        "course_total": "共 {count} 份讲义。",
        "course_header": "| 讲义 | 日期 | 来源 | 资源 |",
        "read": "阅读",
        "index_intro": "这里是从 `{count}` 份 LaTeX 讲义自动生成的网页阅读站。正文直接由 `.tex` 渲染成网页，适合浏览、搜索和连续阅读。",
        "index_map": "## 课程地图",
        "index_count": "{count} 份讲义",
        "index_routes": "## 推荐阅读路线",
        "route_1": "- 入门 LLM：CS336 → CS224R L09 → CS25 Karpathy Transformer 入门",
        "route_2": "- 深入 Agent：Berkeley LLM Agents → Modern Agent → Agentic RL",
        "route_3": "- 模型架构：LLM Architect → CS25 Mixtral → CS336 MoE",
        "route_4": "- 前沿洞察：Ilya → Dario → State of AI 2026",
        "nav_collapse_left": "折叠左侧导航",
        "nav_restore_left": "展开左侧导航",
        "nav_collapse_right": "折叠右侧目录",
        "nav_restore_right": "展开右侧目录",
        "theme_dark": "切换到深色模式",
        "theme_light": "切换到浅色模式",
        "nav_home": "首页",
        "nav_courses": "课程",
        "nav_overview": "概览",
        "dir:articles": "技术文章笔记",
        "dir:aitime": "AITIME 论道",
        "dir:alibaba-cloud": "阿里云",
        "dir:interviews": "访谈笔记",
        "dir:ungrounded": "Ungrounded 不着边际",
        "dir:zhang-xiaojun": "张小珺商业访谈录",
        "dir:qingke": "青稞社区",
        "dir:talks": "演讲与访谈",
    },
)

# Cada etiqueta se eligió por la función que cumple en la nota, no por la
# palabra: `本章小结` dice «resumen de este capitulo», pero cierra cada \section,
# así que su equivalente es «Resumen de la sección».
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
    site_readme="README.md",
    site_language="es",
    site_labels={
        "footnote_interval": "Intervalo del video: {interval}.",
        "pdf_asset_title": "Figura en PDF",
        "open_pdf": "Abrir la figura en PDF",
        "view_original": "Ver la imagen original",
        "missing_image": "Falta la imagen",
        "term_default": "Nota",
        "tikz_title": "Diagrama TikZ sin renderizar",
        "tikz_body": "El entorno de compilación no generó el SVG; se conserva el código TikZ original.",
        "unconverted_env": "Entorno de LaTeX sin convertir: {env}",
        "source_quote": "Fuente: ",
        "category_default": "Cursos",
        "category_articles": "📝 Notas de artículos técnicos",
        "category_talks": "🎤 Conferencias y entrevistas",
        "category_other": "Otros",
        "latex_source": "Código fuente LaTeX",
        "backup_pdf": "PDF alternativo",
        "watch_video": "Ver el video",
        "meta_authors": "Autoría",
        "meta_channel": "Fuente",
        "meta_date": "Fecha",
        "meta_field": "Campo",
        "meta_content": "Contenido",
        "course_total": "{count} notas en total.",
        "course_header": "| Nota | Fecha | Fuente | Recursos |",
        "read": "Leer",
        "index_intro": "Sitio de lectura generado automáticamente a partir de `{count}` notas en LaTeX. El texto se genera directamente desde los `.tex`, para explorar, buscar y leer de corrido.",
        "index_map": "## Mapa de cursos",
        "index_count": "{count} notas",
        "index_routes": "## Rutas de lectura recomendadas",
        "route_1": "- Introducción a LLM: CS336 → CS224R L09 → CS25 Karpathy, introducción a Transformer",
        "route_2": "- Agents a fondo: Berkeley LLM Agents → Modern Agent → Agentic RL",
        "route_3": "- Arquitectura de modelos: LLM Architect → CS25 Mixtral → CS336 MoE",
        "route_4": "- Perspectivas de frontera: Ilya → Dario → State of AI 2026",
        "nav_collapse_left": "Contraer la navegación izquierda",
        "nav_restore_left": "Mostrar la navegación izquierda",
        "nav_collapse_right": "Contraer el índice derecho",
        "nav_restore_right": "Mostrar el índice derecho",
        "theme_dark": "Cambiar al modo oscuro",
        "theme_light": "Cambiar al modo claro",
        "nav_home": "Inicio",
        "nav_courses": "Cursos",
        "nav_overview": "Vista general",
        "dir:articles": "Notas de artículos técnicos",
        "dir:aitime": "AITIME Lundao (AITIME 论道)",
        "dir:alibaba-cloud": "Alibaba Cloud (阿里云)",
        "dir:interviews": "Notas de entrevistas",
        "dir:ungrounded": "Ungrounded (不着边际)",
        "dir:zhang-xiaojun": "Entrevistas de negocios de Zhang Xiaojun (张小珺商业访谈录)",
        "dir:qingke": "Comunidad Qingke (青稞社区)",
        "dir:talks": "Conferencias y entrevistas",
    },
)

PROFILES = (ES_MX, ZH)
BY_CODE = {profile.code: profile for profile in PROFILES}


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
