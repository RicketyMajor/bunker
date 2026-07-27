#!/bin/bash

# Colores para la terminal
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}   Instalador Universal - BUNKER TUI v3.0.0   ${NC}"
echo -e "${CYAN}================================================${NC}\n"

# 1. Verificar si Python y Docker están instalados
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}  Python3 no encontrado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# El runtime usa `docker compose` (V2, sin guion), igual que ensure_infrastructure_up.
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}  docker compose (V2) no encontrado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# Convención única de entorno virtual para todo el equipo
VENV_DIR=".venv"

# 2. Creación del Entorno Virtual
echo -e "${GREEN}▶ Configurando entorno virtual (${VENV_DIR})...${NC}"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# 3. Instalación de Dependencias del CLI
echo -e "${GREEN}▶ Instalando dependencias del CLI...${NC}"
python -m pip install --upgrade pip > /dev/null 2>&1
python -m pip install -r requirements.txt > /dev/null 2>&1
python -m pip install -e . > /dev/null 2>&1

# 4. Creación del Enlace Simbólico Global 
echo -e "${GREEN}▶ Creando comando global 'bunker' (te pedirá contraseña si es necesario)...${NC}"
CURRENT_DIR=$(pwd)
sudo ln -sf "$CURRENT_DIR/$VENV_DIR/bin/bunker" /usr/local/bin/bunker

# 5. Aprovisionamiento de Claves Aisladas para Túneles Seguros
echo -e "${GREEN}▶ Aprovisionando criptografía dedicada para el escáner...${NC}"
# Creamos una llave exclusiva para la app que NO afectará a Git ni a otros sistemas
if [ ! -f ~/.ssh/library_cli_key ]; then
    ssh-keygen -t ed25519 -N "" -f ~/.ssh/library_cli_key > /dev/null 2>&1
    echo -e "${GREEN}  Llave dedicada generada con éxito.${NC}"
else
    echo -e "${GREEN}  Credenciales aisladas listas.${NC}"
fi

echo -e "\n${CYAN}================================================${NC}"
echo -e "${GREEN} ¡Instalación completada con éxito!${NC}"
echo -e "Puedes iniciar tu biblioteca desde cualquier lugar escribiendo: ${YELLOW}bunker enter${NC}"
echo -e "${CYAN}================================================${NC}\n"

# Desactivamos el entorno virtual para dejar la terminal limpia
deactivate