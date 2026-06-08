#!/usr/bin/env bash

# Requiere fzf (sudo pacman -S fzf)

# Obtener lista de paquetes pacman
pacman_list=$(pacman -Qq | awk '{print $1" | pacman"}')

# Obtener lista de flatpaks
if command -v flatpak >/dev/null 2>&1; then
    flatpak_list=$(flatpak list --app | awk '{print $1" | flatpak"}')
else
    flatpak_list=""
fi

# Unir listas
all_packages=$(printf "%s\n%s\n" "$pacman_list" "$flatpak_list")

# Abrir buscador
selected=$(echo "$all_packages" | fzf --prompt="Buscar paquete: " --height=40% --border --layout=reverse)

# Si no seleccionó nada
[ -z "$selected" ] && exit 0

# Extraer nombre y origen
pkg=$(echo "$selected" | awk -F " | " '{print $1}')
origin=$(echo "$selected" | awk -F " | " '{print $3}')

echo "Seleccionado: $pkg ($origin)"
echo

# Desinstalar según origen
case "$origin" in
    pacman)
        sudo pacman -Rns "$pkg"
        ;;
    flatpak)
        flatpak uninstall -y "$pkg"
        ;;
esac
