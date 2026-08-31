const axios = require('axios');

// Sustituye a alfaguara.js, distrito_manga.js y penguin.js. Las tres apuntaban a paginas de
// sello del MISMO sitio, que sirve una cascara y construye el catalogo en el cliente: medido el
// 2026-08-30, axios recibia 0 y 13 KB donde el navegador construye 918 KB y 2.7 MB. Su selector
// `.product-title` NO estaba podrido — casa 74 y 225 veces renderizado.
//
// El buscador del sitio es una API JSON de terceros cuyo motor cubre TODOS los sellos, asi que
// las tres se convierten en una consulta por vigilado. Y trae mas de lo que las tres scrapeaban:
//   name  titulo      f25  autor       f26/f3  sello      code.gtin  ISBN
//   url   ficha real  price.regular    images[0].url  portada
// Las tres viejas escribian `price: "Ver en tienda"` y `buy_url` = la pagina de listado.
//
// OJO — ESTE MOTOR NUNCA DEVUELVE CERO. Medido: 'Berserk' da 101 "resultados" que son
// 'Fotocopias' y 'Fama y soledad de Picasso'; Penguin no publica Berserk. Por eso la
// comprobacion de abajo NO es defensiva, es la que hace utilizable la fuente. `buscalibre` y
// `antartica` si devuelven 0 ante un termino inexistente; este no, y esa diferencia es la que
// separa "buscar" de "buscar y creerselo".
const BASE = 'https://search.api.motive.co/search';
const ENGINE = 'db6c510d-fc24-4874-be2a-b607ad9284b2';

const sinAcentos = s => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

module.exports = {
    name: 'Penguin Libros (todos los sellos)',
    scrape: async function (keywords = []) {
        const releases = [];
        const vistos = new Set();

        for (const keyword of keywords) {
            try {
                const { data } = await axios.get(BASE, {
                    params: {
                        'x-engine-id': ENGINE, 'x-origin': 'default', internal: true,
                        query: keyword, start: 0, rows: 24,
                    },
                    headers: { 'User-Agent': 'Mozilla/5.0' },
                    timeout: 20000,
                });

                for (const doc of (data.hits && data.hits.docs) || []) {
                    const title = doc.name;
                    if (!title) continue;
                    const autor = (doc.f25 || [])[0] || '';

                    // La comprobacion que el motor no hace.
                    if (!sinAcentos(`${title} ${autor}`).includes(sinAcentos(keyword))) continue;

                    if (vistos.has(title)) continue;
                    vistos.add(title);

                    releases.push({
                        title: title,
                        author_string: autor || keyword,
                        publisher: (doc.f26 || doc.f3 || [])[0] || 'Penguin Random House',
                        price: doc.price ? `$${Math.round(doc.price.regular)}` : 'Ver en tienda',
                        buy_url: doc.url || '',
                        cover_url: (doc.images && doc.images[0] && doc.images[0].url) || '',
                    });
                }
            } catch (error) {
                console.error(`   ❌ Error en Penguin Libros ('${keyword}'): ${error.message}`);
            }
        }
        return releases;
    },
};
