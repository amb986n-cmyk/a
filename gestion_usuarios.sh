#!/bin/bash

# Asegurar que el script se ejecuta como root (administrador)
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[31m[!] Error: Este script debe ejecutarse con sudo.\e[0m"
  exit 1
fi

mostrar_menu() {
    clear
    echo -e "\e[36m=================================================="
    echo -e "       GESTOR DE USUARIOS - CACHYOS / ARCH        "
    echo -e "==================================================\e[0m"
    echo -e "1) Ver usuarios reales del sistema"
    echo -e "2) Crear nuevo usuario administrador"
    echo -e "3) Eliminar un usuario y borrar sus archivos"
    echo -e "4) Cambiar SOLO la contraseña de un usuario"
    echo -e "5) Modificar Nombre de Usuario y Contraseña"
    echo -e "6) Salir"
    echo -e "\e[36m==================================================\e[0m"
    echo -n "Seleccione una opción [1-6]: "
}

while true; do
    mostrar_menu
    read opcion
    case $opcion in
        1)
            clear
            echo -e "\e[32m=== USUARIOS REALES EN EL SISTEMA ===\e[0m"
            awk -F: '$6 ~ /\/home/ {print "- " $1 " (Home: " $6 ")"}' /etc/passwd
            echo ""
            read -p "Presione [Enter] para volver al menú..."
            ;;
        2)
            clear
            echo -e "\e[32m=== CREAR NUEVO USUARIO ADMINISTRADOR ===\e[0m"
            echo -n "Introduce el nombre del nuevo usuario: "
            read nuevo_user
            if id "$nuevo_user" &>/dev/null; then
                echo -e "\e[31m[!] El usuario '$nuevo_user' ya existe.\e[0m"
            else
                useradd -m -G wheel,sys,log -s /bin/bash "$nuevo_user"
                echo -e "\e[33mAsigna una contraseña para '$nuevo_user':\e[0m"
                passwd "$nuevo_user"
                echo -e "\e[32m[✓] Usuario '$nuevo_user' creado con permisos sudo con éxito.\e[0m"
            fi
            echo ""
            read -p "Presione [Enter] para volver al menú..."
            ;;
        3)
            clear
            echo -e "\e[31m=== ELIMINAR UN USUARIO COMPLETO ===\e[0m"
            echo -n "Introduce el nombre del usuario a borrar: "
            read user_borrar
            if ! id "$user_borrar" &>/dev/null; then
                echo -e "\e[31m[!] El usuario '$user_borrar' no existe.\e[0m"
            else
                echo -e "\e[31m[!] ADVERTENCIA: Se borrará el usuario y TODA su carpeta /home/$user_borrar\e[0m"
                echo -n "¿Está seguro? (s/n): "
                read confirmar
                if [[ "$confirmar" == "s" || "$confirmar" == "S" ]]; then
                    userdel -r -f "$user_borrar"
                    echo -e "\e[32m[✓] Usuario y datos borrados por completo.\e[0m"
                else
                    echo "[*] Operación cancelada."
                fi
            fi
            echo ""
            read -p "Presione [Enter] para volver al menú..."
            ;;
        4)
            clear
            echo -e "\e[32m=== MODIFICAR SOLO CONTRASEÑA ===\e[0m"
            echo -n "Introduce el nombre del usuario: "
            read user_pass
            if ! id "$user_pass" &>/dev/null; then
                echo -e "\e[31m[!] El usuario '$user_pass' no existe.\e[0m"
            else
                passwd "$user_pass"
                echo -e "\e[32m[✓] Contraseña modificada correctamente.\e[0m"
            fi
            echo ""
            read -p "Presione [Enter] para volver al menú..."
            ;;
        5)
            clear
            echo -e "\e[32m=== MODIFICAR NOMBRE DE USUARIO Y CONTRASEÑA ===\e[0m"
            echo -n "Introduce el nombre ACTUAL del usuario que deseas cambiar: "
            read user_actual
            
            if ! id "$user_actual" &>/dev/null; then
                echo -e "\e[31m[!] El usuario '$user_actual' no existe.\e[0m"
            else
                echo -n "Introduce el NUEVO nombre para este usuario: "
                read user_nuevo
                
                if id "$user_nuevo" &>/dev/null; then
                    echo -e "\e[31m[!] Error: El nombre '$user_nuevo' ya está ocupado por otro usuario.\e[0m"
                else
                    echo -e "\e[33mModificando el identificador del sistema...\e[0m"
                    usermod -l "$user_nuevo" -d /home/"$user_nuevo" -m "$user_actual" 2>/dev/null
                    
                    if [ $? -eq 0 ]; then
                        echo -e "\e[32m[✓] Nombre cambiado con éxito de '$user_actual' a '$user_nuevo'.\e[0m"
                        echo -e "\e[33mAhora, asigna la nueva contraseña para '$user_nuevo':\e[0m"
                        passwd "$user_nuevo"
                        echo -e "\e[32m[✓] Contraseña actualizada correctamente.\e[0m"
                    else
                        echo -e "\e[31m[!] Error: No se pudo renombrar el usuario. Asegúrate de que NO tenga procesos activos o sesiones abiertas.\e[0m"
                    fi
                fi
            fi
            echo ""
            read -p "Presione [Enter] para volver al menú..."
            ;;
        6)
            echo -e "\e[33mSaliendo del gestor.\e[0m"
            exit 0
            ;;
        *)
            echo -e "\e[31m[!] Opción no válida.\e[0m"
            sleep 1
            ;;
    esac
done
