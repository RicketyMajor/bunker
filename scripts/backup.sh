#!/bin/bash
# bunker/scripts/backup.sh
# Script de rotación y backup de la base de datos de Bunker

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="bunker_backup_$TIMESTAMP.json"
MAX_BACKUPS=7

mkdir -p "$BACKUP_DIR"

# Asegurar que estamos en el directorio de la aplicación
cd /app

echo "Iniciando backup automático: $FILENAME"
# Volcar datos
python manage.py dumpdata catalog movies disquera posada chess_study --format=json --indent=4 > "$BACKUP_DIR/$FILENAME"

# Si el backup fue exitoso, rotar
if [ $? -eq 0 ]; then
    echo "Backup completado con éxito."
    
    # Mantener solo los últimos $MAX_BACKUPS archivos, borrar los más viejos
    cd "$BACKUP_DIR"
    ls -tp | grep -v '/$' | tail -n +$((MAX_BACKUPS + 1)) | xargs -I {} rm -- {}
    echo "Rotación completada. Se mantienen los últimos $MAX_BACKUPS backups."
else
    echo "Error: Fallo al generar el backup."
fi
