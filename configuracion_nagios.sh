#!/bin/bash
# ==========================================
# NAGIOS MONITOR PRO V4
# Corrige alertas correo correctamente
# ==========================================

clear

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

NAGIOS_ETC="/usr/local/nagios/etc"
OBJ="$NAGIOS_ETC/objects"
CONTACTS="$OBJ/contacts.cfg"
HOSTS="$OBJ/hosts.cfg"
MAINCFG="$NAGIOS_ETC/nagios.cfg"

msg(){ echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
warn(){ echo -e "${YELLOW}⚠ $1${NC}"; }
fail(){ echo -e "${RED}✘ $1${NC}"; }
pause(){ read -p "ENTER para continuar..."; }

[ "$EUID" -ne 0 ] && echo "Usa sudo" && exit 1

# ==========================================
# UTILIDADES
# ==========================================

validar(){
  /usr/local/nagios/bin/nagios -v $MAINCFG >/tmp/nagioscheck.txt 2>&1
  if grep -q "Things look okay" /tmp/nagioscheck.txt; then
      ok "Configuración válida"
      systemctl restart nagios
  else
      fail "Error en configuración:"
      cat /tmp/nagioscheck.txt
  fi
}

asegurar_cfg(){
  grep -q "cfg_file=$HOSTS" "$MAINCFG" || echo "cfg_file=$HOSTS" >> "$MAINCFG"
  grep -q "cfg_file=$CONTACTS" "$MAINCFG" || echo "cfg_file=$CONTACTS" >> "$MAINCFG"
  grep -q "^enable_notifications=1" "$MAINCFG" || echo "enable_notifications=1" >> "$MAINCFG"
}

crear_hosts(){
  [ -f "$HOSTS" ] || touch "$HOSTS"
}

# ==========================================
# CORREO BIEN HECHO
# ==========================================

config_correo(){
  read -p "Correo destino alertas: " MAIL

  cp "$CONTACTS" "$CONTACTS.bak.$(date +%s)"

  # Sustituir email del contacto original nagiosadmin
  sed -i "/contact_name[[:space:]]*nagiosadmin/,/}/{s|email.*|email                           $MAIL|}" "$CONTACTS"

  # Asegurar opciones de notificación
  sed -i "/contact_name[[:space:]]*nagiosadmin/,/}/{/service_notification_options/c\        service_notification_options    w,u,c,r}" "$CONTACTS"
  sed -i "/contact_name[[:space:]]*nagiosadmin/,/}/{/host_notification_options/c\        host_notification_options       d,u,r}" "$CONTACTS"

  # Si no existen, añadir
  grep -q "service_notification_options.*w,u,c,r" "$CONTACTS" || sed -i "/contact_name[[:space:]]*nagiosadmin/,/alias/a\        service_notification_options    w,u,c,r" "$CONTACTS"
  grep -q "host_notification_options.*d,u,r" "$CONTACTS" || sed -i "/contact_name[[:space:]]*nagiosadmin/,/alias/a\        host_notification_options       d,u,r" "$CONTACTS"

  apt install -y mailutils postfix

  ok "Correo configurado en nagiosadmin -> $MAIL"
  validar
}

# ==========================================
# AÑADIR HOST
# ==========================================

add_host(){
  crear_hosts
  asegurar_cfg

  read -p "Nombre host (ej: pc1): " HN
  read -p "Alias visible: " ALIAS
  read -p "IP: " IP

cat >> "$HOSTS" <<EOF

define host{
 use                     linux-server
 host_name               $HN
 alias                   $ALIAS
 address                 $IP
 max_check_attempts      3
 check_period            24x7
 notification_interval   5
 notification_period     24x7
 contact_groups          admins
}
EOF

  ok "Host añadido"
  validar
}

# ==========================================
# CHECKS
# ==========================================

add_checks(){
  read -p "Host existente: " HN

  while true; do
    echo ""
    echo "1 Ping"
    echo "2 CPU"
    echo "3 Disco"
    echo "4 RAM"
    echo "5 Salir"
    read -p "Opción: " op

    case $op in
      1)
cat >> "$HOSTS" <<EOF

define service{
 use generic-service
 host_name $HN
 service_description PING
 check_command check_ping!100.0,20%!500.0,60%
 contacts nagiosadmin
}
EOF
;;
      2)
cat >> "$HOSTS" <<EOF

define service{
 use generic-service
 host_name $HN
 service_description CPU_Load
 check_command check_nrpe!check_load
 contacts nagiosadmin
}
EOF
;;
      3)
cat >> "$HOSTS" <<EOF

define service{
 use generic-service
 host_name $HN
 service_description Disco
 check_command check_nrpe!check_disk
 contacts nagiosadmin
}
EOF
;;
      4)
cat >> "$HOSTS" <<EOF

define service{
 use generic-service
 host_name $HN
 service_description RAM
 check_command check_nrpe!check_mem
 contacts nagiosadmin
}
EOF
;;
      5) break ;;
    esac
  done

  validar
}

# ==========================================
# LIMPIEZA TOTAL
# ==========================================

limpieza(){
  rm -f "$HOSTS"
  cp "$CONTACTS" "$CONTACTS.reset"

  sed -i "s|email.*|email                           nagios@localhost|" "$CONTACTS"

  sed -i '/cfg_file=.*hosts.cfg/d' "$MAINCFG"

  systemctl restart nagios
  ok "Sistema limpiado"
}

# ==========================================
# MENÚ
# ==========================================

while true; do
clear
echo "===== NAGIOS MONITOR PRO V4 ====="
echo "1 Configurar correo alertas"
echo "2 Añadir host"
echo "3 Añadir checks"
echo "4 Verificar config"
echo "5 Reiniciar Nagios"
echo "6 Limpieza total"
echo "7 Salir"
echo ""
read -p "Opción: " op

case $op in
1) config_correo; pause ;;
2) add_host; pause ;;
3) add_checks; pause ;;
4) validar; pause ;;
5) systemctl restart nagios; pause ;;
6) limpieza; pause ;;
7) exit ;;
*) echo "Inválido"; pause ;;
esac
done
