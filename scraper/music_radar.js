require('./logger');
const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_MUSIC_WATCHERS = 'http://web:8000/api/music/watchers/';
const API_MUSIC_WISHLIST = 'http://web:8000/api/music/wishlist/';

async function getWatchers() {
    try {
        const response = await axios.get(API_MUSIC_WATCHERS);
        return response.data.map(w => w.keyword) || [];
    } catch (error) {
        console.error(`[DISQUERA] Error conectando con API Django:`, error.message);
        return [];
    }
}

async function startRadar() {
    console.log("==================================================");
    console.log("[RADAR MUSICAL] Iniciando patrullaje global");
    console.log("==================================================");
    
    const keywords = await getWatchers();
    if (keywords.length === 0) {
        console.log("[DISQUERA] No hay artistas ni sellos en vigilancia. Saliendo...");
        return;
    }

    console.log(`[DISQUERA] Vigilando ${keywords.length} objetivos: ${keywords.join(', ')}`);

    const strategiesPath = path.join(__dirname, 'strategies', 'music');
    let strategies = [];
    
    // Auto-crear la carpeta si no existe
    if (!fs.existsSync(strategiesPath)) {
        fs.mkdirSync(strategiesPath, { recursive: true });
    } else {
        const files = fs.readdirSync(strategiesPath).filter(f => f.endsWith('.js'));
        for (const file of files) {
            strategies.push(require(path.join(strategiesPath, file)));
        }
    }

    if (strategies.length === 0) {
         console.log("[DISQUERA] No hay tiendas (estrategias) definidas en 'strategies/music/'.");
         return;
    }

    // Contadores analíticos
    let totalFound = 0;
    let totalAdded = 0;
    let totalRecycled = 0;

    for (const strategy of strategies) {
        console.log(`\n[DISQUERA] Desplegando sabueso en: ${strategy.name || 'Tienda Desconocida'}`);
        try {
            const results = await strategy.scrape(keywords, API_MUSIC_WISHLIST);
            
            if (results.length === 0) {
                console.log(`      [!] 0 coincidencias encontradas.`);
                continue;
            }

            console.log(`      [*] ${results.length} coincidencia(s) encontrada(s). Filtrando...`);
            totalFound += results.length;
            
            for (const item of results) {
                try {
                    const response = await axios.post(API_MUSIC_WISHLIST, item);
                    
                    if (response.status === 201) {
                        console.log(`      [+] AÑADIDO: '${item.title}'`);
                        totalAdded++;
                    } 
                    else if (response.status === 200) {
                        console.log(`      [♻️] RECICLADO: '${item.title}'`);
                        totalRecycled++;
                    }
                } catch (dbError) {
                    console.log(`      [❌] Error procesando '${item.title}'`);
                }
            }
        } catch (e) {
            console.log(`[DISQUERA] Error crítico en ${strategy.name}: ${e.message}`);
        }
    }

    console.log("\n==================================================");
    console.log("[RADAR MUSICAL] Rastreo finalizado.");
    console.log(`REPORTE DE RESULTADOS:`);
    console.log(`   - Coincidencias Totales: ${totalFound}`);
    console.log(`   - Coincidencias Recicladas (Ignoradas): ${totalRecycled}`);
    console.log(`   - Nuevos Descubrimientos (Tablón): ${totalAdded}`);
    console.log("==================================================\n");
}

if (process.argv.includes('--manual')) {
    console.log("[RADAR MUSICAL] Ejecución de escaneo manual iniciada.");
    startRadar().then(() => process.exit(0));
} else {
    console.log("[RADAR MUSICAL] Servidor automático en línea (Ciclo: 12 horas).");
    setTimeout(async () => {
        await startRadar();
        setInterval(startRadar, 1000 * 60 * 60 * 12);
    }, 5000);
}