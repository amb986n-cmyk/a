#!/usr/bin/env bash

echo "Intentando cerrar Steam correctamente..."

# intento normal primero
pkill steam

sleep 2

# si sigue vivo, forzar
if pgrep steam >/dev/null; then
    echo "Steam no responde, forzando cierre..."
    pkill -9 steam
    pkill -9 steamwebhelper
fi

echo "Listo."
