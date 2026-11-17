#!/usr/bin/env bash
# Pruebas de la API con curl (Git Bash, Linux o macOS).
# Uso:  bash evidencias/pruebas-api.sh
# Requiere que el proyecto esté levantado (docker compose up -d --build).

API=${API:-http://localhost:5000}
JSON='Content-Type: application/json'

paso() { echo; echo "=================================================================="; echo "\$ $*"; }
citar() {  # muestra los argumentos con comillas, como se escribirían en la terminal
  local salida="" a
  for a in "$@"; do
    if [[ "$a" =~ [[:space:]\{\"] ]]; then salida+=" '$a'"; else salida+=" $a"; fi
  done
  echo "${salida# }"
}
llamar() { paso "curl $(citar "$@")"; curl -s -w "\n--> HTTP %{http_code}\n" "$@"; }

llamar "$API/health"
llamar "$API/api/ordenes"
llamar "$API/api/ordenes/1"
llamar "$API/api/ordenes/999"

# Crear una orden con dos detalles (201)
CUERPO='{"cliente":"Pedro Gomez","fecha":"2026-11-17","estado":"Pendiente","detalles":[{"producto":"Laptop","cantidad":1,"precio_unitario":15000},{"producto":"Mochila","cantidad":2,"precio_unitario":450.50}]}'
paso "curl -X POST $API/api/ordenes -H '$JSON' -d '$CUERPO'"
NUEVA=$(curl -s -w "\n--> HTTP %{http_code}" -X POST "$API/api/ordenes" -H "$JSON" -d "$CUERPO")
echo "$NUEVA"
ID=$(echo "$NUEVA" | head -n 1 | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    (orden $ID creada; total = 1 x 15000 + 2 x 450.50 = 15901)"

llamar -X POST "$API/api/ordenes" -H "$JSON" -d '{"estado":"Pagada"}'
llamar -X POST "$API/api/ordenes" -H "$JSON" -d '{"cliente":"X","estado":"Enviada"}'
llamar -X POST "$API/api/ordenes" -H "$JSON" -d 'esto no es json'

llamar -X PUT "$API/api/ordenes/$ID" -H "$JSON" -d '{"estado":"Pagada"}'
llamar -X PUT "$API/api/ordenes/999" -H "$JSON" -d '{"estado":"Pagada"}'

llamar "$API/api/ordenes/$ID/detalles"

# Agregar un detalle (201) y comprobar que el total se recalcula
CUERPO='{"producto":"Mouse","cantidad":3,"precio_unitario":100}'
paso "curl -X POST $API/api/ordenes/$ID/detalles -H '$JSON' -d '$CUERPO'"
AGREGADO=$(curl -s -w "\n--> HTTP %{http_code}" -X POST "$API/api/ordenes/$ID/detalles" -H "$JSON" -d "$CUERPO")
echo "$AGREGADO"
DET=$(echo "$AGREGADO" | head -n 1 | python -c "import sys,json; print(json.load(sys.stdin)['detalle']['id'])")
echo "    (total recalculado: 15901 + 3 x 100 = 16201)"

llamar -X POST "$API/api/ordenes/$ID/detalles" -H "$JSON" -d '{"producto":"Mouse","cantidad":0,"precio_unitario":100}'
llamar -X POST "$API/api/ordenes/999/detalles" -H "$JSON" -d '{"producto":"Mouse","cantidad":1,"precio_unitario":100}'

llamar -X PUT "$API/api/detalles/$DET" -H "$JSON" -d '{"cantidad":5}'
llamar -X PUT "$API/api/detalles/999" -H "$JSON" -d '{"cantidad":5}'

llamar -X DELETE "$API/api/detalles/$DET"
llamar -X DELETE "$API/api/detalles/$DET"

llamar -X DELETE "$API/api/ordenes/$ID"
llamar "$API/api/ordenes/$ID"
