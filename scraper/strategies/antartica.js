const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Antártica Libros',
    scrape: async function(keywords = []) {
        const releases = [];
        if (keywords.length === 0) return releases;

        for (const keyword of keywords) {
            // URL de búsqueda de Antártica
            const searchUrl = `https://www.antartica.cl/catalogsearch/result/?q=${encodeURIComponent(keyword)}`;

            try {
                const response = await axios.get(searchUrl, {
                    headers: { 'User-Agent': 'Mozilla/5.0' }
                });

                const $ = cheerio.load(response.data);

                // Antártica usa clases específicas para sus productos en la grilla
                $('.product-item-info').slice(0, 3).each((index, element) => {
                    const title = $(element).find('.product-item-link').text().trim();
                    const link = $(element).find('.product-item-link').attr('href');
                    
                    // Extraemos el precio
                    let price = $(element).find('.special-price .price').text().trim();
                    if (!price) price = $(element).find('.price').text().trim();

                    if (title) {
                        releases.push({
                            title: title,
                            publisher: "Antártica",
                            price: price || 'Precio no detectado',
                            buy_url: link,
                            cover_url: ""
                        });
                    }
                });

                await new Promise(resolve => setTimeout(resolve, 1500)); // Cortesía
            } catch (error) {
                console.error(`   ❌ Error en Antártica para '${keyword}': ${error.message}`);
            }
        }
        return releases;
    }
};