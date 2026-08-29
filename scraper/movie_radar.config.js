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
};
