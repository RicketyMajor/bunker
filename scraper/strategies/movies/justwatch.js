const puppeteer = require('puppeteer');

module.exports = {
    name: 'JustWatch (Streaming)',
    scrape: async function(keywords = [], apiUrl, opciones) {
        const lim = (opciones && opciones.limite) || 3;   // 3 en el ciclo de 12 h, cfg.limiteCatalogo en --catalogo
        const releases = [];
        if (keywords.length === 0) return releases;

        const browser = await puppeteer.launch({
            headless: "new",
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage'
            ]
        });

        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-US,en;q=0.9' });

        for (const keyword of keywords) {
            const searchUrl = `https://www.justwatch.com/us/search?q=${encodeURIComponent(keyword)}`;

            try {
                await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

                const results = await page.evaluate((kw, max) => {
                    const items = [];
                    // JustWatch a menudo usa .title-list-grid__item o etiquetas de enlace similares
                    const nodes = document.querySelectorAll('a.title-list-grid__item, a.title-list-row__column, img.picture-comp__img');
                    
                    const maxNodes = Math.min(nodes.length, max);
                    for (let i = 0; i < maxNodes; i++) {
                        let title = "";
                        
                        if (nodes[i].tagName === 'IMG') {
                            title = nodes[i].getAttribute('alt');
                        } else {
                            const img = nodes[i].querySelector('img');
                            title = img ? img.getAttribute('alt') : nodes[i].innerText;
                        }
                        
                        if (title) {
                            items.push({
                                title: title.replace(/ - JustWatch/i, '').trim(),
                                director: kw,
                                release_year: ""   // ponytail: vacio cuando la fuente no da fecha. Antes ponia el año del
                                       // BARRIDO, y por eso The Thing (1982) esta guardada como 2026. Un
                                       // filtro de novedad sobre un año inventado sale verde en las dos
                                       // direcciones. Rellenar el dia que la fuente traiga la fecha real.
                            });
                        }
                    }
                    return items;
                }, keyword, lim);

                releases.push(...results);
                await new Promise(r => setTimeout(r, 2000 + Math.random() * 2000));
            } catch (error) {
                console.error(`   Error en JustWatch para '${keyword}': ${error.message}`);
            }
        }

        await browser.close();
        return releases;
    }
};
