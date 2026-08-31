require('./logger');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const https = require('https');

// Node 20 activa happy-eyeballs por defecto y da 250 ms POR INTENTO de conexion
// (autoSelectFamilyAttemptTimeout). El TCP a musicbrainz.org (Hetzner, Alemania) tarda 321 ms
// desde este contenedor, asi que el intento IPv4 se abandona y el IPv6 muere con ENETUNREACH
// porque la red de Docker no tiene. El `timeout` de la estrategia no llega a aplicarse jamas:
// falla a los 250 ms. Va aqui y no en la estrategia porque cualquier host a mas de 250 ms muere
// igual, en las ocho. Las estrategias heredan esto sin nombrarlo: Node cachea el modulo, asi que
// su require('axios') es esta misma instancia. Verificado conduciendo hhv_vinyl, no leyendo una
// propiedad — `new https.Agent({autoSelectFamily:false}).autoSelectFamily` es `undefined`, la
// opcion vive en `.options`, y comprobar el nombre en vez del comportamiento da un falso rojo.
axios.defaults.httpsAgent = new https.Agent({ autoSelectFamily: false });

// Un AggregateError tiene `.message` VACIO. Las ocho estrategias registran solo `error.message`,
// asi que el fallo de arriba se imprimia como una linea en blanco —
// `[!] Error en Vinyl Store para 'Daft Punk': ` — y costo una sesion entera diagnosticarlo.
// `err.code` traia ETIMEDOUT desde el principio y nadie lo miraba.
axios.interceptors.response.use(null, (error) => {
    if (!error.message) {
        const subs = error.errors ? error.errors.map(e => e.code || e.message).join(', ') : '';
        error.message = (error.code || 'error sin codigo') + (subs ? ` :: ${subs}` : '');
    }
    return Promise.reject(error);
});

// El cuerpo compartido de los radares de cine y musica. Eran dos ficheros de ~107 lineas que
// diferian en 45, y de esas 45 solo DOS eran comportamiento:
//
//   · `priority`/`added_by`, que solo el tablon de peliculas tiene como columnas. Viajan en
//     `cfg.extras`, vacio para la musica.
//   · un `fs.mkdirSync` que solo estaba en el musical y estaba muerto: las dos carpetas de
//     estrategias existen y estan rastreadas, y una carpeta vacia recien creada da cero
//     estrategias y cae en el mismo return una linea despues.
//
// Los libros entraron el 2026-08-30. Las tres diferencias que este comentario listaba eran
// reales y las tres cosmeticas: `claves` absorbe la forma distinta de watchers, `enriquecer`
// absorbe `author_string`, y el segundo endpoint desaparecio solo cuando el filtro de
// duplicados subio al servidor (bunker_core/dedup.py) y el tablon dejo de viajar hasta aqui.

async function obtenerVigilados(cfg) {
    try {
        const response = await axios.get(cfg.apiWatchers);
        // `/api/books/watchers/` devuelve {keywords:[…]}; los otros dos, [{keyword}]. Una
        // linea de config en vez de tocar un endpoint que sirve a otros consumidores.
        const extraer = cfg.claves || (d => d.map(w => w.keyword));
        return extraer(response.data) || [];
    } catch (error) {
        console.error(`[${cfg.etiqueta}] Error conectando con API Django:`, error.message);
        return [];
    }
}

