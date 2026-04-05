const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Ediciones Minotauro',
    scrape: async function() {
        const releases = [];
        // Apuntamos directo a la sub-página del sello Minotauro
        const targetUrl = 'https://www.planetadelibros.cl/editorial/minotauro/211';
        
        try {
            const response = await axios.get(targetUrl, { 
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' } 
            });
            const $ = cheerio.load(response.data);
            
            $('.titol, .title, .titol-llibre').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).closest('a').attr('href') || $(element).find('a').attr('href');
                
                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        publisher: "Minotauro",
                        price: "Ver en tienda",
                        buy_url: link ? (link.startsWith('http') ? link : `https://www.planetadelibros.com${link}`) : targetUrl,
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