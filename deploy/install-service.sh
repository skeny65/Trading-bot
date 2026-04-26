#!/bin/bash
set -e
usuario=${1:-$USER}
ruta_proyecto="/home/$usuario/trading-bot"

if [ "$EUID" -ne 0 ]; then
    echo "Error: Ejecutar con sudo"
    exit 1
fi

echo "Instalando servicio para $usuario en $ruta_proyecto"

if [ ! -d "$ruta_proyecto" ]; then
    echo "Error: Directorio no encontrado"
    exit 1
fi

cp "$ruta_proyecto/deploy/trading-bot.service" "/etc/systemd/system/trading-bot@.service"
systemctl daemon-reload
systemctl enable "trading-bot@$usuario.service"

echo "Servicio instalado. Iniciar con: sudo systemctl start trading-bot@$usuario"