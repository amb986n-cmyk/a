#!/bin/bash
set -e

echo "########################################################"
echo "#        UNIVERSAL SYSTEM OPTIMIZER (DEFINITIVO)      #"
echo "########################################################"
echo ""

# =========================
# DETECCIÓN DISTRO
# =========================

if [ -f /etc/arch-release ]; then
    DISTRO="arch"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
else
    echo "[ERROR] Distro no soportada"
    exit 1
fi

echo "[✔] Distro: $DISTRO"

# =========================
# PERFIL
# =========================

echo ""
echo "Perfil:"
echo "1) performance"
echo "2) gaming"
echo "3) battery"
read -p "> " P

case $P in
    2) PROFILE="gaming" ;;
    3) PROFILE="battery" ;;
    *) PROFILE="performance" ;;
esac

echo "[✔] Perfil: $PROFILE"

# =========================
# ACTUALIZACIÓN
# =========================

echo "[1/7] Updating..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -Syu --noconfirm
else
    sudo apt update && sudo apt upgrade -y
fi

# =========================
# BASE PACKAGES
# =========================

echo "[2/7] Installing base..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -S --needed --noconfirm \
        gamemode mangohud cpupower zram-generator \
        mesa lib32-mesa vulkan-tools fastfetch
else
    sudo apt install -y \
        gamemode mangohud cpufrequtils zram-tools \
        mesa-utils vulkan-tools fastfetch
fi

# =========================
# FLATHUB (SMART)
# =========================

echo "[3/7] Flatpak..."

if command -v flatpak >/dev/null 2>&1; then
    if ! flatpak remotes | grep -q flathub; then
        echo "[+] Activando Flathub..."
        flatpak remote-add --if-not-exists flathub \
        https://flathub.org/repo/flathub.flatpakrepo
    else
        echo "[✔] Flathub OK"
    fi
fi

# =========================
# AUR (ARCH ONLY)
# =========================

if [ "$DISTRO" = "arch" ]; then
    echo "[4/7] AUR..."

    if ! command -v yay >/dev/null 2>&1; then
        echo "[+] Instalando yay..."

        sudo pacman -S --needed --noconfirm git base-devel

        tmp=$(mktemp -d)
        git clone https://aur.archlinux.org/yay.git "$tmp/yay"
        cd "$tmp/yay"
        makepkg -si --noconfirm
        cd -
        rm -rf "$tmp"
    else
        echo "[✔] yay OK"
    fi
fi

# =========================
# GPU DETECTION
# =========================

echo "[5/7] GPU..."

GPU=$(lspci | grep -Ei "vga|3d|display")

echo "$GPU"

if echo "$GPU" | grep -qi nvidia; then
    GPU_TYPE="nvidia"
elif echo "$GPU" | grep -Eqi "amd|radeon"; then
    GPU_TYPE="amd"
else
    GPU_TYPE="intel"
fi

echo "[✔] GPU: $GPU_TYPE"

# =========================
# DISCO (FIX DEFINITIVO)
# =========================

echo "[+] Detectando disco real del sistema..."

ROOT_SRC=$(findmnt -n -o SOURCE /)

# elimina partición (sda1 -> sda, nvme0n1p2 -> nvme0n1)
ROOT_DISK=$(echo "$ROOT_SRC" | sed -E 's/p?[0-9]+$//')

if [ -e "/sys/block/$(basename "$ROOT_DISK")/queue/rotational" ]; then
    ROTATIONAL=$(cat /sys/block/$(basename "$ROOT_DISK")/queue/rotational)
else
    ROTATIONAL=1
fi

if [ "$ROTATIONAL" -eq 0 ]; then
    DISK_TYPE="ssd"
else
    DISK_TYPE="hdd"
fi

echo "[✔] Disco: $ROOT_DISK ($DISK_TYPE)"

# =========================
# LAPTOP / DESKTOP
# =========================

SYSTEM_TYPE="desktop"

if [ -d /sys/class/power_supply ]; then
    ls /sys/class/power_supply | grep -qi bat && SYSTEM_TYPE="laptop"
fi

echo "[✔] Sistema: $SYSTEM_TYPE"

# =========================
# ZRAM + SYSCTL
# =========================

echo "[6/7] Tuning..."

sudo tee /etc/systemd/zram-generator.conf > /dev/null << EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF

sudo systemctl daemon-reload || true

if [ "$PROFILE" = "gaming" ]; then
    SWAP=10; CACHE=50
elif [ "$PROFILE" = "battery" ]; then
    SWAP=60; CACHE=90
else
    SWAP=20; CACHE=70
fi

sudo tee /etc/sysctl.d/99-optimizer.conf > /dev/null << EOF
vm.swappiness=$SWAP
vm.vfs_cache_pressure=$CACHE
kernel.sched_autogroup_enabled=1
EOF

# =========================
# CPU + LAPTOP POWER
# =========================

echo "[7/7] CPU & power..."

if command -v cpupower >/dev/null 2>&1; then

    GOV="ondemand"

    if [ "$PROFILE" = "gaming" ]; then
        GOV="performance"
    elif [ "$PROFILE" = "battery" ]; then
        GOV="powersave"
    fi

    sudo tee /etc/default/cpupower > /dev/null << EOF
governor='$GOV'
EOF

    sudo systemctl enable cpupower.service || true
fi

# LAPTOP POWER TOOL
if [ "$SYSTEM_TYPE" = "laptop" ]; then
    if [ "$DISTRO" = "arch" ]; then
        sudo pacman -S --needed --noconfirm tlp tlp-rdw
    else
        sudo apt install -y tlp tlp-rdw
    fi
    sudo systemctl enable tlp.service || true
fi

# =========================
# GPU DRIVERS
# =========================

if [ "$DISTRO" = "arch" ]; then
    case $GPU_TYPE in
        nvidia) sudo pacman -S --needed --noconfirm nvidia-utils lib32-nvidia-utils ;;
        amd) sudo pacman -S --needed --noconfirm vulkan-radeon lib32-vulkan-radeon ;;
        intel) sudo pacman -S --needed --noconfirm vulkan-intel lib32-vulkan-intel ;;
    esac
else
    sudo apt install -y mesa-vulkan-drivers
fi

# =========================
# FINAL
# =========================

echo ""
echo "########################################################"
echo "#                 OPTIMIZACIÓN COMPLETA               #"
echo "########################################################"
echo ""
echo "Distro     : $DISTRO"
echo "Perfil     : $PROFILE"
echo "GPU        : $GPU_TYPE"
echo "Disco      : $DISK_TYPE"
echo "Sistema    : $SYSTEM_TYPE"
echo ""
echo "✔ Todo optimizado correctamente"
echo "########################################################"
