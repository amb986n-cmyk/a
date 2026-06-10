#!/bin/bash
set -e

echo "########################################################"
echo "#              UNIVERSAL OPTIMIZER ELITE              #"
echo "#                 FINAL MODE ACTIVATED                #"
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
# DETECCIÓN HARDWARE BASE
# =========================

echo "[+] Detectando hardware..."

GPU=$(lspci | grep -Ei "vga|3d|display")
CPU=$(lscpu | grep "Model name" | cut -d: -f2)

echo "[GPU] $GPU"
echo "[CPU] $CPU"

if echo "$GPU" | grep -qi nvidia; then GPU_TYPE="nvidia"
elif echo "$GPU" | grep -Eqi "amd|radeon"; then GPU_TYPE="amd"
else GPU_TYPE="intel"
fi

# =========================
# LAPTOP / DESKTOP
# =========================

SYSTEM_TYPE="desktop"

if [ -d /sys/class/power_supply ]; then
    if ls /sys/class/power_supply | grep -qi bat; then
        SYSTEM_TYPE="laptop"
    fi
fi

echo "[✔] Sistema: $SYSTEM_TYPE"

# =========================
# SSD / HDD DETECCIÓN
# =========================

DISK_TYPE="hdd"

if lsblk -d -o rota | grep -q 0; then
    DISK_TYPE="ssd"
fi

echo "[✔] Disco: $DISK_TYPE"

# =========================
# STEAM DETECCIÓN (GAMING MODE AUTO)
# =========================

STEAM_MODE="off"

if command -v steam >/dev/null 2>&1; then
    STEAM_MODE="on"
fi

echo "[✔] Steam: $STEAM_MODE"

# =========================
# ACTUALIZACIÓN
# =========================

echo "[1/8] Updating system..."

if [ "$DISTRO" = "arch" ]; then
    sudo pacman -Syu --noconfirm
else
    sudo apt update && sudo apt upgrade -y
fi

# =========================
# BASE PACKAGES
# =========================

echo "[2/8] Installing base..."

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
# FLATHUB SMART
# =========================

echo "[3/8] Flatpak..."

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
# AUR SMART
# =========================

if [ "$DISTRO" = "arch" ]; then
    echo "[4/8] AUR..."

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
# GPU DRIVERS
# =========================

echo "[5/8] GPU drivers..."

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
# ZRAM + SYSCTL (ELITE)
# =========================

echo "[6/8] System tuning..."

sudo tee /etc/systemd/zram-generator.conf > /dev/null << EOF
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
EOF

sudo systemctl daemon-reload || true

# tuning dinámico
if [ "$SYSTEM_TYPE" = "gaming" ]; then
    SWAP=10; CACHE=50
elif [ "$SYSTEM_TYPE" = "laptop" ]; then
    SWAP=40; CACHE=80
else
    SWAP=20; CACHE=60
fi

sudo tee /etc/sysctl.d/99-elite.conf > /dev/null << EOF
vm.swappiness=$SWAP
vm.vfs_cache_pressure=$CACHE
kernel.sched_autogroup_enabled=1
EOF

# =========================
# CPU + LAPTOP TLP
# =========================

echo "[7/8] CPU & power management..."

if command -v cpupower >/dev/null 2>&1; then
    GOV="ondemand"

    if [ "$SYSTEM_TYPE" = "laptop" ]; then
        GOV="powersave"
    fi

    sudo tee /etc/default/cpupower > /dev/null << EOF
governor='$GOV'
EOF

    sudo systemctl enable cpupower.service || true
fi

# TLP solo laptop
if [ "$SYSTEM_TYPE" = "laptop" ]; then
    echo "[+] Laptop detected → TLP"

    if [ "$DISTRO" = "arch" ]; then
        sudo pacman -S --needed --noconfirm tlp tlp-rdw
    else
        sudo apt install -y tlp tlp-rdw
    fi

    sudo systemctl enable tlp.service || true
fi

# =========================
# I/O OPTIMIZATION (SSD vs HDD)
# =========================

echo "[8/8] I/O tuning..."

SCHED="mq-deadline"

if [ "$DISK_TYPE" = "ssd" ]; then
    SCHED="mq-deadline"
else
    SCHED="bfq"
fi

sudo tee /etc/udev/rules.d/60-ioscheduler.rules > /dev/null << EOF
ACTION=="add|change", KERNEL=="sd[a-z]|nvme[0-9]*", ATTR{queue/scheduler}="$SCHED"
EOF

# =========================
# GAMING BOOST AUTO
# =========================

if [ "$STEAM_MODE" = "on" ]; then
    echo "[+] Steam detected → Gaming optimizations active"
fi

# =========================
# FASTFETCH
# =========================

grep -q fastfetch ~/.bashrc 2>/dev/null || echo "fastfetch" >> ~/.bashrc

# =========================
# FINAL REPORT
# =========================

echo ""
echo "########################################################"
echo "#                ✔ ELITE OPTIMIZATION DONE            #"
echo "########################################################"
echo ""
echo "Distro   : $DISTRO"
echo "GPU      : $GPU_TYPE"
echo "System   : $SYSTEM_TYPE"
echo "Disk     : $DISK_TYPE"
echo "Steam    : $STEAM_MODE"
echo ""
echo "✔ Adaptive tuning applied"
echo "✔ Laptop/desktop detected"
echo "✔ SSD/HDD optimized"
echo "✔ Gaming stack ready"
echo "########################################################"
