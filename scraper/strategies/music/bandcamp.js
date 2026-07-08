const axios = require('axios');

module.exports = {
    name: 'Bandcamp / Digital Releases (iTunes API Mock)',
    scrape: async function(keywords, apiUrl) {
        const releases = [];
        
        for (const keyword of keywords) {
            const encodedKeyword = encodeURIComponent(keyword);
            const targetUrl = `https://itunes.apple.com/search?term=${encodedKeyword}&entity=album&limit=3`;
            
            try {
                const response = await axios.get(targetUrl, { timeout: 5000 });
                const results = response.data.results || [];
                
                results.forEach((data) => {
                    let title = data.collectionName;
                    let artist = data.artistName;
                    
                    if (title && !releases.some(r => r.title === title && r.artist === artist)) {
                        releases.push({
                            title: title,
                            artist: artist,
                            release_year: data.releaseDate ? data.releaseDate.substring(0, 4) : "",
                            discogs_id: null
                        });
                    }
                });
                
            } catch (error) {
                console.log(`      [!] Error en Digital Releases para '${keyword}': ${error.message}`);
            }
        }
        return releases;
    }
};
