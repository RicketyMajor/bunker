const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Panini Cómics (Novedades)',
    scrape: async function() {
        const releases = [];
        // Apuntamos a la vista de novedades de la tienda de Panini
        const targetUrl = 'https://tiendapanini.cl/manga/novedades-manga';

        try {
            const response = await axios.get(targetUrl, {
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0' },
                maxHeaderSize: 65536 // 🚀 FIX: Aceptamos cabeceras gigantes para Evitar 'Header overflow'
            });

            const $ = cheerio.load(response.data);

            // Panini suele usar Magento, buscamos la clase de enlace de producto
            $('.product-item-link, .product-item-name a').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).attr('href');

                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        publisher: "Panini Cómics",
                        price: "Ver en tienda", 
                        buy_url: link || targetUrl,
                        cover_url: ""
                    });
                }
            });

            // Limpieza de duplicados clásica
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
            console.error(`   ❌ Error en Panini: ${error.message}`);
            return [];
        }
    }
};