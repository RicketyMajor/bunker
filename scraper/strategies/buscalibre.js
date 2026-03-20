const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Buscalibre Chile',
    scrape: async function(keywords = []) {
        const releases = [];
        if (keywords.length === 0) return releases;

        for (const keyword of keywords) {
            // 🚀 CAZADOR: Añadimos parámetros a la URL para forzar orden por "Más Nuevos" (Novedades)
            const searchUrl = `https://www.buscalibre.cl/libros/search?q=${encodeURIComponent(keyword)}&sst=novedades`;

            try {
                const response = await axios.get(searchUrl, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
                    }
                });

                const $ = cheerio.load(response.data);

                $('.producto').slice(0, 3).each((index, element) => {
                    const title = $(element).find('.nombre, h3').text().trim();
                    const link = $(element).find('a').attr('href');
                    
                    let rawPrice = $(element).find('[class*="precio"], .p-precio').text().trim();
                    if (!rawPrice) rawPrice = $(element).text();
                    
                    const priceMatch = rawPrice.match(/\$\s*[\d\.]+/);
                    const finalPrice = priceMatch ? priceMatch[0] : 'Precio no detectado';

                    // 🚀 CAZADOR: Descartamos basura obvia o reposiciones genéricas
                    const isBoxset = title.toLowerCase().includes('boxset') || title.toLowerCase().includes('caja');
                    
                    // Solo guardamos si hay título y pasa nuestro filtro básico anti-reposiciones
                    if (title && !isBoxset) {
                        releases.push({
                            title: title,
                            publisher: "Buscalibre",
                            price: finalPrice, 
                            buy_url: link.startsWith('http') ? link : `https://www.buscalibre.cl${link}`,
                            cover_url: ""
                        });
                    }
                });

                await new Promise(resolve => setTimeout(resolve, 1500));

            } catch (error) {
                console.error(`   ❌ Error buscando '${keyword}' en Buscalibre: ${error.message}`);
            }
        }
        
        return releases;
    }
};