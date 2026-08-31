// Separado del entry point para que el check pueda leer la configuracion sin arrancar el
// temporizador de 12 h que `arrancarRadar` monta al importarse.
module.exports = {
    etiqueta: 'CINE',
    banner: 'RADAR CINEMATOGRÁFICO',
    vacio: 'No hay directores ni sagas en vigilancia. Saliendo...',
    carpeta: 'movies',
    apiWatchers: 'http://web:8000/api/movies/watchers/',
    apiWishlist: 'http://web:8000/api/movies/wishlist/',
    // `MovieWishlist` tiene las dos columnas (movies/models.py:89-90) y `MusicWishlist` no.
    // Coinciden con los `default` del modelo, pero eso es una observacion, no una garantia:
    // el dia que un default cambie, el radar seguira diciendo lo que quiere decir.
    extras: { priority: 'MED', added_by: 'scraper' },
    // La ventana de novedades: el año en curso y los dos anteriores. Solo juzga filas con año
    // REAL — las tres estrategias de musica lo traen; amazon_usa no da fecha y entra por su orden
    // `s=date-desc-rank`, no por este filtro. Una fila sin año NO se descarta.
    desdeAno: new Date().getFullYear() - 2,
    // Solo lo usa el barrido `--catalogo`. Medido: iTunes da 49 albumes a limit=50 contra 3 a
    // limit=3; Discogs tiene 50 disponibles y se usaban 3.
    limiteCatalogo: 25,
};
