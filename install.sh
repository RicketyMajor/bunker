#!/bin/bash

# Colores para la terminal
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================${NC}"
echo -e "${CYAN}   🚀 Instalador Universal - Library CLI v1.0   ${NC}"
echo -e "${CYAN}================================================${NC}\n"

# 1. Verificar si Python y Docker están instalados
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  Python3 no encontrado. Por favor, instálalo primero.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose no encontrado. Por favor, instálalo primero.${NC}"
    exit 1
fi

# 2. Creación del Entorno Virtual
echo -e "${GREEN}▶ Configurando entorno virtual (venv)...${NC}"
python3 -m venv venv
source venv/bin/activate

# 3. Instalación de Dependencias del CLI
echo -e "${GREEN}▶ Instalando dependencias del CLI...${NC}"
pip install -e . > /dev/null 2>&1
pip install pyfiglet > /dev/null 2>&1

# 4. Creación del Enlace Simbólico Global (Requiere sudo)
echo -e "${GREEN}▶ Creando comando global 'library' (te pedirá contraseña si es necesario)...${NC}"
CURRENT_DIR=$(pwd)
sudo ln -sf "$CURRENT_DIR/venv/bin/library" /usr/local/bin/library

# 5. Aprovisionamiento de Claves para Túneles Seguros
echo -e "${GREEN}▶ Verificando credenciales de red (SSH) para el escáner móvil...${NC}"
if [ ! -f ~/.ssh/id_ed25519 ] && [ ! -f ~/.ssh/id_rsa ]; then
    echo -e "${YELLOW}  Generando clave SSH criptográfica automáticamente...${NC}"
    # Ejecuta el keygen de forma silenciosa sin pedir interacción
    ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519 > /dev/null 2>&1
else
    echo -e "${GREEN}  Credenciales detectadas correctamente.${NC}"
fi

echo -e "\n${CYAN}================================================${NC}"
echo -e "${GREEN}✅ ¡Instalación completada con éxito!${NC}"
echo -e "Puedes iniciar tu biblioteca desde cualquier lugar escribiendo: ${YELLOW}library shell${NC}"
echo -e "${CYAN}================================================${NC}\n"

# Desactivamos el venv para dejar la terminal limpia
deactivate