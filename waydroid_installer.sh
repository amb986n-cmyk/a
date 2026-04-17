#!/bin/bash
clear
GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'
run(){ echo -e "${BLUE}>> $1${NC}"; eval "$1" || { echo -e "${RED}Error${NC}"; exit 1; }; }
echo -e "${GREEN}=== INSTALADOR WAYDROID + WESTON ===${NC}"
read -p "Pulsa ENTER para continuar..."
[ "$EUID" -ne 0 ] && echo "Ejecuta con sudo" && exit 1
run "apt update"
run "apt install -y curl ca-certificates weston"
run "curl -s https://repo.waydro.id | bash"
run "apt install -y waydroid"
run "waydroid init"
echo -e "${GREEN}Instalación completada.${NC}"
echo "Inicia entorno gráfico con: weston"
echo "Luego inicia Waydroid con: waydroid session start && waydroid show-full-ui"
