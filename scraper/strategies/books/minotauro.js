const axios = require('axios');
const cheerio = require('cheerio');

// NO usa `render.js`, y eso se midio antes de escribirlo: axios recibe 735 KB de esta pagina
// y el catalogo YA VIENE dentro. La primera sonda dijo "render por JS" porque conto el
// selector VIEJO sobre ese cuerpo — cero coincidencias — y confundio "selector podrido" con
// "pagina vacia". Con el selector correcto, axios da las mismas 20/21 filas que el navegador
// y tarda un tercio. La inversion que lo destapo salio VERDE cuando debia salir roja.

module.exports = {
    name: 'Ediciones Minotauro',
    scrape: async function () {
        const releases = [];
        // La sub-pagina del sello Minotauro dentro del mismo sitio que `planeta.js`, asi que
        // comparte con el la UNICA razon por la que estaba muerta: el selector que el rediseño
        // a CSS-modules dejo sin casar. Ver planeta.js para el porque del ancla por subcadena,
        // del plural en el selector de autor, y de por que aqui no hace falta navegador.
        const targetUrl = 'https://www.planetadelibros.cl/editorial/minotauro/211';

        try {
            const response = await axios.get(targetUrl, {
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0' },
                timeout: 20000,
            });
            const $ = cheerio.load(response.data);

            $('[class*="libro__titulo"]').each((index, element) => {
                const title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).closest('a').attr('href') || $(element).find('a').attr('href');

                const tarjeta = $(element).closest('article, li, div[class*="libro"]');
                const autor = tarjeta.find('[class*="libro__autor"]').first().text()
                    .replace(/\s+/g, ' ').trim();

                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        author_string: autor,
                        publisher: "Minotauro",
                        price: "Ver en tienda",
                        buy_url: link
                            ? (link.startsWith('http') ? link : `https://www.planetadelibros.cl${link}`)
                            : targetUrl,
                        cover_url: ""
                    });
                }
            });

            // Filtro de duplicados
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
            console.error(`   ❌ Error en Minotauro: ${error.message}`);
            return [];
        }
    }
};
