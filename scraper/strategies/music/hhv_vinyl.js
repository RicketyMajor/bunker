const axios = require('axios');

module.exports = {
    name: 'HHV Vinyl Store (MusicBrainz Mock)',
    scrape: async function(keywords, apiUrl) {
        const releases = [];
        
        for (const keyword of keywords) {
            const encodedKeyword = encodeURIComponent(keyword);
            const targetUrl = `https://musicbrainz.org/ws/2/release/?query=artist:"${encodedKeyword}" AND format:vinyl&fmt=json&limit=3`;
            
            try {
                const response = await axios.get(targetUrl, { 
                    headers: { 'User-Agent': 'BunkerDisqueraScraper/1.0 ( alonso@bunker )' },
                    timeout: 5000
                });
                
                const results = response.data.releases || [];
                
                results.forEach((data) => {
                    let title = data.title;
                    let artist = keyword;
                    
                    if (title && !releases.some(r => r.title === title && r.artist === artist)) {
                        releases.push({
                            title: title,
                            artist: artist,
                            release_year: data.date ? data.date.substring(0, 4) : "",
                            discogs_id: null
                        });
                    }
                });
                
            } catch (error) {
                console.log(`      [!] Error en Vinyl Store para '${keyword}': ${error.message}`);
            }
        }
        return releases;
    }
};
