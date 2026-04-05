const axios = require('axios');

const API_MOVIES_WATCHERS = 'http://web:8000/api/movies/watchers/';
const API_MOVIES_WISHLIST = 'http://web:8000/api/movies/wishlist/';
const TMDB_API_KEY = process.env.TMDB_API_KEY;

async function getWatchers() {
    try {
        const response = await axios.get(API_MOVIES_WATCHERS);
        return response.data.keywords || [];
    } catch (error) {
        console.error(`[CINE] Error conectando con API:`, error.message);
        return [];
    }
}

async function syncMovies(keywords) {
    // Aquí implementaremos la lógica del Oráculo TMDB y futuros scrapers físicos
    console.log(`[CINE] Consultando Oráculo para ${keywords.length} directores/sagas...`);
    // (Tu lógica de TMDB irá aquí)
}

async function startRadar() {
    console.log("==================================================");
    console.log("[RADAR CINEMATOGRÁFICO] Iniciando escaneo en TMDB");
    console.log("==================================================");
    const keywords = await getWatchers();
    if (keywords.length > 0) {
        await syncMovies(keywords);
    }
    console.log("[RADAR CINEMATOGRÁFICO] En reposo. Esperando próxima ventana.");
}

console.log("[RADAR CINEMATOGRÁFICO] Esperando inicio del servidor central...");
setTimeout(async () => {
    await startRadar();
    setInterval(startRadar, 1000 * 60 * 60 * 12); // Cada 12 horas
}, 15000);