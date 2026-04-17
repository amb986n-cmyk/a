#!/bin/bash
# Abrir Weston sobre X11
weston --backend=x11-backend.so --width=1920 --height=1080 --socket=wayland-1 &
WESTON_PID=$!

# Abrir una nueva terminal y ejecutar Waydroid UI
gnome-terminal -- bash -c "export WAYLAND_DISPLAY=wayland-1; waydroid show-full-ui; exec bash"
gnome-terminal -- bash -c "firewall-cmd --zone=trusted --add-interface=waydroid0; exec bash"
# Esperar a que Weston termine

