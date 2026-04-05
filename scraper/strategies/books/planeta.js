const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Grupo Planeta (Novedades)',
    scrape: async function() {
        const releases = [];
        const targetUrl = 'https://www.planetadelibros.cl/libros-novedades';
        
        try {
            const response = await axios.get(targetUrl, { 
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' } 
            });
            const $ = cheerio.load(response.data);
            
            // Planeta suele usar estas clases para los nombres de sus libros
            $('.titol, .title, .titol-llibre').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                const link = $(element).closest('a').attr('href') || $(element).find('a').attr('href');
                
                if (title && title.length > 3) {
                    releases.push({
                        title: title,
                        publisher: "Grupo Planeta",
                        price: "Ver en tienda",
                        // A veces los links son relativos, así que los armamos completos
                        buy_url: link ? (link.startsWith('http') ? link : `https://www.planetadelibros.com${link}`) : targetUrl,
                        cover_url: ""
                    });
                }
            });
            
            // Filtro para eliminar posibles duplicados
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
            console.error(`   ❌ Error en Grupo Planeta: ${error.message}`);
            return [];
        }
    }
};