#!/bin/bash
# bunker/scripts/backup.sh
# Script de rotación y backup de la base de datos de Bunker

# cron does not inherit the container environment, only PID 1 does. Without this the
# POSTGRES_* variables are missing and Django falls back to localhost:5432, which does
# not exist inside the web container. The file is written by the CMD in the Dockerfile.
set -a
[ -f /etc/bunker.env ] && . /etc/bunker.env
set +a

BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="bunker_backup_$TIMESTAMP.json"
MAX_BACKUPS=7

mkdir -p "$BACKUP_DIR"

# Asegurar que estamos en el directorio de la aplicación
cd /app

echo "Iniciando backup automático: $FILENAME"
# Volcar a un temporal: si el dump falla, el archivo truncado no llega al directorio de
# backups, donde contaría entre los $MAX_BACKUPS y acabaría expulsando a uno bueno.
if python manage.py dumpdata catalog movies disquera posada chess_study \
        --format=json --indent=4 > "$BACKUP_DIR/$FILENAME.tmp"; then
    mv "$BACKUP_DIR/$FILENAME.tmp" "$BACKUP_DIR/$FILENAME"
    echo "Backup completado con éxito."

    # Mantener solo los últimos $MAX_BACKUPS archivos, borrar los más viejos
    cd "$BACKUP_DIR"
    ls -tp | grep -v '/$' | tail -n +$((MAX_BACKUPS + 1)) | xargs -I {} rm -- {}
    echo "Rotación completada. Se mantienen los últimos $MAX_BACKUPS backups."
else
    rm -f "$BACKUP_DIR/$FILENAME.tmp"
    echo "Error: Fallo al generar el backup."
fi
