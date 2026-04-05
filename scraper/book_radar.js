const axios = require('axios');
const fs = require('fs');
const path = require('path');

const API_BOOKS_WATCHERS = 'http://web:8000/api/books/watchers/';
const API_BOOKS_WISHLIST = 'http://web:8000/api/books/wishlist/add/';

async function getWatchers() {
    try {
        const response = await axios.get(API_BOOKS_WATCHERS);
        return response.data.keywords || [];
    } catch (error) {
        console.error(`[LIBROS] Error conectando con API:`, error.message);
        return [];
    }
}

async function sendToWishlist(item) {
    try {
        const response = await axios.post(API_BOOKS_WISHLIST, item);
        if (response.status === 201) {
            console.log(`   > Guardado en Tablón: ${item.title}`);
        }
    } catch (error) {
        // Ignoramos silenciosamente si ya existe (código 400)
    }
}

async function runScrapers(keywords) {
    const strategiesDir = path.join(__dirname, 'strategies', 'books');
    if (!fs.existsSync(strategiesDir)) return;

    const files = fs.readdirSync(strategiesDir).filter(f => f.endsWith('.js'));
    
    for (const file of files) {
        const strategy = require(path.join(strategiesDir, file));
        console.log(`[LIBROS] Ejecutando estrategia: ${strategy.name}...`);
        
        const results = await strategy.scrape(keywords);
        for (const item of results) {
            item.author_string = keywords.find(k => item.title.toLowerCase().includes(k.toLowerCase())) || "Desconocido";
            await sendToWishlist(item);
        }
    }
}

async function startRadar() {
    console.log("==================================================");
    console.log("[RADAR LITERARIO] Iniciando escaneo de novedades");
    console.log("==================================================");
    const keywords = await getWatchers();
    if (keywords.length > 0) {
        await runScrapers(keywords);
    }
    console.log("[RADAR LITERARIO] En reposo. Esperando próxima ventana.");
}

console.log("[RADAR LITERARIO] Esperando inicio del servidor central...");
setTimeout(async () => {
    await startRadar();
    setInterval(startRadar, 1000 * 60 * 60 * 12); // Cada 12 horas
}, 15000);