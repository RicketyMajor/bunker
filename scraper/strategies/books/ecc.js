const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'ECC Ediciones',
    scrape: async function() {
        const releases = [];
        const targetUrl = 'https://www.eccediciones.com/novedades';

        try {
            const response = await axios.get(targetUrl, {
                headers: { 'User-Agent': 'Mozilla/5.0' }
            });

            const $ = cheerio.load(response.data);

            // ECC suele poner sus títulos en <h3> o etiquetas con clase "title"
            $('.product-name, h2, h3').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).attr('href');

                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        publisher: "ECC Ediciones",
                        price: "Ver en tienda",
                        buy_url: link ? `https://www.ecccomics.com${link}` : targetUrl,
                        cover_url: ""
                    });
                }
            });

            return releases;
        } catch (error) {
            console.error(`   ❌ Error en ECC Ediciones: ${error.message}`);
            return [];
        }
    }
};