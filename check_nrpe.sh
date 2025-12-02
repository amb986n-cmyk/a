#!/bin/bash

### =============================
### CONFIGURACIÓN
### =============================
NRPE_VERSION="4.1.0"

echo "--- Instalando plugin check_nrpe ---"

### =============================
### IR AL HOME
### =============================
cd ~

### =============================
### DESCARGAR NRPE
### =============================
wget https://github.com/NagiosEnterprises/nrpe/releases/download/nrpe-$NRPE_VERSION/nrpe-$NRPE_VERSION.tar.gz

### =============================
### DESCOMPRIMIR
### =============================
tar xvzf nrpe-$NRPE_VERSION.tar.gz
cd nrpe-$NRPE_VERSION

### =============================
### CONFIGURAR COMPILACIÓN
### =============================
./configure

### =============================
### COMPILAR SOLO check_nrpe
### =============================
make check_nrpe

### =============================
### INSTALAR EL PLUGIN
### =============================
sudo make install-plugin

echo "=============================================="
echo " Plugin check_nrpe instalado correctamente."
echo "=============================================="
