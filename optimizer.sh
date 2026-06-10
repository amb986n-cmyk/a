#!/bin/bash
set -e

echo "========================================="
echo "   UNIVERSAL SYSTEM OPTIMIZER PRO"
echo "        (ARCH / DEBIAN / UBUNTU)"
echo "========================================="

# =========================
# DETECCIÓN DISTRO
# =========================

if [ -f /etc/arch-release ]; then
    DISTRO="arch"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
else
    echo "Distro no soportada"
    exit 1
fi

echo "[INFO] Detectado: $DISTRO"

# =========================
# PERFIL
# =========================

echo ""
echo "Selecciona perfil:"
echo "1) performance (equilibrado rápido)"
echo "2) gaming (latencia baja)"
echo "3) battery (portátil)"
read -p "Opción: " PROFILE

# =========================
# ACTUALIZACIÓN
# =========================

echo "[1/9] Actualizando sistema..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -Syu --noconfirm
else
    sudo apt update && sudo apt upgrade -y
fi

# =========================
# BASE PACKAGES
# =========================

echo "[2/9] Instalando base..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -S --needed --noconfirm \
        flatpak gamemode mangohud cpupower zram-generator \
        mesa lib32-mesa vulkan-tools \
        fastfetch
else
    sudo apt install -y \
        flatpak gamemode mangohud cpufrequtils zram-tools \
        mesa-utils vulkan-tools fastfetch
fi

# =========================
# FLATPAK
# =========================

flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo || true

# =========================
# AUR (ARCH ONLY)
# =========================

if [ "$DISTRO" = "arch" ]; then
    echo "[3/9] AUR helper..."

    if ! command -v yay >/dev/null 2>&1; then
        sudo pacman -S --needed --noconfirm git base-devel
        tmp=$(mktemp -d)
        git clone https://aur.archlinux.org/yay.git "$tmp/yay"
        cd "$tmp/yay"
        makepkg -si --noconfirm
        cd -
        rm -rf "$tmp"
    fi
fi

# =========================
# GPU DETECTION PRO
# =========================

echo "[4/9] Detectando GPU..."

GPU=$(lspci | grep -Ei "vga|3d|display")

echo "$GPU"

if echo "$GPU" | grep -qi nvidia; then
    GPU_TYPE="nvidia"
elif echo "$GPU" | grep -Eqi "amd|radeon"; then
    GPU_TYPE="amd"
else
    GPU_TYPE="intel"
fi

echo "[INFO] GPU: $GPU_TYPE"

# =========================
# DRIVERS VULKAN
# =========================

if [ "$DISTRO" = "arch" ]; then
    case $GPU_TYPE in
        nvidia)
            sudo pacman -S --needed --noconfirm nvidia-utils lib32-nvidia-utils
            ;;
        amd)
            sudo pacman -S --needed --noconfirm vulkan-radeon lib32-vulkan-radeon
            ;;
        intel)
            sudo pacman -S --needed --noconfirm vulkan-intel lib32-vulkan-intel
            ;;
    esac
else
    sudo apt install -y mesa-vulkan-drivers
fi

# =========================
# ZRAM PRO
# =========================

echo "[5/9] ZRAM..."

sudo tee /etc/systemd/zram-generator.conf > /dev/null << EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF

sudo systemctl daemon-reload || true

# =========================
# SYSCTL PRO
# =========================

echo "[6/9] Kernel tuning..."

if [ "$PROFILE" = "gaming" ]; then
    SWAP=10
    CACHE=50
elif [ "$PROFILE" = "battery" ]; then
    SWAP=60
    CACHE=90
else
    SWAP=20
    CACHE=70
fi

sudo tee /etc/sysctl.d/99-optimizer.conf > /dev/null << EOF
vm.swappiness=$SWAP
vm.vfs_cache_pressure=$CACHE
kernel.sched_autogroup_enabled=1
EOF

# =========================
# CPU GOVERNOR PRO
# =========================

echo "[7/9] CPU governor..."

if command -v cpupower >/dev/null 2>&1; then

    if [ "$PROFILE" = "gaming" ]; then
        GOV="performance"
    elif [ "$PROFILE" = "battery" ]; then
        GOV="powersave"
    else
        GOV="ondemand"
    fi

    sudo tee /etc/default/cpupower > /dev/null << EOF
governor='$GOV'
EOF

    sudo systemctl enable cpupower.service || true
fi

# =========================
# I/O SCHEDULER TUNING
# =========================

echo "[8/9] I/O tuning..."

sudo tee /etc/udev/rules.d/60-ioscheduler.rules > /dev/null << EOF
ACTION=="add|change", KERNEL=="sd[a-z]|nvme[0-9]*", ATTR{queue/scheduler}="mq-deadline"
EOF

# =========================
# GAMING STACK CONFIG
# =========================

mkdir -p ~/.config

cat > ~/.config/gamemode.ini << EOF
[general]
renice=10
ioprio=0

[cpu]
governor=performance
EOF

# =========================
# CLEANUP
# =========================

echo "[9/9] Limpieza..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -Rns --noconfirm $(pacman -Qtdq 2>/dev/null || true) 2>/dev/null || true
else
    sudo apt autoremove -y
fi

# =========================
# FASTFETCH
# =========================

if ! grep -q "fastfetch" ~/.bashrc 2>/dev/null; then
    echo "fastfetch" >> ~/.bashrc
fi

echo ""
echo "========================================="
echo " OPTIMIZER PRO COMPLETADO"
echo "========================================="
echo ""
echo "Perfil aplicado: $PROFILE"
echo "GPU: $GPU_TYPE"
echo "Distro: $DISTRO"
echo ""
echo "✔ CPU tuning"
echo "✔ ZRAM activo"
echo "✔ GPU drivers configurados"
echo "✔ I/O scheduler optimizado"
echo "✔ Gaming stack listo"
echo "========================================="
