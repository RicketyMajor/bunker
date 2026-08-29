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
    // (disquera/models.py:62-73). No es una omision pendiente de rellenar.
    extras: {},
};
