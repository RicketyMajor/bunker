const axios = require('axios');
const cheerio = require('cheerio');

module.exports = {
    name: 'Editorial Ivrea (Novedades)',
    scrape: async function() {
        const releases = [];
        // Apuntamos a la sección de próximas salidas/novedades (puedes cambiar ARG por ESP si prefieres la filial española)
        const targetUrl = 'https://www.editorialivrea.com/ESP/proximas/';

        try {
            // 1. TÁCTICA DE CORTESÍA: Disfrazamos nuestro bot como un navegador real
            const response = await axios.get(targetUrl, {
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            });

            const $ = cheerio.load(response.data);

            // 2. EXTRACCIÓN: La web de Ivrea suele usar la clase .novedad, tablas o simplemente etiquetas <b>/<strong>
            // Buscamos todas las imágenes o textos resaltados en la página
            $('b, strong, .tomo').each((index, element) => {
                // Limpiamos el texto (quitamos saltos de línea y espacios extra)
                let title = $(element).text().replace(/\n/g, ' ').trim();

                // 3. SANITIZACIÓN: Filtramos basura. Queremos textos que parezcan títulos (ni muy cortos, ni muy largos)
                if (title && title.length > 3 && title.length < 100) {
                    
                    // Excluimos palabras típicas de la interfaz web que no son mangas
                    const ignoreWords = ['novedades', 'reediciones', 'próximamente', 'ivrea', 'comprar'];
                    const isGarbage = ignoreWords.some(word => title.toLowerCase().includes(word));

                    if (!isGarbage) {
                        releases.push({
                            title: title,
                            publisher: "Editorial Ivrea",
                            price: "Ver en tienda", // Ivrea ARG no suele listar el precio directamente en el título
                            buy_url: targetUrl, 
                            cover_url: "" // Lo dejamos vacío por ahora para mantenerlo simple
                        });
                    }
                }
            });

            // 4. ELIMINAR DUPLICADOS: Como buscamos etiquetas genéricas, a veces atrapamos el mismo título dos veces
            const uniqueReleases = [];
            const seenTitles = new Set();
            
            for (const item of releases) {
                if (!seenTitles.has(item.title)) {
                    seenTitles.add(item.title);
                    uniqueReleases.push(item);
                }
            }

            return uniqueReleases;

        } catch (error) {
            console.error(`   ❌ Error crítico conectando con Ivrea: ${error.message}`);
            return []; // Devolvemos un array vacío para no tumbar todo el orquestador
        }
    }
};