const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Norma Editorial (Novedades)',
    scrape: async function() {
        const releases = [];
        // Apuntamos directo a la vena de las novedades
        const targetUrl = 'https://www.normaeditorial.com/novedades';

        try {
            const response = await axios.get(targetUrl, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            });

            const $ = cheerio.load(response.data);

            // Norma suele usar etiquetas de título en sus tarjetas de libros
            $('.uk-card-title, .title, h3').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();

                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        publisher: "Norma Editorial",
                        price: "Ver en tienda",
                        buy_url: targetUrl,
                        cover_url: ""
                    });
                }
            });

            // Limpieza de duplicados
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
            console.error(`   ❌ Error en Norma Editorial: ${error.message}`);
            return [];
        }
    }
};