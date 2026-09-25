"""Relee los resultados ya pagados de la ejecución con el parser tolerante."""
import json, sys
from pathlib import Path
sys.path.insert(0, "tools/scripts")
import translate_figure_text as t
bench = Path(sys.argv[1]); table_path = Path("tools/lang/es-mx/figure_text.tsv")
table = t.read_table(table_path); before = len(table)
for index in bench.glob("translate/*/index.tsv"):
    for line in index.read_text(encoding="utf-8").splitlines():
        n, _s, item = line.partition("\t")
        requested = set(Path(item).read_text(encoding="utf-8").splitlines())
        result = json.loads((index.parent / f"{n}.json").read_text(encoding="utf-8")).get("result", "")
        table.update(t.parse_result(result, requested))
t.write_table(table_path, table)
print(f"recollect: {before} -> {len(table)} filas")