async function barrer(cfg) {
    console.log("==================================================");
    console.log(`[${cfg.banner}] Iniciando patrullaje global`);
    console.log("==================================================");

    const keywords = await obtenerVigilados(cfg);
    if (keywords.length === 0) {
        console.log(`[${cfg.etiqueta}] ${cfg.vacio}`);
        return;
    }

    console.log(`[${cfg.etiqueta}] Vigilando ${keywords.length} objetivos: ${keywords.join(', ')}`);

    const strategiesPath = path.join(__dirname, 'strategies', cfg.carpeta);
    let strategies = [];

    if (fs.existsSync(strategiesPath)) {
        const files = fs.readdirSync(strategiesPath).filter(f => f.endsWith('.js'));
        for (const file of files) {
            strategies.push(require(path.join(strategiesPath, file)));
        }
    }

    if (strategies.length === 0) {
        console.log(`[${cfg.etiqueta}] No hay tiendas definidas en 'strategies/${cfg.carpeta}/'.`);
        return;
    }

    // Contadores analíticos
    let totalFound = 0;
    let totalAdded = 0;
    let totalRecycled = 0;

    for (const strategy of strategies) {
        // Una estrategia de catalogo no corre de noche. `bluray_com` puede traer hasta 3
        // ediciones fisicas por cada titulo del tablon: con 12 titulos eso son 36 filas de
        // variantes de formato que hay que rechazar a mano. Es una accion deliberada de Alonso,
        // no algo que pase a las 3 de la mañana.
        if (strategy.soloCatalogo && !cfg.catalogo) {
            console.log(`\n[${cfg.etiqueta}] Omitida (sólo catálogo): ${strategy.name}`);
            continue;
        }
        console.log(`\n[${cfg.etiqueta}] Desplegando sabueso en: ${strategy.name || 'Tienda Desconocida'}`);
        try {
            const results = await strategy.scrape(keywords, cfg.apiWishlist, { limite: cfg.limite || 3 });

            if (results.length === 0) {
                console.log(`      [!] 0 coincidencias encontradas.`);
                continue;
            }

            console.log(`      [*] ${results.length} coincidencia(s) encontrada(s). Filtrando...`);
            totalFound += results.length;

            for (const item of results) {
                // Ventana de novedades. Una fila SIN año NO se juzga: `amazon_usa` no da fecha
                // (su fuente no la publica en el listado) y es la UNICA fuente de cine capaz de
                // descubrir algo, por su orden `s=date-desc-rank`. Rechazar el año vacio la
                // borraria en silencio, que es peor que el ruido que este filtro quita.
                if (cfg.desdeAno && item.release_year && Number(item.release_year) < cfg.desdeAno) {
                    console.log(`      [⌛] Fuera de ventana (${item.release_year}) :: '${item.title}'`);
                    continue;
                }
                try {
                    Object.assign(item, cfg.extras);
                    if (cfg.enriquecer) Object.assign(item, cfg.enriquecer(item, keywords));
                    const response = await axios.post(cfg.apiWishlist, item);

                    // Django devuelve 201 si es un descubrimiento nuevo
                    if (response.status === 201) {
                        console.log(`      [+] AÑADIDO: '${item.title}'`);
                        totalAdded++;
                    }
                    // Django devuelve 200 si ya existe, si esta en lista negra, o si no
                    // menciona a ningun vigilado. El mensaje distingue los tres; el status no,
                    // asi que hardcodear RECICLADO contaba un descarte como un duplicado.
                    else if (response.status === 200) {
                        console.log(`      [♻️] ${response.data.message} :: '${item.title}'`);
                        totalRecycled++;
                    }
                } catch (dbError) {
                    console.log(`      [❌] Error procesando '${item.title}'`);
                }
            }
        } catch (e) {
            console.log(`[${cfg.etiqueta}] Error crítico en ${strategy.name}: ${e.message}`);
        }
    }

    console.log("\n==================================================");
    console.log(`[${cfg.banner}] Rastreo finalizado.`);
    console.log(`REPORTE DE RESULTADOS:`);
    console.log(`   - Coincidencias Totales: ${totalFound}`);
    console.log(`   - Coincidencias Recicladas: ${totalRecycled}`);
    console.log(`   - Nuevos Descubrimientos: ${totalAdded}`);
    console.log("==================================================\n");
}

function arrancarRadar(cfg) {
    if (process.argv.includes('--catalogo')) {
        // Barrido de CATALOGO: trae todo lo publicado por cada vigilado, sin ventana de fecha.
        // Termina y no se repite — callar despues es correcto, ya lo trajo todo. Es lo contrario
        // del ciclo de 12 h, que pregunta "que ha salido" en vez de "que me falta".
        console.log(`[${cfg.banner}] Barrido de CATÁLOGO (límite ${cfg.limiteCatalogo || 25}).`);
        barrer({ ...cfg, limite: cfg.limiteCatalogo || 25, desdeAno: null, catalogo: true })
            .then(() => process.exit(0));
    } else if (process.argv.includes('--manual')) {
        console.log(`[${cfg.banner}] Ejecución de escaneo manual iniciada.`);
        barrer(cfg).then(() => process.exit(0));
    } else {
        console.log(`[${cfg.banner}] Servidor automático en línea (Ciclo: 12 horas).`);
        setTimeout(async () => {
            await barrer(cfg);
            setInterval(() => barrer(cfg), 1000 * 60 * 60 * 12);
        }, 5000);
    }
}

module.exports = { arrancarRadar, barrer };
