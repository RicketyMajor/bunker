const axios = require('axios');
const cheerio = require('cheerio');

async function scrapeReleases() {
    console.log("🚀 Iniciando motor de extracción (Scraper)...");
    
    try {
        // 1. Apuntamos a la web objetivo
        const targetUrl = 'https://books.toscrape.com/';
        console.log(`📡 Descargando HTML de: ${targetUrl}`);
        
        const response = await axios.get(targetUrl);
        const html = response.data;

        // 2. Cargamos el HTML en Cheerio para poder manipularlo
        const $ = cheerio.load(html);
        const newReleases = [];

        // 3. Inspeccionamos la estructura y extraemos los datos
        // En esta web de prueba, cada libro está dentro de un <article class="product_pod">
        // Vamos a extraer los primeros 5 libros a modo de prueba
        $('article.product_pod').slice(0, 5).each((index, element) => {
            
            // Buscamos el título (está dentro de un <h3> en la etiqueta <a>, atributo 'title')
            const title = $(element).find('h3 a').attr('title');
            
            // Buscamos el precio (está en un párrafo con la clase 'price_color')
            const price = $(element).find('.price_color').text();

            newReleases.push({ 
                title: title, 
                price: price 
            });
        });

        console.log("✅ ¡Datos extraídos con éxito!");
        console.log(newReleases);

        // TODO: En la Fase 9.3, enviaremos este array (newReleases) a nuestro backend Django

    } catch (error) {
        console.error("❌ Error crítico durante el scraping:", error.message);
    }
}

// Ejecutamos la función
scrapeReleases();