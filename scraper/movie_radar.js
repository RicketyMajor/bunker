require('./logger');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_MOVIES_WATCHERS = 'http://web:8000/api/movies/watchers/';
const API_MOVIES_WISHLIST = 'http://web:8000/api/movies/wishlist/';

async function getWatchers() {
    try {
        const response = await axios.get(API_MOVIES_WATCHERS);
        return response.data.map(w => w.keyword) || [];
    } catch (error) {
        console.error(`[CINE] Error conectando con API Django:`, error.message);
        return [];
    }
}

async function startRadar() {
    console.log("==================================================");
    console.log("[RADAR CINEMATOGRÁFICO] Iniciando patrullaje global");
    console.log("==================================================");
    
    const keywords = await getWatchers();
    if (keywords.length === 0) {
        console.log("[CINE] No hay directores ni sagas en vigilancia. Saliendo...");
        return;
    }

    console.log(`[CINE] Vigilando ${keywords.length} objetivos: ${keywords.join(', ')}`);

    const strategiesPath = path.join(__dirname, 'strategies', 'movies');
    let strategies = [];
    
    if (fs.existsSync(strategiesPath)) {
        const files = fs.readdirSync(strategiesPath).filter(f => f.endsWith('.js'));
        for (const file of files) {
            strategies.push(require(path.join(strategiesPath, file)));
        }
    }

    if (strategies.length === 0) {
         console.log("[CINE] No hay tiendas definidas en 'strategies/movies/'.");
         return;
    }

    // Contadores analíticos
    let totalFound = 0;
    let totalAdded = 0;
    let totalRecycled = 0;

    for (const strategy of strategies) {
        console.log(`\n[CINE] Desplegando sabueso en: ${strategy.name || 'Tienda Desconocida'}`);
        try {
            const results = await strategy.scrape(keywords, API_MOVIES_WISHLIST);
            
            if (results.length === 0) {
                console.log(`      [!] 0 coincidencias encontradas.`);
                continue;
            }

            console.log(`      [*] ${results.length} coincidencia(s) encontrada(s). Filtrando...`);
            totalFound += results.length;
            
            for (const item of results) {
                try {
                    item.priority = 'MED';
                    item.added_by = 'scraper';
                    const response = await axios.post(API_MOVIES_WISHLIST, item);
                    
                    // Django devuelve 201 si es un descubrimiento nuevo
                    if (response.status === 201) {
                        console.log(`      [+] AÑADIDO: '${item.title}'`);
                        totalAdded++;
                    } 
                    // Django devuelve 200 si la película ya existe o está en lista negra
                    else if (response.status === 200) {
                        console.log(`      [♻️] RECICLADO: '${item.title}'`);
                        totalRecycled++;
                    }
                } catch (dbError) {
                    console.log(`      [❌] Error procesando '${item.title}'`);
                }
            }
        } catch (e) {
            console.log(`[CINE] Error crítico en ${strategy.name}: ${e.message}`);
        }
    }

    console.log("\n==================================================");
    console.log("[RADAR CINEMATOGRÁFICO] Rastreo finalizado.");
    console.log(`REPORTE DE RESULTADOS:`);
    console.log(`   - Coincidencias Totales: ${totalFound}`);
    console.log(`   - Coincidencias Recicladas: ${totalRecycled}`);
    console.log(`   - Nuevos Descubrimientos: ${totalAdded}`);
    console.log("==================================================\n");
}

if (process.argv.includes('--manual')) {
    console.log("[RADAR CINEMATOGRÁFICO] Ejecución de escaneo manual iniciada.");
    startRadar().then(() => process.exit(0));
} else {
    console.log("[RADAR CINEMATOGRÁFICO] Servidor automático en línea (Ciclo: 12 horas).");
    setTimeout(async () => {
        await startRadar();
        setInterval(startRadar, 1000 * 60 * 60 * 12);
    }, 5000);
}