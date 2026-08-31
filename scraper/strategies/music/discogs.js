const axios = require('axios');

module.exports = {
    name: 'Discogs API',
    scrape: async function(keywords, apiUrl, opciones) {
        const lim = (opciones && opciones.limite) || 3;   // 3 en el ciclo de 12 h, cfg.limiteCatalogo en --catalogo
        const releases = [];
        const token = process.env.DISCOGS_API_KEY || "TU_TOKEN_AQUI";
        
        if (token === "TU_TOKEN_AQUI") {
            console.log("      [!] No hay DISCOGS_API_KEY configurada. Omitiendo Discogs.");
            return [];
        }
        
        for (const keyword of keywords) {
            const encodedKeyword = encodeURIComponent(keyword);
            // Orden por año descendente: es lo unico gratis que tiene esta API y es lo que hace
            // que el modo novedades no salga siempre vacio. Sin el, `q=` ordena por relevancia y
            // los 3 primeros no cambian NUNCA entre barridos — el techo que hacia que este radar
            // no descubriera nada. Medido: sin orden da 2013/2004/2016; con orden, 2026.
            const targetUrl = `https://api.discogs.com/database/search?q=${encodedKeyword}&type=release&sort=year&sort_order=desc&token=${token}`;
            
            try {
                const response = await axios.get(targetUrl, { 
                    headers: { 'User-Agent': 'BunkerDisqueraScraper/1.0' },
                    timeout: 5000
                });
                
                const results = response.data.results || [];
                
                results.slice(0, lim).forEach((data) => {
                    let titleRaw = data.title || '';
                    let artist = keyword;
                    let title = titleRaw;
                    
                    if (titleRaw.includes(' - ')) {
                        const parts = titleRaw.split(' - ');
                        artist = parts[0].trim();
                        title = parts.slice(1).join(' - ').trim();
                    }
                    
                    if (title && !releases.some(r => r.title === title && r.artist === artist)) {
                        releases.push({
                            title: title,
                            artist: artist,
                            release_year: data.year || "",
                            discogs_id: data.id || null
                        });
                    }
                });
                
            } catch (error) {
                console.log(`      [!] Error en Discogs API para '${keyword}': ${error.message}`);
            }
        }
        return releases;
    }
};
