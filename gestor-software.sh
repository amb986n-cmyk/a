#!/usr/bin/env bash

set -e

# -----------------------------
# AUTO-INTEGRACIÓN EN MENÚ (SOLO 1ª VEZ)
# -----------------------------

SCRIPT_PATH="$(readlink -f "$0")"
DESKTOP_FILE="$HOME/.local/share/applications/gestor-software.desktop"

if [ ! -f "$DESKTOP_FILE" ]; then

    mkdir -p "$HOME/.local/share/applications"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Gestor de Software
Comment=Instalar y desinstalar paquetes (pacman + flatpak)
Exec=lxterminal -e bash -c \"$SCRIPT_PATH; exec bash\"
Icon=system-software-install
Categories=System;
Terminal=false
EOF

    chmod +x "$DESKTOP_FILE"
fi


# -----------------------------
# DEPENDENCIAS
# -----------------------------

if ! command -v fzf >/dev/null 2>&1; then
    echo "Error: fzf no está instalado."
    exit 1
fi


# -----------------------------
# FUNCIONES
# -----------------------------

instalar_paquete() {

    echo "Cargando paquetes disponibles..."

    pacman_list=$(pacman -Sl | awk '{print $2 " | pacman"}' | sort -u)

    if command -v flatpak >/dev/null 2>&1; then
        flatpak_list=$(flatpak remote-ls --app | awk '{print $1 " | flatpak"}')
    else
        flatpak_list=""
    fi

    selected=$(
        printf "%s\n%s\n" "$pacman_list" "$flatpak_list" |
        fzf --prompt="Instalar > " --height=40% --border --layout=reverse
    )

    [ -z "$selected" ] && return

    pkg=$(echo "$selected" | cut -d'|' -f1 | xargs)
    origin=$(echo "$selected" | cut -d'|' -f2 | xargs)

    echo
    echo "Instalando: $pkg ($origin)"
    echo

    case "$origin" in
        pacman)
            sudo pacman -S "$pkg"
            ;;
        flatpak)
            flatpak install -y "$pkg"
            ;;
    esac
}


desinstalar_paquete() {

    echo "Cargando paquetes instalados..."

    pacman_list=$(pacman -Qq | awk '{print $1 " | pacman"}')

    if command -v flatpak >/dev/null 2>&1; then
        flatpak_list=$(flatpak list --app --columns=application | awk '{print $1 " | flatpak"}')
    else
        flatpak_list=""
    fi

    selected=$(
        printf "%s\n%s\n" "$pacman_list" "$flatpak_list" |
        fzf --prompt="Desinstalar > " --height=40% --border --layout=reverse
    )

    [ -z "$selected" ] && return

    pkg=$(echo "$selected" | cut -d'|' -f1 | xargs)
    origin=$(echo "$selected" | cut -d'|' -f2 | xargs)

    echo
    echo "Desinstalando: $pkg ($origin)"
    echo

    case "$origin" in
        pacman)
            sudo pacman -Rns "$pkg"
            ;;
        flatpak)
            flatpak uninstall -y "$pkg"
            ;;
    esac
}


# -----------------------------
# MENÚ PRINCIPAL
# -----------------------------

while true; do

    accion=$(
        printf "Instalar software\nDesinstalar software\nSalir\n" |
        fzf --prompt="Gestor de Software > " --height=30% --border --layout=reverse
    )

    case "$accion" in
        "Instalar software")
            instalar_paquete
            ;;
        "Desinstalar software")
            desinstalar_paquete
            ;;
        "Salir"|"")
            exit 0
            ;;
    esac

    echo
    read -rp "Pulsa ENTER para continuar..."
done
