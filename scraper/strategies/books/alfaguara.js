const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Alfaguara (Penguin)',
    scrape: async function() {
        const releases = [];
        // Apuntamos al catálogo del sello Alfaguara dentro de Penguin Chile
        const targetUrl = 'https://www.penguinlibros.com/cl/185557-alfaguara';
        
        try {
            const response = await axios.get(targetUrl, { 
                headers: { 'User-Agent': 'Mozilla/5.0' } 
            });
            const $ = cheerio.load(response.data);
            
            // 🚀 FIX: Red de captura HTML ampliada
            $('h3, h4, h2, .titulo-libro, .product-title, .book-title').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).find('a').attr('href') || $(element).attr('href');

                if (title && title.length > 4 && !releases.some(r => r.title === title)) {
                    releases.push({
                        title: title,
                        publisher: "Alfaguara",
                        price: "Ver en tienda",
                        buy_url: link || targetUrl,
                        cover_url: ""
                    });
                }
            });
            return releases;
        } catch (error) { 
            console.error(`   ❌ Error en Alfaguara: ${error.message}`);
            return []; 
        }
    }
};