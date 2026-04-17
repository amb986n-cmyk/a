#!/bin/bash
# Script interactivo de instalación de Nagios Core 4.4.13
clear
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
msg(){ echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"; }
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
fail(){ echo -e "${RED}✘ $1${NC}"; exit 1; }
run(){ eval "$1" || fail "Error ejecutando: $1"; }

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}   BIENVENIDO AL INSTALADOR      ${NC}"
echo -e "${GREEN}        NAGIOS CORE             ${NC}"
echo -e "${GREEN}=================================${NC}"
read -p "Pulsa ENTER para continuar..."

if [ "$EUID" -ne 0 ]; then echo "Ejecuta con sudo"; exit 1; fi
read -p "Usuario web para Nagios [nagiosadmin]: " USERNAME
USERNAME=${USERNAME:-nagiosadmin}
read -s -p "Contraseña para $USERNAME: " PASSWORD; echo

msg "Actualizando repositorios..."
run "apt update"
msg "Instalando dependencias..."
run "apt install -y autoconf gcc libc6 make wget unzip apache2 php libapache2-mod-php libgd-dev openssl libssl-dev"
cd /tmp || exit
msg "Descargando Nagios Core..."
run "wget -O nagioscore.tar.gz https://github.com/NagiosEnterprises/nagioscore/archive/nagios-4.4.13.tar.gz"
run "tar xzf nagioscore.tar.gz"
cd nagioscore-nagios-4.4.13/ || exit
msg "Configurando compilación..."
run "./configure --with-httpd-conf=/etc/apache2/sites-enabled"
run "make all"
run "make install-groups-users"
run "usermod -a -G nagios www-data"
run "make install"
run "make install-daemoninit"
run "make install-config"
run "make install-commandmode"
run "make install-webconf"
run "systemctl restart apache2"
run "ufw allow apache || true"
msg "Creando usuario web..."
echo -e "$PASSWORD\n$PASSWORD" | htpasswd -ci /usr/local/nagios/etc/htpasswd.users "$USERNAME"
run "systemctl restart apache2.service"
msg "Instalando plugins..."
run "apt install -y autoconf gcc libc6 make libssl-dev wget bc gawk dc build-essential snmp libnet-snmp-perl gettext"
cd /tmp || exit
run "wget https://nagios-plugins.org/download/nagios-plugins-2.3.3.tar.gz"
run "tar zxvf nagios-plugins-2.3.3.tar.gz"
cd nagios-plugins-2.3.3/ || exit
run "./configure"
run "make"
run "make install"
run "ufw allow 80 || true"
IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}\nInstalación completada.${NC}"
echo -e "Accede en: http://$IP/nagios"
echo -e "Usuario: $USERNAME"
