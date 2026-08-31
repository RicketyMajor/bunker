// Separado del entry point para que el check pueda leer la configuracion sin arrancar el
// temporizador de 12 h que `arrancarRadar` monta al importarse.
module.exports = {
    etiqueta: 'DISQUERA',
    banner: 'RADAR MUSICAL',
    vacio: 'No hay artistas ni sellos en vigilancia. Saliendo...',
    carpeta: 'music',
    apiWatchers: 'http://web:8000/api/music/watchers/',
    apiWishlist: 'http://web:8000/api/music/wishlist/',
    // Vacio a proposito: `MusicWishlist` no tiene `priority` ni `added_by`
    // (music/models.py:62-73). No es una omision pendiente de rellenar.
    extras: {},
    // La ventana de novedades: el año en curso y los dos anteriores. Solo juzga filas con año
    // REAL — las tres estrategias de musica lo traen; amazon_usa no da fecha y entra por su orden
    // `s=date-desc-rank`, no por este filtro. Una fila sin año NO se descarta.
    desdeAno: new Date().getFullYear() - 2,
    // Solo lo usa el barrido `--catalogo`. Medido: iTunes da 49 albumes a limit=50 contra 3 a
    // limit=3; Discogs tiene 50 disponibles y se usaban 3.
    limiteCatalogo: 25,
};
