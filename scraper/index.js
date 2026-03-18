const axios = require('axios');
const cheerio = require('cheerio');

// 🌐 URLs de la API interna (Usamos 'web' porque así se llama el servicio en docker-compose)
const API_URL_WATCHERS = 'http://web:8000/api/books/watchers/';
const API_URL_WISHLIST = 'http://web:8000/api/books/wishlist/add/';

/**
 * PASO 1: Preguntar al Cerebro (Django) qué debemos buscar hoy.
 */
async function getWatchers() {
    try {
        const response = await axios.get(API_URL_WATCHERS);
        return response.data.keywords || [];
    } catch (error) {
        console.error("❌ Error conectando con Django para obtener watchers:", error.message);
        return [];
    }
}

/**
 * PASO 4: Enviar el hallazgo al Tablón de Deseos (Django).
 */
async function sendToWishlist(item) {
    try {
        const response = await axios.post(API_URL_WISHLIST, item);
        console.log(`> Django responde: ${response.data.message} (${item.title})`);
    } catch (error) {
        console.error(`❌ Error enviando '${item.title}' a Django:`, error.response?.data || error.message);
    }
}

/**
 * PASO 2 y 3: Extraer de la web y Filtrar resultados.
 */
async function scrapeReleases(keywords) {
    if (keywords.length === 0) {
        console.log("📭 No hay palabras clave para vigilar en la base de datos. Abortando scraping.");
        return;
    }

    console.log(`🔍 Buscando coincidencias para: [ ${keywords.join(', ')} ]...`);

    try {
        // Usaremos books.toscrape temporalmente para validar el ecosistema completo
        // sin riesgo de bloqueos. Luego podrás cambiar esto a Buscalibre o Ivrea.
        const targetUrl = 'https://books.toscrape.com/';
        const response = await axios.get(targetUrl);
        const $ = cheerio.load(response.data);

        // Simulamos la revisión de la página de novedades
        $('article.product_pod').each((index, element) => {
            const title = $(element).find('h3 a').attr('title');
            const price = $(element).find('.price_color').text();
            
            // Construimos la URL completa de compra
            const relativeUrl = $(element).find('h3 a').attr('href');
            const buyUrl = new URL(relativeUrl, targetUrl).href;

            // PASO 3: EL FILTRO INTELIGENTE
            // Pasamos todo a mayúsculas para evitar problemas de case sensitivity
            const titleUpper = title.toUpperCase();
            
            // Verificamos si alguna de nuestras palabras clave está contenida en el título
            const matchFound = keywords.some(keyword => 
                titleUpper.includes(keyword.toUpperCase())
            );

            if (matchFound) {
                console.log(`🎯 ¡COINCIDENCIA ENCONTRADA!: ${title}`);
                
                // Si hay match, empaquetamos y disparamos a Django
                sendToWishlist({
                    title: title,
                    price: price,
                    publisher: "ToScrape Bookstore", 
                    buy_url: buyUrl
                });
            }
        });

    } catch (error) {
        console.error("❌ Error crítico durante el scraping:", error.message);
    }
}

/**
 * Función principal que orquesta el microservicio
 */
async function main() {
    console.log("\n🚀 --- Iniciando ciclo de vigilancia ---");
    const keywords = await getWatchers();
    await scrapeReleases(keywords);
    console.log("🏁 --- Ciclo de vigilancia terminado ---\n");
}

// Ejecutamos el flujo
main();