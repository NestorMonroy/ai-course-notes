# tools/thyrox/lib.sh — funciones comunes de los wrappers de ai-course-notes
# como CONSUMER de THYROX. Se carga con `source`; no se ejecuta.
#
# Opción A: el consumer no copia la lógica de THYROX, la invoca donde vive
# (`$THYROX_ROOT/bin/`). Lo único que aporta este archivo es el entorno que
# esa invocación necesita, y ese entorno tiene dos piezas:
#
#   THYROX_ENV_FILE     sin ella, un script de `bin/` busca el `.env` desde su
#                       propia ubicación dentro de THYROX y no desde el
#                       consumer: `agent_store` escribiría en el store del
#                       PROVIDER (H-THYROX-178).
#
# Precedencia de THYROX_ROOT: el proceso, después el `.env` del consumer. No
# hay una tercera fuente: suponer la ubicación de THYROX compondría una ruta
# que nadie declaro, y el fallo aparecería lejos de su causa.

# La raíz del consumer se deriva de la ubicación de este archivo
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

# Imprime un error con el prefijo del wrapper y devuelve 2: el código de
# «no se pudo operar», distinto del 1 de «se midio y hay hallazgos».
thyrox_refuse() {
    echo "tools/thyrox: ERROR — $*" >&2
    return 2
}

# Resuelve y exporta el entorno del consumer. Devuelve 2 si falta una
# precondición, y en ese caso no exporta nada a medias.
thyrox_prepare_env() {
    local consumer env_file root
    consumer="$(thyrox_consumer_root)"
    env_file="$consumer/.env"

    # Sin el `.env` del consumer, THYROX resolvería cada clave desde su propio
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

    # `src/lib/toolchain.sh` de THYROX lee sus parámetros solo del entorno del
    # proceso, no de un `.env`: sin exportarlas, las claves de la cadena de
    # herramientas que el consumer declara (paquetes de TeX, su documento de
    # prueba, los opt-in de instalación) no llegan a los guards. El proceso
    # conserva la precedencia: una clave ya exportada no se sustituye.
    local key value
    while IFS= read -r key; do
        [[ -n "${!key:-}" ]] && continue
        value="$(thyrox_env_value "$env_file" "$key")"
        [[ -n "$value" ]] && export "$key=$value"
    done < <(sed -nE 's/^(THYROX_TOOLCHAIN_[A-Z0-9_]+|THYROX_INSTALL_[A-Z0-9_]+)=.*/\1/p' "$env_file" | sort -u)
}
