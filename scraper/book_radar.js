require('./logger');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const Fuse = require('fuse.js'); 

const API_BOOKS_WATCHERS = 'http://web:8000/api/books/watchers/';
const API_BOOKS_WISHLIST = 'http://web:8000/api/books/wishlist-crud/'; // GET
const API_BOOKS_WISHLIST_ADD = 'http://web:8000/api/books/wishlist/add/'; // POST

async function getWatchers() {
    try {
        const response = await axios.get(API_BOOKS_WATCHERS);
        return response.data.keywords || [];
    } catch (error) {
        console.error(`[LIBROS] Error conectando con API de Watchers:`, error.message);
        return [];
    }
}

// Obtiene el tablón completo para saber qué se descartó antes
async function getWishlist() {
    try {
        const response = await axios.get(API_BOOKS_WISHLIST);
        return response.data || [];
    } catch (error) {
        console.error(`[LIBROS] Error obteniendo el tablón actual:`, error.message);
        return [];
    }
}

async function sendToWishlist(item) {
    try {
        const response = await axios.post(API_BOOKS_WISHLIST_ADD, item);
        if (response.status === 201) {
            console.log(`   [+] AÑADIDO: '${item.title}' (${item.price})`);
        }
    } catch (error) {
        // Atrapa el error 400 de Django UniqueConstraint para saber si ya existe
        if (error.response && error.response.status === 400) {
            console.log(`   [♻️] RECICLADO (Ya en radar): '${item.title}'`);
        } else {
            console.error(`   [❌] ERROR guardando '${item.title}': ${error.message}`);
        }
    }
}

// Función auxiliar para normalizar texto (quitar acentos, lower, trim)
function normalizeText(text) {
    if (!text) return "";
    return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

async function runScrapers(keywords) {
    const strategiesDir = path.join(__dirname, 'strategies', 'books');
    if (!fs.existsSync(strategiesDir)) return;

    const files = fs.readdirSync(strategiesDir).filter(f => f.endsWith('.js'));
    
    // Preparar el motor de coincidencias difusas con el tablón actual
    console.log(`[LIBROS] Descargando memoria del tablón para aplicar filtros...`);
    const currentWishlist = await getWishlist();
    
    // Preparar datos normalizados para Fuse
    const normalizedWishlist = currentWishlist.map(w => ({
        ...w,
        normalized_title: normalizeText(w.title)
    }));
    
    // Configurar Fuse.js para usar el título normalizado con un threshold más estricto
    const fuse = new Fuse(normalizedWishlist, { keys: ['normalized_title'], threshold: 0.15 });

    for (const file of files) {
        const strategy = require(path.join(strategiesDir, file));
        console.log(`\n==================================================`);
        console.log(`[LIBROS] Desplegando sabueso en: ${strategy.name}`);
        console.log(`==================================================`);
        
        const results = await strategy.scrape(keywords);
        console.log(`   -> Se encontraron ${results.length} coincidencias crudas. Analizando...\n`);

        for (const item of results) {
            console.log(`   🔎 Evaluando: '${item.title}'`);
            item.author_string = keywords.find(k => item.title.toLowerCase().includes(k.toLowerCase())) || "Desconocido";
            
            let isDuplicate = false;
            let isRejected = false;
            
            // 1. Coincidencia por ISBN (si está disponible en item y Wishlist lo tuviese en el futuro, o en Django)
            if (item.isbn) {
                const isbnMatch = currentWishlist.find(w => w.isbn && w.isbn === item.isbn);
                if (isbnMatch) {
                    isDuplicate = true;
                    isRejected = isbnMatch.is_rejected;
                }
            }

            // 2. Coincidencia por Fuse.js con títulos normalizados
            if (!isDuplicate) {
                const normTitle = normalizeText(item.title);
                const existingMatches = fuse.search(normTitle);
                
                if (existingMatches.length > 0) {
                    isDuplicate = true;
                    isRejected = existingMatches.some(match => match.item.is_rejected);
                }
            }
            
            if (isRejected) {
                console.log(`      [🚫] DESCARTADO (En Lista Negra)`);
                continue; 
            } else if (isDuplicate) {
                console.log(`      [♻️] OMITIDO (Ya existe en el Tablón actual)`);
                continue;
            }

            // Si sobrevive a los filtros, intenta enviarlo a Django
            await sendToWishlist(item);
        }
    }
}

async function startRadar() {
    console.log("\n==================================================");
    console.log("[RADAR LITERARIO] Iniciando escaneo de novedades");
    console.log("==================================================");
    const keywords = await getWatchers();
    
    if (keywords.length > 0) {
        console.log(`[LIBROS] Vigilando ${keywords.length} autores/sagas: [${keywords.join(', ')}]`);
        await runScrapers(keywords);
    } else {
        console.log(`[LIBROS] No hay autores en vigilancia actualmente.`);
    }
    
    console.log("\n[RADAR LITERARIO] En reposo. Esperando próxima ventana de 12 horas.");
}

if (process.argv.includes('--manual')) {
    console.log("[RADAR LITERARIO] Ejecución de escaneo manual iniciada.");
    startRadar().then(() => process.exit(0));
} else {
    console.log("[RADAR LITERARIO] Servidor automático en línea (Ciclo: 12 horas).");
    setTimeout(async () => {
        await startRadar();
        setInterval(startRadar, 1000 * 60 * 60 * 12);
    }, 5000);
}