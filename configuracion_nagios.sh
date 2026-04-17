#!/bin/bash
# Nagios Monitor PRO
clear
RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BLUE='\033[1;34m'; NC='\033[0m'
LOG=/var/log/nagios_monitor_pro.log
exec > >(tee -a "$LOG") 2>&1
msg(){ echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
fail(){ echo -e "${RED}✘ $1${NC}"; exit 1; }
run(){ msg "$1"; eval "$1" || fail "Error: $1"; }
CFG=/usr/local/nagios/etc/nagios.cfg
ensure_include(){ grep -q 'objects/hosts.cfg' $CFG || echo 'cfg_file=/usr/local/nagios/etc/objects/hosts.cfg' >> $CFG; }
HOSTS=/usr/local/nagios/etc/objects/hosts.cfg
CMDS=/usr/local/nagios/etc/objects/commands.cfg
CONTACTS=/usr/local/nagios/etc/objects/contacts.cfg
menu(){
 echo '===== NAGIOS MONITOR PRO ====='
 echo '1) Añadir host + ping'
 echo '2) Preparar servidor NRPE'
 echo '3) Instalar cliente NRPE por SSH'
 echo '4) Añadir checks CPU/RAM/Disco'
 echo '5) Configurar alertas por correo'
 echo '6) Ajustar hora servidor'
 echo '7) Verificar configuración'
 echo '8) Reiniciar Nagios'
 echo '9) Eliminar host'
 echo '10) Limpieza total del script'
 echo '11) Salir'
 read -p 'Opción: ' op
}
add_host(){
 ensure_include
 read -p 'Host name: ' HN; read -p 'Alias: ' AL; read -p 'IP: ' IP
cat >> $HOSTS <<EOF

define host {
 use linux-server
 host_name $HN
 alias $AL
 address $IP
}

define service {
 use generic-service
 host_name $HN
 service_description PING
 check_command check_ping!100.0,20%!500.0,60%
}
EOF
ok 'Host añadido'
}
prep_nrpe(){
 grep -q 'command_name    check_nrpe' $CMDS || cat >> $CMDS <<EOF

define command{
 command_name check_nrpe
 command_line \$USER1\$/check_nrpe -H \$HOSTADDRESS\$ -c \$ARG1\$
}
EOF
run 'apt install -y nagios-nrpe-plugin'
run 'cp /usr/lib/nagios/plugins/check_nrpe /usr/local/nagios/libexec/'
ok 'Servidor preparado'
}
client_nrpe(){
 read -p 'IP cliente: ' CIP; read -p 'Usuario SSH: ' USR; read -p 'IP servidor Nagios: ' SIP
ssh $USR@$CIP "sudo apt update && sudo apt install -y nagios-nrpe-server nagios-plugins wget && wget -O /tmp/check_mem.pl https://raw.githubusercontent.com/justintime/nagios-plugins/master/check_mem/check_mem.pl && sudo mv /tmp/check_mem.pl /usr/lib/nagios/plugins/check_mem && sudo chmod +x /usr/lib/nagios/plugins/check_mem && sudo sed -i 's/^allowed_hosts=.*/allowed_hosts=127.0.0.1,::1,$SIP/' /etc/nagios/nrpe.cfg && echo 'command[check_users]=/usr/lib/nagios/plugins/check_users -w 5 -c 10' | sudo tee -a /etc/nagios/nrpe.cfg && echo 'command[check_load]=/usr/lib/nagios/plugins/check_load -w 3,2.5,2 -c 6,5,4' | sudo tee -a /etc/nagios/nrpe.cfg && echo 'command[check_disk]=/usr/lib/nagios/plugins/check_disk -w 15% -c 5% -p /' | sudo tee -a /etc/nagios/nrpe.cfg && echo 'command[check_mem]=/usr/lib/nagios/plugins/check_mem -u -w 80 -c 90' | sudo tee -a /etc/nagios/nrpe.cfg && sudo systemctl restart nagios-nrpe-server"
ok 'Cliente configurado'
}
add_checks(){
 read -p 'Host name existente: ' HN
 while true; do
  echo '1) CPU  2) RAM  3) Disco  4) Ping  5) Usuarios  6) Salir'
  read -p 'Elegir check: ' ch
  case $ch in
   1) cat >> $HOSTS <<EOF

define service {
 use generic-service
 host_name $HN
 service_description CPU Load
 check_command check_nrpe!check_load
 contacts admin
}
EOF
;;
   2) cat >> $HOSTS <<EOF

define service {
 use generic-service
 host_name $HN
 service_description RAM
 check_command check_nrpe!check_mem
 contacts admin
}
EOF
;;
   3) cat >> $HOSTS <<EOF

define service {
 use generic-service
 host_name $HN
 service_description Disco
 check_command check_nrpe!check_disk
 contacts admin
}
EOF
;;
   4) cat >> $HOSTS <<EOF

define service {
 use generic-service
 host_name $HN
 service_description PING
 check_command check_ping!100.0,20%!500.0,60%
 contacts admin
}
EOF
;;
   5) cat >> $HOSTS <<EOF

define service {
 use generic-service
 host_name $HN
 service_description Usuarios
 check_command check_nrpe!check_users
 contacts admin
}
EOF
;;
   6) break;;
   *) echo 'Opción inválida';;
  esac
 done
 ok 'Checks añadidos'
}
mail_alert(){
 run 'apt install -y mailutils'
 read -p 'Correo destino: ' MAIL
sed -i 's/^enable_notifications=.*/enable_notifications=1/' $CFG 2>/dev/null || echo 'enable_notifications=1' >> $CFG
grep -q 'contact_name.*admin' $CONTACTS || cat >> $CONTACTS <<EOF

define contact{
 contact_name admin
 use generic-contact
 alias Administrador
 email $MAIL
 service_notification_options c
 host_notification_options d
}

define contactgroup{
 contactgroup_name admins
 alias Administradores
 members admin
}
EOF
ok 'Alertas configuradas'
}
time_fix(){ run 'timedatectl set-timezone Europe/Madrid'; run 'timedatectl set-ntp true'; }
verify(){
 ensure_include run '/usr/local/nagios/bin/nagios -v /usr/local/nagios/etc/nagios.cfg'; }
restart_n(){ run 'systemctl restart nagios'; }
del_host(){ read -p 'Host a borrar: ' HN; sed -i "/host_name[[:space:]]*$HN/,+6d" $HOSTS; ok 'Revisa services relacionados manualmente'; }
cleanup_all(){
 sed -i '/cfg_file=\/usr\/local\/nagios\/etc\/objects\/hosts.cfg/d' $CFG
 : > $HOSTS
 sed -i '/command_name check_nrpe/,+3d' $CMDS
 sed -i '/contact_name admin/,+12d' $CONTACTS
 systemctl restart nagios 2>/dev/null
 ok 'Limpieza completada'
}
while true; do menu; case $op in 1) add_host;;2) prep_nrpe;;3) client_nrpe;;4) add_checks;;5) mail_alert;;6) time_fix;;7) verify;;8) restart_n;;9) del_host;;10) cleanup_all;;11) exit;;*) echo 'Inválido';; esac; read -p 'ENTER...'; clear; done
