#!/bin/bash
# Shared by the FPP command scripts (sourced, not run). fppd runs a command
# script with only MEDIADIR/FPPDIR/SCRIPTDIR set and waits for it to finish,
# so set PATH and keep every request short.

export PATH=/usr/local/bin:/usr/bin:/bin

MS_API="http://localhost/api/plugin/fpp-matrixscroller"

# ms_post <endpoint> <json body>
ms_post() {
    curl -sf --connect-timeout 3 --max-time 5 -X POST "$MS_API/$1" \
        -H 'Content-Type: application/json' -d "$2" \
        || { echo "matrixscroller: $1 request failed" >&2; return 1; }
}

# ms_state <On|Off|Toggle>  ->  true | false | "toggle" (JSON)
ms_state() {
    case "$(echo "$1" | tr '[:upper:]' '[:lower:]')" in
        on|true|1)  echo true ;;
        off|false|0) echo false ;;
        toggle)     echo '"toggle"' ;;
        *) echo "matrixscroller: state must be On, Off or Toggle (got '$1')" >&2; return 1 ;;
    esac
}

# ms_json_string <text>  ->  the text as a JSON string
ms_json_string() {
    python3 -c 'import json, sys; print(json.dumps(sys.argv[1]))' "$1"
}
