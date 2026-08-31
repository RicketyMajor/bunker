const axios = require('axios');

module.exports = {
    name: 'HHV Vinyl Store (MusicBrainz Mock)',
    scrape: async function(keywords, apiUrl, opciones) {
        const lim = (opciones && opciones.limite) || 3;   // 3 en el ciclo de 12 h, cfg.limiteCatalogo en --catalogo
        const releases = [];
        
        for (const keyword of keywords) {
            const encodedKeyword = encodeURIComponent(keyword);
            const targetUrl = `https://musicbrainz.org/ws/2/release/?query=artist:"${encodedKeyword}" AND format:vinyl&fmt=json&limit=${lim}`;
            
            try {
                const pedir = () => axios.get(targetUrl, {
                    headers: { 'User-Agent': 'BunkerDisqueraScraper/1.0 ( alonso@bunker )' },
                    // 20 s y no 5: a limit=25 (barrido de catalogo) MusicBrainz tarda mas de 5 s
                    // y dos de cinco consultas morian por timeout. El 5000 original solo servia
                    // para limit=3, y ademas nunca llegaba a aplicarse mientras happy-eyeballs
                    // abortaba la conexion a los 250 ms.
                    timeout: 20000
                });

                // El 503 de MusicBrainz es su limitador, y esta MEDIDO que es transitorio: la
                // misma consulta que falla vuelve a dar 200 sin tocar nada.
                //
                // ponytail: UN reintento, no backoff. Y la espera fija de abajo NO lo arregla:
                // medido desde ventana limpia con 5 consultas, 1200 ms da 3/5 y 4000 ms da 2/5
                // — la duracion no correlaciona, asi que subirla es cargo cult. Si algun dia
                // hay muchos vigilados de musica, leer el header Retry-After.
                let response;
                try {
                    response = await pedir();
                } catch (e) {
                    if (!e.response || e.response.status !== 503) throw e;
                    console.log(`      [⏳] MusicBrainz limitó '${keyword}'; reintento en 5 s.`);
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    response = await pedir();
                }

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

            // ponytail: MusicBrainz admite ~1 peticion/segundo y responde 503 al pasarse — lo
            // hizo dos veces contra las sondas que midieron esta estrategia. Espera fija; leer
            // el header Retry-After el dia que haya muchos vigilados de musica.
            await new Promise(resolve => setTimeout(resolve, 1200));
        }
        return releases;
    }
};
