#!/bin/bash

### =============================
### CONFIGURACIÓN
### =============================
SERVER_IP="192.168.1.10"
PLUGINS_VERSION="2.4.9"
NRPE_VERSION="4.1.0"

### =============================
### ACTUALIZAR SISTEMA
### =============================
echo "--- Actualizando sistema ---"
sudo apt update && sudo apt upgrade -y

### =============================
### INSTALAR PAQUETES NECESARIOS
### =============================
echo "--- Instalando paquetes necesarios ---"
sudo apt install -y wget openssl perl build-essential libssl-dev

### =============================
### INSTALAR NAGIOS PLUGINS (EN HOME)
### =============================
echo "--- Instalando Nagios Plugins en HOME ---"
cd ~
wget https://github.com/nagios-plugins/nagios-plugins/releases/download/release-$PLUGINS_VERSION/nagios-plugins-$PLUGINS_VERSION.tar.gz
tar -xzvf nagios-plugins-$PLUGINS_VERSION.tar.gz
cd nagios-plugins-$PLUGINS_VERSION

./configure
make
sudo make install

### =============================
### INSTALAR NRPE (daemon) EN HOME
### =============================
echo "--- Instalando NRPE en HOME ---"
cd ~
wget https://github.com/NagiosEnterprises/nrpe/releases/download/nrpe-$NRPE_VERSION/nrpe-$NRPE_VERSION.tar.gz
tar xvzf nrpe-$NRPE_VERSION.tar.gz
cd nrpe-$NRPE_VERSION

./configure --enable-command-args
make all
sudo make install
sudo make install-config
sudo make install-init
sudo systemctl enable nrpe.service
sudo systemctl start nrpe.service
### =============================
### CONFIGURAR NRPE
### =============================
echo "--- Configurando allowed_hosts en NRPE ---"
NRPE_CFG="/usr/local/nagios/etc/nrpe.cfg"

sed -i "s/^allowed_hosts=.*/allowed_hosts=127.0.0.1,::1,$SERVER_IP/" $NRPE_CFG

### =============================
### ACTIVAR SERVICIO NRPE
### =============================
echo "--- Activando NRPE ---"
systemctl enable nrpe.service
systemctl restart nrpe.service

echo "=============================================="
echo " Cliente Nagios instalado correctamente."
echo "=============================================="
