#!/usr/bin/env bash
set -e

# -----------------------------
# AUTO-INTEGRACIÓN EN MENÚ
# -----------------------------

SCRIPT_PATH="$(readlink -f "$0")"
DESKTOP_FILE="$HOME/.local/share/applications/gestor-software.desktop"

if [ ! -f "$DESKTOP_FILE" ]; then
    mkdir -p "$HOME/.local/share/applications"

    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Gestor de Software
Comment=Instalar y desinstalar paquetes (pacman + flatpak + yay)
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

for cmd in fzf pacman; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "Falta dependencia: $cmd"
        exit 1
    }
done

HAS_FLATPAK=0
HAS_YAY=0

command -v flatpak >/dev/null 2>&1 && HAS_FLATPAK=1
command -v yay >/dev/null 2>&1 && HAS_YAY=1

# -----------------------------
# FUNCIONES
# -----------------------------

instalar_paquete() {

    echo "Cargando paquetes disponibles..."

    pacman_list=$(pacman -Sl | awk '{print $2 " | pacman"}')

    yay_list=""
    if [ "$HAS_YAY" -eq 1 ]; then
        yay_list=$(yay -Sl 2>/dev/null | awk '{print $2 " | aur"}')
    fi

    flatpak_list=""
    if [ "$HAS_FLATPAK" -eq 1 ]; then
        flatpak_list=$(flatpak remote-ls --app | awk '{print $1 " | flatpak"}')
    fi

    selected=$(
        printf "%s\n%s\n%s\n" "$pacman_list" "$yay_list" "$flatpak_list" |
        sort -u |
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
        aur)
            yay -S "$pkg"
            ;;
        flatpak)
            flatpak install -y "$pkg"
            ;;
    esac
}

desinstalar_paquete() {

    echo "Cargando paquetes instalados..."

    pacman_list=$(pacman -Qq | awk '{print $1 " | pacman"}')

    yay_list=""
    if [ "$HAS_YAY" -eq 1 ]; then
        yay_list=$(yay -Qm 2>/dev/null | awk '{print $1 " | aur"}')
    fi

    flatpak_list=""
    if [ "$HAS_FLATPAK" -eq 1 ]; then
        flatpak_list=$(flatpak list --app --columns=application | awk '{print $1 " | flatpak"}')
    fi

    selected=$(
        printf "%s\n%s\n%s\n" "$pacman_list" "$yay_list" "$flatpak_list" |
        sort -u |
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
        aur)
            yay -Rns "$pkg"
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
        "Instalar software") instalar_paquete ;;
        "Desinstalar software") desinstalar_paquete ;;
        "Salir"|"" ) exit 0 ;;
    esac

    echo
    read -rp "Pulsa ENTER para continuar..."
done
