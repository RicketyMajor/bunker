const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Editorial Anagrama',
    scrape: async function() {
        const releases = [];
        const targetUrl = 'https://www.anagrama-ed.es/novedades';
        try {
            const response = await axios.get(targetUrl, { headers: { 'User-Agent': 'Mozilla/5.0' } });
            const $ = cheerio.load(response.data);
            
            // Buscamos títulos en su grilla de novedades
            $('h3, h4, .titulo-libro').each((index, element) => {
                let title = $(element).text().replace(/\n/g, ' ').trim();
                if (title && title.length > 4 && !releases.some(r => r.title === title)) {
                    releases.push({
                        title: title,
                        publisher: "Anagrama",
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