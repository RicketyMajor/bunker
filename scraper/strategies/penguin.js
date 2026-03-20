const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Penguin Libros (Debolsillo)',
    scrape: async function() {
        const releases = [];
        const targetUrl = 'https://www.penguinlibros.com/cl/13-novedades';
        try {
            const response = await axios.get(targetUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
            const $ = cheerio.load(response.data);
            
            $('.product-title, h3').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                if (title && title.length > 4 && !releases.some(r => r.title === title)) {
                    releases.push({
                        title: title,
                        publisher: "Penguin Random House",
                        price: "Ver en tienda",
                        buy_url: targetUrl,
                        cover_url: ""
                    });
                }
            });
            return releases;
        } catch (error) { return []; }
    }
};