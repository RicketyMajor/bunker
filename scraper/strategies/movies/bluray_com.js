const puppeteer = require('puppeteer');
const axios = require('axios');

module.exports = {
    name: 'Blu-ray.com (ediciones físicas, sembrada por el tablón)',

    // No corre en el ciclo de 12 h. `radar.js` la omite salvo en `--catalogo`: hasta 3 ediciones
    // por cada titulo del tablon son 36 filas de variantes de formato que hay que rechazar a mano.
    soloCatalogo: true,

    // POR QUE NO LA CONDUCEN LOS VIGILADOS: `keywords` son PERSONAS —los dos vigilados de cine son
    // directores— y el `keyword=` de este sitio indexa TITULOS. Medido con un navegador el
    // 2026-08-30: 'Denis Villeneuve' -> "No matches for your selected countries", 'Dune' -> 21
    // ediciones fisicas con formato y año. Asi que la conducen los titulos que YA estan en el
    // tablon, y cada fila hereda el `director` de la que la sembro, sin el cual `es_vigilado`
    // la rechazaria con un 200 (bunker_core/dedup.py).
    scrape: async function(keywords, apiUrl, opciones) {
        // OJO: aqui `limite` significa otra cosa que en las demas estrategias. Alli acota
        // resultados POR VIGILADO; aqui no hay vigilado, asi que acota CUANTOS TITULOS DEL
        // TABLON se siembran. El tope de ediciones de un mismo titulo es `porTitulo`, aparte y
        // fijo: subir `limite` debe cubrir mas tablon, nunca traer mas ediciones de una pelicula.
        const lim = (opciones && opciones.limite) || 3;
        const porTitulo = 3;
        const releases = [];

        let semillas = [];
        try {
            // El propio `apiUrl` que recibe es el tablon. Verificado: GET responde 200 con las
            // filas NO rechazadas — que es lo correcto, no se resiembra desde un rechazo.
            const r = await axios.get(apiUrl, { timeout: 15000 });
            const filas = Array.isArray(r.data) ? r.data : (r.data.results || []);
            semillas = filas.filter(f => f.title && f.director).slice(0, lim);
        } catch (error) {
            console.log(`      [!] No se pudo leer el tablón para sembrar: ${error.message}`);
            return releases;
        }
        if (semillas.length === 0) {
            console.log('      [!] El tablón no tiene filas con título y director: nada que sembrar.');
            return releases;
        }

        // El navegador esta MEDIDO, no supuesto: axios y curl reciben "error42" (7 bytes, con
        // status 200) desde el host Y desde el contenedor; un navegador limpio del contenedor
        // recibe 231 KB y el titulo "Search Movies".
        const browser = await puppeteer.launch({
            headless: 'new',
            executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || null,
            args: ['--no-sandbox', '--disable-setuid-sandbox',
                   '--disable-blink-features=AutomationControlled', '--disable-dev-shm-usage'],
        });
        const page = await browser.newPage();
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

        for (const semilla of semillas) {
            const searchUrl = `https://www.blu-ray.com/movies/search.php?keyword=${encodeURIComponent(semilla.title)}&action=search`;
            try {
                await page.goto(searchUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });

                // El titulo vive en el ATRIBUTO `title` y trae formato y año:
                // "Dune: Part Two 4K (2024)". El textContent esta VACIO porque cada enlace
                // envuelve una portada — por eso el selector viejo `a.title` daba 0 nodos incluso
                // sobre la pagina buena, y por eso "selector podrido" se leia como "pagina vacia".
                const crudos = await page.evaluate((max) => {
                    const out = [];
                    const nodos = document.querySelectorAll('a.hoverlink[title]');
                    for (let i = 0; i < Math.min(nodos.length, max); i++) {
                        out.push(nodos[i].getAttribute('title'));
                    }
                    return out;
                }, porTitulo);

                for (const crudo of crudos) {
                    // "Dune: Part Two 4K (2024)" -> titulo + año REAL. Sin parentesis: año vacio,
                    // NUNCA la fecha del barrido — es el defecto que dejo The Thing (1982)
                    // guardada como 2026 en las 13 filas del tablon.
                    const m = crudo.match(/^(.*?)\s*\((\d{4})\)\s*$/);
                    releases.push({
                        title: m ? m[1].trim() : crudo.trim(),
                        director: semilla.director,
                        release_year: m ? m[2] : "",
                    });
                }

                await new Promise(resolve => setTimeout(resolve, 1500));
            } catch (error) {
                console.log(`      [!] Error en Blu-ray.com para '${semilla.title}': ${error.message}`);
            }
        }

        await browser.close();
        return releases;
    }
};
