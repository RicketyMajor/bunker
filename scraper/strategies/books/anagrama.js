const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Editorial Anagrama',
    scrape: async function () {
        const releases = [];
        // `/novedades` REDIRIGE a `/catalogo` — lo hace el propio sitio. Y es una SPA con
        // utilidades Tailwind: `h3`, `h4` y `.titulo-libro` dan CERO incluso en el DOM
        // renderizado, asi que el selector viejo no habria casado ni con navegador.
        const targetUrl = 'https://www.anagrama-ed.es/catalogo';
        try {
            const response = await axios.get(targetUrl, {
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0' },
                timeout: 20000,
            });
            const $ = cheerio.load(response.data);

            $('a[href*="/libro/"]').each((index, element) => {
                const $a = $(element);
                const href = $a.attr('href') || '';
                // El titulo es el <h2> de la tarjeta y el autor su hermano ANTERIOR. Verificado
                // en el DOM, no supuesto:
                //   <div class="space-y-1">
                //     <div class="">                          "Mario Crespo López"   <- autor
                //     <h2 class="text-lg/tight font-bold ..."> "Donde Álvaro Pombo"  <- titulo
                // Las clases son utilidades de Tailwind: no hay nada semantico donde anclar, la
                // estructura ES el ancla.
                //
                // NO partir el texto de la tarjeta por '\n'. `textContent` no lleva saltos — el
                // crudo es "Mario Crespo LópezDonde Álvaro Pombo" — y cheerio solo tiene
                // `.text()`, que es textContent. La primera version del plan lo partia asi y
                // descartaba LAS 24 filas.
                const $h2 = $a.find('h2').first();
                const title = $h2.text().replace(/\s+/g, ' ').trim();
                const autor = $h2.prev().text().replace(/\s+/g, ' ').trim();
                if (title.length < 4 || releases.some(r => r.title === title)) return;

                releases.push({
                    title: title,
                    author_string: autor,
                    publisher: "Anagrama",
                    price: "Ver en tienda",
                    // El href lleva el ISBN:
                    //   /libro/narrativas-hispanicas/los-paramos/9788433951120/NH_801
                    buy_url: href.startsWith('http') ? href : `https://www.anagrama-ed.es${href}`,
                    cover_url: ""
                });
            });
            return releases;
        } catch (error) {
            console.error(`   ❌ Error en Anagrama: ${error.message}`);
            return [];
        }
    }
};
