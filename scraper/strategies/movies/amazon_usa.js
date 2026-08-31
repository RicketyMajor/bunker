const puppeteer = require('puppeteer');

module.exports = {
    name: 'Amazon USA (Movies & TV) - Puppeteer Edition',
    scrape: async function(keywords = [], apiUrl, opciones) {
        const lim = (opciones && opciones.limite) || 3;   // 3 en el ciclo de 12 h, cfg.limiteCatalogo en --catalogo
        const releases = [];
        if (keywords.length === 0) return releases;

        // Inicia un navegador Chrome real e invisible
        const browser = await puppeteer.launch({
            headless: "new",
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled', // Evita que Amazon detecte que es un bot
                '--disable-dev-shm-usage'
            ]
        });

        const page = await browser.newPage();
        
        // Falsifica la identidad para parecer un usuario en Mac
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        await page.setExtraHTTPHeaders({ 'Accept-Language': 'en-US,en;q=0.9' });

        for (const keyword of keywords) {
            const searchUrl = `https://www.amazon.com/s?k=${encodeURIComponent(keyword)}&i=movies-tv&s=date-desc-rank`;

            try {
                // Navega y espera a que el DOM cargue
                await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

                // Extrae la información inyectando código directamente en el navegador
                const results = await page.evaluate((kw, max) => {
                    const items = [];
                    // Amazon usa este atributo para sus resultados
                    const nodes = document.querySelectorAll('[data-component-type="s-search-result"]');
                    
                    // Solo analiza los primeros 3 resultados
                    const maxNodes = Math.min(nodes.length, max);
                    for (let i = 0; i < maxNodes; i++) {
                        const titleEl = nodes[i].querySelector('.a-text-normal');
                        if (!titleEl) continue;
                        
                        const title = titleEl.innerText.trim();
                        //Solo interesan formatos físicos
                        const isPhysicalMedia = /(blu-ray|dvd|4k|uhd)/i.test(title);

                        if (title && isPhysicalMedia) {
                            items.push({
                                title: title.split(' [')[0].split(' (')[0], // Limpia " [Blu-ray]"
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
                console.error(`   Error en Amazon para '${keyword}': ${error.message}`);
            }
        }

        await browser.close();
        return releases;
    }
};