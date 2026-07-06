const puppeteer = require('puppeteer');

module.exports = {
    name: 'JustWatch (Streaming)',
    scrape: async function(keywords = [], apiUrl) {
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

                const results = await page.evaluate((kw) => {
                    const items = [];
                    // JustWatch a menudo usa .title-list-grid__item o etiquetas de enlace similares
                    const nodes = document.querySelectorAll('a.title-list-grid__item, a.title-list-row__column, img.picture-comp__img');
                    
                    const maxNodes = Math.min(nodes.length, 3);
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
                                release_year: new Date().getFullYear().toString()
                            });
                        }
                    }
                    return items;
                }, keyword);

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
