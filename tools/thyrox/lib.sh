# tools/thyrox/lib.sh — funciones comunes de los wrappers de ai-course-notes
# como CONSUMER de THYROX. Se carga con `source`; no se ejecuta.
#
# Opcion A: el consumer no copia la logica de THYROX, la invoca donde vive
# (`$THYROX_ROOT/bin/`). Lo unico que aporta este archivo es el entorno que
# esa invocacion necesita, y ese entorno tiene dos piezas:
#
#   THYROX_ENV_FILE     sin ella, un script de `bin/` busca el `.env` desde su
#                       propia ubicacion dentro de THYROX y no desde el
#                       consumer: `agent_store` escribiria en el store del
#                       PROVIDER (H-THYROX-178).
#   VOCAB_GATE_*        el gate de vocabulario lee sus parametros solo del
#                       entorno del proceso, nunca del `.env`.
#
# Precedencia de THYROX_ROOT: el proceso, despues el `.env` del consumer. No
# hay una tercera fuente: suponer la ubicacion de THYROX compondria una ruta
# que nadie declaro, y el fallo apareceria lejos de su causa.

# La raiz del consumer se deriva de la ubicacion de este archivo
# (`<consumer>/tools/thyrox/lib.sh`), no del cwd: un wrapper se invoca desde
# cualquier subdirectorio.
thyrox_consumer_root() {
    (cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
}

# El valor de una clave en un archivo `.env`: la ultima linea `CLAVE=valor`
# gana, igual que en el lector de THYROX. Sin la clave imprime nada.
thyrox_env_value() {
    local file="$1" key="$2"
    [[ -r "$file" ]] || return 0
    sed -n "s/^${key}=//p" "$file" | tail -n 1 | sed 's/^["'\'']//; s/["'\'']$//'
}

# Imprime un error con el prefijo del wrapper y devuelve 2: el codigo de
# «no se pudo operar», distinto del 1 de «se midio y hay hallazgos».
thyrox_refuse() {
    echo "tools/thyrox: ERROR — $*" >&2
    return 2
}

# Resuelve y exporta el entorno del consumer. Devuelve 2 si falta una
# precondicion, y en ese caso no exporta nada a medias.
thyrox_prepare_env() {
    local consumer env_file root
    consumer="$(thyrox_consumer_root)"
    env_file="$consumer/.env"

    # Sin el `.env` del consumer, THYROX resolveria cada clave desde su propio
    # `.env`: el store, los logs y el workbench serian los del PROVIDER.
    if [[ ! -f "$env_file" ]]; then
        thyrox_refuse "no existe $env_file. El consumer declara ahi THYROX_ROOT y sus hogares; sin el, THYROX usaria los suyos. Ver tools/thyrox/README.md."
        return 2
    fi

    root="${THYROX_ROOT:-$(thyrox_env_value "$env_file" THYROX_ROOT)}"
    if [[ -z "$root" ]]; then
        thyrox_refuse "THYROX_ROOT no esta declarada ni en el proceso ni en $env_file."
        return 2
    fi
    if [[ ! -f "$root/src/paths/reach.py" || ! -d "$root/bin" ]]; then
        thyrox_refuse "THYROX_ROOT=$root no es una raiz de THYROX (falta src/paths/reach.py o bin/)."
        return 2
    fi

    export THYROX_ROOT="$root"
    export THYROX_ENV_FILE="$env_file"
    export VOCAB_GATE_ROOT="$consumer"
    export VOCAB_GATE_BASELINE="$consumer/tools/thyrox/prose_vocabulary_baseline.txt"

    # `src/lib/toolchain.sh` de THYROX lee sus parametros solo del entorno del
    # proceso, no de un `.env`: sin exportarlas, las claves de la cadena de
    # herramientas que el consumer declara (paquetes de TeX, su documento de
    # prueba, los opt-in de instalacion) no llegan a los guards. El proceso
    # conserva la precedencia: una clave ya exportada no se sustituye.
    local key value
    while IFS= read -r key; do
        [[ -n "${!key:-}" ]] && continue
        value="$(thyrox_env_value "$env_file" "$key")"
        [[ -n "$value" ]] && export "$key=$value"
    done < <(sed -nE 's/^(THYROX_TOOLCHAIN_[A-Z0-9_]+|THYROX_INSTALL_[A-Z0-9_]+)=.*/\1/p' "$env_file" | sort -u)
}
