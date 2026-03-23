const axios = require('axios');
const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js'); // El motor de coincidencias difusas
const { CronJob } = require('cron');

// 🌐 URLs de la API interna de Django
const API_URL_WATCHERS = 'http://web:8000/api/books/watchers/';
const API_URL_WISHLIST = 'http://web:8000/api/books/wishlist/add/';

async function getWatchers() {
    try {
        const response = await axios.get(API_URL_WATCHERS);
        return response.data.keywords || [];
    } catch (error) {
        console.error("❌ Error conectando con Django:", error.message);
        return [];
    }
}

async function sendToWishlist(item) {
    try {
        const response = await axios.post(API_URL_WISHLIST, item);
        if (response.status === 201) {
            console.log(`   > 📥 Guardado en Tablón: ${item.title} (${item.publisher})`);
        }
    } catch (error) {
        console.error(`   ❌ Error enviando '${item.title}':`, error.response?.data || error.message);
    }
}

/**
 * 🕵️‍♂️ FILTRO TEMPORAL: Consulta a Google Books para descartar reposiciones
 */
async function verifyNewRelease(title) {
    try {
        const searchUrl = `https://www.googleapis.com/books/v1/volumes?q=intitle:${encodeURIComponent(title)}&maxResults=1`;
        const response = await axios.get(searchUrl);

        if (response.data.items && response.data.items.length > 0) {
            const pubDate = response.data.items[0].volumeInfo.publishedDate; // Ej: "2011", "2023-11-08"
            if (pubDate) {
                const pubYear = parseInt(pubDate.substring(0, 4));
                const currentYear = new Date().getFullYear();

                // 🛑 Si el libro se publicó hace más de 2 años, es una reposición
                if (currentYear - pubYear > 2) {
                    return { isNew: false, year: pubYear };
                }
            }
        }
        // Si no lo encuentra o es reciente, le damos el beneficio de la duda
        return { isNew: true, year: "Reciente/Desconocido" }; 
    } catch (error) {
        return { isNew: true, year: "Error API" }; // No bloqueamos si falla la red
    }
}

/**
 * 🏭 PATRÓN FACTORY: Carga dinámicamente todas las estrategias de scraping
 */
function loadStrategies() {
    const strategies = [];
    const strategiesPath = path.join(__dirname, 'strategies');
    
    // Leemos todos los archivos dentro de la carpeta 'strategies'
    if (fs.existsSync(strategiesPath)) {
        const files = fs.readdirSync(strategiesPath);
        for (const file of files) {
            if (file.endsWith('.js')) {
                const strategy = require(path.join(strategiesPath, file));
                // Solo cargamos si el archivo tiene el formato correcto
                if (strategy.name && typeof strategy.scrape === 'function') {
                    strategies.push(strategy);
                }
            }
        }
    }
    return strategies;
}

/**
 * 🧠 EL MOTOR PRINCIPAL: Extrae, consolida y aplica Inteligencia Artificial
 */
async function runScrapers(keywords) {
    if (keywords.length === 0) {
        console.log("📭 No hay palabras clave para vigilar. Abortando.");
        return;
    }

    console.log(`🔍 Iniciando vigilancia para: [ ${keywords.join(', ')} ]`);
    const strategies = loadStrategies();
    let allReleases = []; // Aquí meteremos TODOS los libros de TODAS las webs

    // 1. Recolectar lanzamientos de todas las editoriales (El Multiverso)
    for (const strategy of strategies) {
        console.log(`\n🏢 Consultando a: ${strategy.name}...`);
        try {
            // Le pasamos las palabras clave a la estrategia por si las necesita
            const releases = await strategy.scrape(keywords); 
            allReleases = allReleases.concat(releases);
            console.log(`   ✅ ${releases.length} lanzamientos obtenidos de ${strategy.name}`);
        } catch (error) {
            console.error(`   ❌ Error crítico en ${strategy.name}:`, error.message);
        }
    }

    // 2. Motor de Coincidencias Difusas (Fuzzy Matching)
    console.log(`\n🧠 Analizando ${allReleases.length} libros encontrados en total...`);
    
    // fuse.js perdona errores ortográficos, símbolos extra (como "Vol. 13") y mayúsculas
    const fuseOptions = {
        keys: ['title'],
        threshold: 0.3, // 0.0 es idéntico, 1.0 empareja cualquier cosa. 0.3 es el punto dulce para mangas/libros.
        ignoreLocation: true
    };
    const fuse = new Fuse(allReleases, fuseOptions);

    // 3. Evaluar cada palabra clave contra el universo de lanzamientos
    for (const keyword of keywords) {
        const results = fuse.search(keyword);
        
        if (results.length > 0) {
            console.log(`\n🎯 ¡MATCH PARA '${keyword}'! Analizando ${results.length} coincidencias...`);
            
            for (const result of results) {
                const item = result.item;
                
                // 🚀 EJECUCIÓN DEL FILTRO DE NOVEDAD
                const verification = await verifyNewRelease(item.title);

                if (!verification.isNew) {
                    console.log(`   ♻️  Descartado por Reposición: '${item.title}' (Publicado originalmente en ${verification.year})`);
                    continue; // ⛔ Rompemos el ciclo aquí, no se enviará a la base de datos
                }

                item.author_string = keyword;
                await sendToWishlist(item);
            }
        }
    }
}

async function main() {
    console.log("\n🚀 --- Iniciando ciclo de vigilancia distribuida ---");
    const keywords = await getWatchers();
    await runScrapers(keywords);
    console.log("🏁 --- Ciclo de vigilancia terminado ---\n");
}

// ============================================================================
// ⏰ PILOTO AUTOMÁTICO (CRON JOB)
// ============================================================================
console.log("🕒 Inicializando el orquestador (Cron)...");

const job = new CronJob(
    '0 9 * * *', 
    async function() {
        console.log(`\n⏰ [${new Date().toLocaleTimeString()}] Despertando al trabajador...`);
        await main();
    },
    null, true, 'America/Santiago'
);
console.log("✅ Piloto automático activado. Búsqueda diaria a las 09:00 AM.");
