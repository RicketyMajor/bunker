const axios = require('axios');

module.exports = {
    name: 'Discogs API',
    scrape: async function(keywords, apiUrl) {
        const releases = [];
        const token = process.env.DISCOGS_API_KEY || "TU_TOKEN_AQUI";
        
        if (token === "TU_TOKEN_AQUI") {
            console.log("      [!] No hay DISCOGS_API_KEY configurada. Omitiendo Discogs.");
            return [];
        }
        
        for (const keyword of keywords) {
            const encodedKeyword = encodeURIComponent(keyword);
            const targetUrl = `https://api.discogs.com/database/search?q=${encodedKeyword}&type=release&token=${token}`;
            
            try {
                const response = await axios.get(targetUrl, { 
                    headers: { 'User-Agent': 'BunkerDisqueraScraper/1.0' },
                    timeout: 5000
                });
                
                const results = response.data.results || [];
                
                results.slice(0, 3).forEach((data) => {
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
