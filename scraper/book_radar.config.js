// Separado del entry point para que el check pueda leer la configuracion sin arrancar el
// temporizador de 12 h que `arrancarRadar` monta al importarse.
module.exports = {
    etiqueta: 'LIBROS',
    banner: 'RADAR LITERARIO',
    vacio: 'No hay autores en vigilancia actualmente. Saliendo...',
    carpeta: 'books',
    apiWatchers: 'http://web:8000/api/books/watchers/',
    // El endpoint de escritura, no el de lectura: `wishlist-crud/` se quedo sin llamador
    // cuando el filtro de duplicados paso al servidor.
    apiWishlist: 'http://web:8000/api/books/wishlist/add/',
    // Vacio a proposito: `WishlistItem` no tiene `priority` ni `added_by` (catalog/models.py).
    extras: {},
    // `/api/books/watchers/` responde {keywords:[…]}; los otros dos, [{keyword}].
    claves: d => d.keywords,
    // `author_string` es columna solo del tablon de libros. Sale del vigilado que aparece
    // dentro del titulo, que es lo que hacia book_radar.js antes de encogerse.
    enriquecer: (item, keywords) => ({
        author_string: keywords.find(
            k => item.title.toLowerCase().includes(k.toLowerCase())) || 'Desconocido',
    }),
};
