#!/bin/bash
clear
RED='\033[1;31m';GREEN='\033[1;32m';BLUE='\033[1;34m';YELLOW='\033[1;33m';NC='\033[0m'
CFG=/usr/local/nagios/etc/nagios.cfg
HOSTS=/usr/local/nagios/etc/objects/hosts.cfg
CMDS=/usr/local/nagios/etc/objects/commands.cfg
CONTACTS=/usr/local/nagios/etc/objects/contacts.cfg
msg(){ echo -e "${BLUE}$1${NC}"; }
ok(){ echo -e "${GREEN}$1${NC}"; }
warn(){ echo -e "${YELLOW}$1${NC}"; }
ensure(){ touch "$HOSTS"; grep -q 'objects/hosts.cfg' "$CFG" || echo 'cfg_file=/usr/local/nagios/etc/objects/hosts.cfg' >> "$CFG"; }
verify(){ /usr/local/nagios/bin/nagios -v "$CFG"; }
restart_n(){ systemctl restart nagios && ok 'Nagios reiniciado'; }
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
prep_nrpe(){ grep -q 'check_nrpe' "$CMDS" || cat >> "$CMDS" <<EOF

define command{
 command_name check_nrpe
 command_line \$USER1\$/check_nrpe -H \$HOSTADDRESS\$ -c \$ARG1\$
}
EOF
apt install -y nagios-nrpe-plugin; cp /usr/lib/nagios/plugins/check_nrpe /usr/local/nagios/libexec/; ok 'Servidor NRPE listo'; }
ssh_client(){ read -p 'IP cliente: ' IP; read -p 'Usuario SSH: ' U; read -p 'IP servidor Nagios: ' SIP; ssh $U@$IP "sudo apt update && sudo apt install -y nagios-nrpe-server nagios-plugins wget && wget -O /tmp/check_mem.pl https://raw.githubusercontent.com/justintime/nagios-plugins/master/check_mem/check_mem.pl && sudo mv /tmp/check_mem.pl /usr/lib/nagios/plugins/check_mem && sudo chmod +x /usr/lib/nagios/plugins/check_mem && sudo sed -i 's/^allowed_hosts=.*/allowed_hosts=127.0.0.1,::1,$SIP/' /etc/nagios/nrpe.cfg && echo 'command[check_load]=/usr/lib/nagios/plugins/check_load -w 3,2.5,2 -c 6,5,4' | sudo tee -a /etc/nagios/nrpe.cfg && echo 'command[check_disk]=/usr/lib/nagios/plugins/check_disk -w 15% -c 5% -p /' | sudo tee -a /etc/nagios/nrpe.cfg && echo 'command[check_mem]=/usr/lib/nagios/plugins/check_mem -u -w 80 -c 90' | sudo tee -a /etc/nagios/nrpe.cfg && sudo systemctl restart nagios-nrpe-server"; ok 'Cliente configurado'; }
add_checks(){ read -p 'Host existente: ' H; while true; do echo '1 CPU | 2 RAM | 3 Disco | 4 Ping | 5 Salir'; read -p 'Opción: ' c; case $c in 1)D='CPU Load';C='check_nrpe!check_load';;2)D='RAM';C='check_nrpe!check_mem';;3)D='Disco';C='check_nrpe!check_disk';;4)D='PING';C='check_ping!100.0,20%!500.0,60%';;5)break;;*)continue;;esac; cat >> "$HOSTS" <<EOF

define service {
 use generic-service
 host_name $H
 service_description $D
 check_command $C
 contacts admin
}
EOF
ok "$D añadido"; done }
mail_alert(){ apt install -y mailutils; read -p 'Correo: ' M; grep -q 'contact_name admin' "$CONTACTS" || cat >> "$CONTACTS" <<EOF

define contact{
 contact_name admin
 use generic-contact
 alias Administrador
 email $M
 service_notification_options c
 host_notification_options d
}
EOF
 grep -q '^enable_notifications=1' "$CFG" || echo 'enable_notifications=1' >> "$CFG"; ok 'Correo configurado'; }
time_fix(){ timedatectl set-timezone Europe/Madrid; timedatectl set-ntp true; ok 'Hora ajustada'; }
del_host(){ read -p 'Host a borrar: ' H; sed -i "/host_name $H/,+12d" "$HOSTS"; ok 'Host borrado'; }
cleanup(){
 mkdir -p /tmp/nagios_backup
 cp "$CMDS" /tmp/nagios_backup/commands.cfg.bak 2>/dev/null
 cp "$HOSTS" /tmp/nagios_backup/hosts.cfg.bak 2>/dev/null
 cp "$CONTACTS" /tmp/nagios_backup/contacts.cfg.bak 2>/dev/null
 echo '' > "$HOSTS"
 sed -i '/check_nrpe/,+5d' "$CMDS"
 sed -i '/contact_name admin/,+8d' "$CONTACTS"
 sed -i '/enable_notifications=1/d' "$CFG"
 grep -q 'objects/hosts.cfg' "$CFG" || echo 'cfg_file=/usr/local/nagios/etc/objects/hosts.cfg' >> "$CFG"
 if ! /usr/local/nagios/bin/nagios -v "$CFG" >/dev/null 2>&1; then
   cp /tmp/nagios_backup/commands.cfg.bak "$CMDS" 2>/dev/null
   sed -i '/check_nrpe/,+5d' "$CMDS"
 fi
 /usr/local/nagios/bin/nagios -v "$CFG"
 systemctl restart nagios
 ok 'Limpieza total completada y saneada'; }
while true; do echo '===== NAGIOS MONITOR PRO V3 ====='; echo '1 Añadir host'; echo '2 Preparar servidor NRPE'; echo '3 Instalar cliente NRPE SSH'; echo '4 Añadir checks'; echo '5 Alertas correo'; echo '6 Ajustar hora'; echo '7 Verificar'; echo '8 Reiniciar'; echo '9 Eliminar host'; echo '10 Limpieza total'; echo '11 Salir'; read -p 'Opción: ' op; case "$op" in 1)add_host;;2)prep_nrpe;;3)ssh_client;;4)add_checks;;5)mail_alert;;6)time_fix;;7)verify;;8)restart_n;;9)del_host;;10)cleanup;;11)exit;;*)warn 'Inválido';; esac; read -p 'ENTER...'; clear; done
