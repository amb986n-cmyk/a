#!/bin/bash
clear
RED='\033[1;31m';GREEN='\033[1;32m';BLUE='\033[1;34m';NC='\033[0m'
CFG=/usr/local/nagios/etc/nagios.cfg
HOSTS=/usr/local/nagios/etc/objects/hosts.cfg
msg(){ echo -e "${BLUE}$1${NC}"; }
ok(){ echo -e "${GREEN}$1${NC}"; }
ensure(){ grep -q 'objects/hosts.cfg' "$CFG" || echo 'cfg_file=/usr/local/nagios/etc/objects/hosts.cfg' >> "$CFG"; touch "$HOSTS"; }
verify(){ /usr/local/nagios/bin/nagios -v "$CFG"; }
restart_n(){ systemctl restart nagios; }
add_host(){ ensure; read -p 'Host name: ' H; read -p 'Alias: ' A; read -p 'IP: ' IP; cat >> "$HOSTS" <<EOF

define host {
 use linux-server
 host_name $H
 alias $A
 address $IP
}

define service {
 use generic-service
 host_name $H
 service_description PING
 check_command check_ping!100.0,20%!500.0,60%
}
EOF
ok 'Host añadido'; }
add_checks(){ ensure; read -p 'Host name existente: ' H; while true; do echo '1 CPU | 2 RAM | 3 Disco | 4 Ping | 5 Salir'; read -p 'Opción: ' c; case $c in 1) D='CPU Load';C='check_nrpe!check_load';;2) D='RAM';C='check_nrpe!check_mem';;3) D='Disco';C='check_nrpe!check_disk';;4) D='PING';C='check_ping!100.0,20%!500.0,60%';;5) break;;*) continue;; esac; cat >> "$HOSTS" <<EOF

define service {
 use generic-service
 host_name $H
 service_description $D
 check_command $C
 contacts admin
}
EOF
ok "$D añadido"; done }
del_host(){ read -p 'Host name a borrar: ' H; sed -i "/host_name $H/,+12d" "$HOSTS"; ok 'Revisado'; }
cleanup(){ echo '' > "$HOSTS"; ok 'hosts.cfg limpiado'; }
while true; do
 echo '===== NAGIOS MONITOR PRO V2 ====='
 echo '1) Añadir host'
 echo '2) Añadir checks'
 echo '3) Verificar config'
 echo '4) Reiniciar Nagios'
 echo '5) Eliminar host'
 echo '6) Limpiar hosts.cfg'
 echo '7) Salir'
 read -p 'Opción: ' op
 case "$op" in
 1) add_host ;;
 2) add_checks ;;
 3) verify ;;
 4) restart_n ;;
 5) del_host ;;
 6) cleanup ;;
 7) exit ;;
 *) echo 'Inválido' ;;
 esac
 read -p 'ENTER...'
 clear
done
