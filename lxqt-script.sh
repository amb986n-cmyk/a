#!/bin/bash

set -e

echo "========================================="
echo " CACHYOS LXQT NOIR EDITION "
echo "========================================="

echo "[1/8] Actualizando sistema..."
sudo pacman -Syu --noconfirm

echo "[2/8] Instalando software..."

sudo pacman -S --needed --noconfirm \
    flatpak \
    discover \
    packagekit-qt6 \
    flatpak-kcm \
    gamemode \
    mangohud \
    cpupower \
    zram-generator \
    firefox \
    vlc \
    qterminal \
    pcmanfm-qt \
    pavucontrol \
    ark \
    mesa \
    lib32-mesa \
    papirus-icon-theme \
    breeze \
    qt6ct \
    kvantum \
    noto-fonts \
    noto-fonts-emoji \
    ttf-jetbrains-mono \
    fastfetch \
    vulkan-tools

echo "[3/8] Configurando Flathub..."

sudo flatpak remote-add --if-not-exists flathub \
https://flathub.org/repo/flathub.flatpakrepo

echo "[4/8] Detectando GPU..."

if lspci | grep -i "vga" | grep -qi "intel"; then
    echo "GPU Intel detectada"

    sudo pacman -S --needed --noconfirm \
        vulkan-intel \
        lib32-vulkan-intel

elif lspci | grep -i "vga" | grep -Eqi "amd|radeon|ati"; then
    echo "GPU AMD detectada"

    sudo pacman -S --needed --noconfirm \
        vulkan-radeon \
        lib32-vulkan-radeon

fi

echo "[5/8] Configurando ZRAM..."

sudo tee /etc/systemd/zram-generator.conf > /dev/null << EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF

sudo systemctl daemon-reload

echo "[6/8] Optimizando memoria..."

sudo tee /etc/sysctl.d/99-performance.conf > /dev/null << EOF
vm.swappiness=10
vm.vfs_cache_pressure=50
EOF

echo "[7/8] Configurando CPU..."

sudo tee /etc/default/cpupower > /dev/null << EOF
governor='performance'
EOF

sudo systemctl enable cpupower.service

echo "[8/8] Configurando GameMode..."

mkdir -p ~/.config

cat > ~/.config/gamemode.ini << EOF
[general]
renice=10
ioprio=0

[cpu]
governor=performance

[gpu]
apply_gpu_optimisations=accept-responsibility
EOF

echo "Configurando fondo Spider-Noir..."

mkdir -p ~/.config/pcmanfm-qt/lxqt

cat > ~/.config/pcmanfm-qt/lxqt/desktop-items-0.conf << EOF
[*]
Wallpaper=$HOME/Imágenes/spider-noir.jpg
WallpaperMode=stretch
EOF

if ! grep -q "fastfetch" ~/.bashrc 2>/dev/null; then
    echo "" >> ~/.bashrc
    echo "fastfetch" >> ~/.bashrc
fi

echo ""
echo "========================================="
echo " INSTALACIÓN COMPLETADA "
echo "========================================="
echo ""
echo "GUARDA TU FONDO COMO:"
echo ""
echo "$HOME/Imágenes/spider-noir.jpg"
echo ""
echo "========================================="
echo " CONFIGURACIÓN NOIR"
echo "========================================="
echo ""
echo "Ejecuta:"
echo ""
echo "lxqt-config-appearance"
echo ""
echo "Y configura:"
echo ""
echo "Tema LXQt:"
echo "  Dark"
echo ""
echo "Tema de iconos:"
echo "  Papirus-Dark"
echo ""
echo "Fuente:"
echo "  JetBrains Mono"
echo "  Tamaño 10"
echo ""
echo "Cursor:"
echo "  Breeze"
echo ""
echo "========================================="
echo " VENTANAS OPENBOX"
echo "========================================="
echo ""
echo "Ejecuta:"
echo ""
echo "obconf-qt"
echo ""
echo "Tema recomendado:"
echo ""
echo "  Onyx"
echo ""
echo "========================================="
echo " QT6CT"
echo "========================================="
echo ""
echo "Ejecuta:"
echo ""
echo "qt6ct"
echo ""
echo "Configura:"
echo ""
echo "Style:"
echo "  Breeze"
echo ""
echo "Icon Theme:"
echo "  Papirus-Dark"
echo ""
echo "========================================="
echo " ATAJOS RECOMENDADOS"
echo "========================================="
echo ""
echo "LXQt -> Preferencias -> Teclas rápidas"
echo ""
echo "Super       -> Menú principal"
echo "Super + E   -> pcmanfm-qt"
echo "Super + T   -> qterminal"
echo "Super + D   -> Mostrar escritorio"
echo "Super + L   -> Bloquear pantalla"
echo ""
echo "========================================="
echo " GAMING"
echo "========================================="
echo ""
echo "Steam:"
echo "gamemoderun %command%"
echo ""
echo "========================================="
echo " HDD"
echo "========================================="
echo ""
echo "Añadir manualmente:"
echo "noatime"
echo ""
echo "en /etc/fstab"
echo ""
echo "========================================="
echo ""

read -p "¿Abrir configuración de apariencia ahora? (s/n): " RESP

if [[ $RESP =~ ^[Ss]$ ]]; then
    lxqt-config-appearance &
    sleep 2
    obconf-qt &
    sleep 2
    qt6ct &
fi

echo ""
echo "Reinicia el equipo cuando termines."
echo "========================================="
