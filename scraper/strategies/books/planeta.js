const axios = require('axios');
const cheerio = require('cheerio');

// NO usa `render.js`, y eso se midio antes de escribirlo: axios recibe 735 KB de esta pagina
// y el catalogo YA VIENE dentro. La primera sonda dijo "render por JS" porque conto el
// selector VIEJO sobre ese cuerpo — cero coincidencias — y confundio "selector podrido" con
// "pagina vacia". Con el selector correcto, axios da las mismas 20/21 filas que el navegador
// y tarda un tercio. La inversion que lo destapo salio VERDE cuando debia salir roja.

module.exports = {
    name: 'Grupo Planeta (Novedades)',
    scrape: async function () {
        const releases = [];
        const targetUrl = 'https://www.planetadelibros.cl/libros-novedades';

        try {
            const response = await axios.get(targetUrl, {
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0' },
                timeout: 20000,
            });
            const $ = cheerio.load(response.data);

            // `.titol` / `.title` / `.titol-llibre` daban CERO incluso en el DOM renderizado: el
            // sitio se reconstruyo con CSS-modules. La clase real es
            // `Libro-module-scss-module__P-8Z5q__libro__titulo`, y ese `P-8Z5q` es un hash de
            // build que cambia en cada deploy — por eso el ancla es la subcadena y no la clase.
            $('[class*="libro__titulo"]').each((index, element) => {
                const title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).closest('a').attr('href') || $(element).find('a').attr('href');

                // La tarjeta trae autor: "A oscuras · Thomas Pynchon · NOVELA LITERARIA".
                // Es lo que permite que un vigilado que es PERSONA case aqui.
                //
                // El selector casa por el PLURAL: la clase real es
                // `LibroAutores-...__autoresList Libro-...__libro__autores`, y `libro__autor` es
                // subcadena de `libro__autores`. Verificado en el DOM, 20 coincidencias. Si
                // alguien lo "corrige" al singular exacto, deja de casar.
                //
                // Devuelve los autores CONCATENADOS cuando hay varios ("H.G.Oesterheld Hugo
                // Pratt"). Correcto aqui: `es_vigilado` busca subcadena, asi que un libro a
                // cuatro manos casa por cualquiera de ellas.
                const tarjeta = $(element).closest('article, li, div[class*="libro"]');
                const autor = tarjeta.find('[class*="libro__autor"]').first().text()
                    .replace(/\s+/g, ' ').trim();

                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        author_string: autor,
                        publisher: "Grupo Planeta",
                        price: "Ver en tienda",
                        // `.cl`, no `.com`: los enlaces relativos salen del sitio chileno y
                        // montarlos contra el español daba una URL que no existe.
                        buy_url: link
                            ? (link.startsWith('http') ? link : `https://www.planetadelibros.cl${link}`)
                            : targetUrl,
                        cover_url: ""
                    });
                }
            });

            // Filtro para eliminar posibles duplicados
            const uniqueReleases = [];
            const seenTitles = new Set();
            for (const item of releases) {
                if (!seenTitles.has(item.title)) {
                    seenTitles.add(item.title);
                    uniqueReleases.push(item);
                }
            }

            return uniqueReleases;
        } catch (error) {
            console.error(`   ❌ Error en Grupo Planeta: ${error.message}`);
            return [];
        }
    }
};
