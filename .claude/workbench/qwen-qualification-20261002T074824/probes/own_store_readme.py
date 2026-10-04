"""El README de tools/thyrox declara el store de agentes propio de ai-course-notes."""
from pathlib import Path

README = Path("/home/user/ai-course-notes/tools/thyrox/README.md")
OLD = """## Sin store de agentes

Este consumer no tiene store de agentes. `tools/thyrox/run` niega
`agent_store`, `task_ids` y `hallazgo_ids` mientras el `.env` no declare
`THYROX_AGENT_STORE`: sin esa clave, esos comandos leerían o escribirían el
store de THYROX (H-THYROX-178), que es un ejemplo del mecanismo y no se llena
desde aquí. Declararla los habilita contra el store que nombre.
"""
NEW = """## Store de agentes propio

El store de agentes de este consumer es `agent-results/agent_store.sqlite3`, en
la raíz de ESTE repositorio: es de ai-course-notes, no de THYROX. El `.env` lo
declara con `THYROX_AGENT_STORE=<consumer>/agent-results/agent_store.sqlite3`.
`tools/thyrox/run` sigue negando `agent_store`, `task_ids` y `hallazgo_ids` si
esa clave falta: sin ella leerían o escribirían el store de THYROX
(H-THYROX-178), que no se llena desde aquí.
"""
text = README.read_text(encoding="utf-8")
assert text.count(OLD) == 1
README.write_text(text.replace(OLD, NEW), encoding="utf-8")
