const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Distrito Manga (PRH)',
    scrape: async function() {
        const releases = [];
        // Apuntamos al buscador de Penguin filtrando por el sello Distrito Manga
        const targetUrl = 'https://www.penguinlibros.com/cl/207547-distrito-manga';
        
        try {
            const response = await axios.get(targetUrl, { 
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0' } 
            });
            const $ = cheerio.load(response.data);
            
            $('.product-title, h3, .name').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).find('a').attr('href') || $(element).attr('href');

                if (title && title.length > 4 && !releases.some(r => r.title === title)) {
                    releases.push({
                        title: title,
                        publisher: "Distrito Manga",
                        price: "Ver en tienda",
                        buy_url: link || targetUrl,
                        cover_url: ""
                    });
                }
            });
            return releases;
        } catch (error) { 
            console.error(`   ❌ Error en Distrito Manga: ${error.message}`);
            return []; 
        }
    }
};