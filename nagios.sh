#!/bin/bash
# NAGIOS PRO INSTALLER
clear
RED='\033[1;31m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; BLUE='\033[1;34m'; CYAN='\033[1;36m'; NC='\033[0m'
LOG=/var/log/nagios_pro_install.log
exec > >(tee -a "$LOG") 2>&1
msg(){ echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
warn(){ echo -e "${YELLOW}⚠ $1${NC}"; }
fail(){ echo -e "${RED}✘ $1${NC}"; exit 1; }
run(){ msg "$1"; eval "$1" || fail "Error ejecutando: $1"; }
bar(){ for i in {1..25}; do echo -ne "${CYAN}#${NC}"; sleep 0.03; done; echo; }
menu(){
 echo -e "${GREEN}==============================${NC}"
 echo -e "${GREEN}      NAGIOS INSTALLER        ${NC}"
 echo -e "${GREEN}==============================${NC}"
 echo "1) Instalar Nagios"
 echo "2) Desinstalar Nagios"
 echo "3) Salir"
 read -p 'Opción: ' op
}
install_nagios(){
 [ "$EUID" -ne 0 ] && fail "Ejecuta con sudo"
 read -p "Usuario web [nagiosadmin]: " USERNAME; USERNAME=${USERNAME:-nagiosadmin}
 read -s -p "Contraseña: " PASSWORD; echo
 read -s -p "Repite contraseña: " PASSWORD2; echo
 [ "$PASSWORD" != "$PASSWORD2" ] && fail "Las contraseñas no coinciden"
 bar
 run "apt update"
 run "apt install -y autoconf gcc libc6 make wget unzip apache2 apache2-utils php libapache2-mod-php libgd-dev openssl libssl-dev ufw bc gawk dc build-essential snmp libnet-snmp-perl gettext"
 cd /tmp || exit 1
 rm -rf nagioscore* nagios-plugins*
 run "wget -O nagioscore.tar.gz https://github.com/NagiosEnterprises/nagioscore/archive/nagios-4.4.13.tar.gz"
 run "tar xzf nagioscore.tar.gz"
 cd nagioscore-nagios-4.4.13 || exit 1
 run "./configure --with-httpd-conf=/etc/apache2/conf-available"
 run "make all"
 run "make install-groups-users"
 run "usermod -a -G nagios www-data"
 run "make install && make install-daemoninit && make install-config && make install-commandmode && make install-webconf"
 run "a2enmod cgi rewrite auth_basic authn_file"
 run "a2enconf nagios"
 htpasswd -b -c /usr/local/nagios/etc/htpasswd.users "$USERNAME" "$PASSWORD"
 chown www-data:www-data /usr/local/nagios/etc/htpasswd.users
 chmod 640 /usr/local/nagios/etc/htpasswd.users
 run "systemctl enable apache2 && systemctl restart apache2"
 run "systemctl enable nagios || true"
 run "systemctl restart nagios || true"
 run "ufw allow Apache || true"
 cd /tmp || exit 1
 run "wget https://nagios-plugins.org/download/nagios-plugins-2.3.3.tar.gz"
 run "tar xzf nagios-plugins-2.3.3.tar.gz"
 cd nagios-plugins-2.3.3 || exit 1
 run "./configure && make && make install"
 IP=$(hostname -I | awk '{print $1}')
 ok "Instalación completada"
 echo "URL: http://$IP/nagios"
 echo "Usuario: $USERNAME"
}
uninstall_nagios(){
 read -p "¿Seguro? (s/n): " r; [ "$r" != "s" ] && return
 run "systemctl stop nagios 2>/dev/null || true"
 run "rm -rf /usr/local/nagios"
 run "rm -f /etc/init.d/nagios /lib/systemd/system/nagios.service"
 run "rm -f /etc/apache2/conf-enabled/nagios.conf /etc/apache2/conf-available/nagios.conf"
 run "systemctl daemon-reload"
 run "systemctl restart apache2"
 ok "Nagios eliminado"
}
while true; do menu; case $op in 1) install_nagios;; 2) uninstall_nagios;; 3) exit;; *) warn "Opción inválida";; esac; read -p 'ENTER para volver al menú...'; clear; done
