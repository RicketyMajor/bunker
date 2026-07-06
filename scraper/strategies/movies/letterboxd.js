const puppeteer = require('puppeteer');

module.exports = {
    name: 'Letterboxd (Trending)',
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
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        for (const keyword of keywords) {
            const searchUrl = `https://letterboxd.com/search/films/${encodeURIComponent(keyword)}/`;

            try {
                await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

                const results = await page.evaluate((kw) => {
                    const items = [];
                    // Letterboxd usa posters con la clase .film-poster o enlaces directos
                    const nodes = document.querySelectorAll('.film-poster, .film-detail-content h2 a');
                    
                    const maxNodes = Math.min(nodes.length, 4);
                    for (let i = 0; i < maxNodes; i++) {
                        let title = "";
                        
                        if (nodes[i].hasAttribute('data-film-name')) {
                            title = nodes[i].getAttribute('data-film-name');
                        } else {
                            title = nodes[i].innerText;
                        }
                        
                        if (title && title.trim().length > 0) {
                            items.push({
                                title: title.trim(),
                                director: kw,
                                release_year: new Date().getFullYear().toString()
                            });
                        }
                    }
                    return items;
                }, keyword);

                // Deduplicación básica
                const uniqueResults = [];
                const seen = new Set();
                for (const item of results) {
                    if (!seen.has(item.title)) {
                        seen.add(item.title);
                        uniqueResults.push(item);
                    }
                }

                releases.push(...uniqueResults.slice(0, 3));
                await new Promise(r => setTimeout(r, 2000 + Math.random() * 2000));
            } catch (error) {
                console.error(`   Error en Letterboxd para '${keyword}': ${error.message}`);
            }
        }

        await browser.close();
        return releases;
    }
};
