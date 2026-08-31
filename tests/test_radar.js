// Guard for the ONE thing the radar unification could silently change: which extra fields each
// radar attaches to an item before POSTing it. `MovieWishlist` has `priority`/`added_by` columns
// (movies/models.py:89-90); `MusicWishlist` has neither (music/models.py:62-73). Merging the
// two radars without this check is how a schema difference becomes a silent behaviour change in
// whichever copy lost the argument.
//
// RUNS INSIDE THE `scraper-movies` CONTAINER, and it has to: `radar.js` requires `axios`, and
// `scraper/node_modules` is empty on the host (compose supplies it as an anonymous volume).
// `cli/doctor.py` invokes it through `docker compose exec`.
//
// The first version of this check read the two config objects and never loaded `radar.js`, so
// deleting `Object.assign(item, cfg.extras)` from the shared body left it printing OK and
// exiting 0 — green in both directions for the exact defect it advertised. Five inversions had
// been run on it, and all five were on the CONFIGS: the readers were inverted and the writer
// never was. It now drives `barrer()` against a stubbed axios and a planted strategy, so the
// line that attaches the fields actually executes.
//
// Run: docker compose exec -T scraper-movies node /app/../tests/test_radar.js   (see doctor)
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const RAIZ = '/app';
const movie = require(path.join(RAIZ, 'movie_radar.config.js'));
const music = require(path.join(RAIZ, 'music_radar.config.js'));
const books = require(path.join(RAIZ, 'book_radar.config.js'));

// --- Estrategia de sonda, plantada en disco porque `barrer` las lee de ahi ---------------
const CARPETA = '_sonda';
const dirSonda = path.join(RAIZ, 'strategies', CARPETA);
fs.mkdirSync(dirSonda, { recursive: true });
fs.writeFileSync(path.join(dirSonda, 'sonda.js'), `
module.exports = {
    name: 'Sonda',
    scrape: async () => [{ title: 'Berserk Deluxe Volume 15' }],
};
`);

// --- axios apuñalado: `require` devuelve la MISMA instancia que ve radar.js --------------
const axios = require('axios');
const enviados = [];
// Libros y los otros dos NO comparten forma de watchers: `/api/books/watchers/` devuelve
// {keywords:[…]} y los otros [{keyword}]. Esa diferencia es justo lo que `cfg.claves` existe
// para absorber, asi que el stub sirve la forma que le toque a cada uno.
let formaWatchers = [{ keyword: 'objetivo' }];
axios.get = async () => ({ data: formaWatchers });
axios.post = async (url, item) => { enviados.push({ url, item }); return { status: 201 }; };

const { barrer } = require(path.join(RAIZ, 'radar.js'));

async function conducir(cfg, forma) {
    enviados.length = 0;
    formaWatchers = forma;
    await barrer({ ...cfg, carpeta: CARPETA });
    // Una COPIA, no el array vivo: devolverlo tal cual hacia que la segunda llamada vaciara y
    // rellenara el resultado de la primera, y las dos comprobaciones miraban el item musical.
    return [...enviados];
}

(async () => {
    try {
        const deCine = await conducir(movie, [{ keyword: 'objetivo' }]);
        const deMusica = await conducir(music, [{ keyword: 'objetivo' }]);
        const deLibros = await conducir(books, { keywords: ['Berserk'] });

        // Vacuidad primero: si `barrer` no llego a postear nada, todo lo de abajo pasa por vacio.
        assert.strictEqual(deCine.length, 1, `el radar de cine no posteo nada: el barrido no corrio`);
        assert.strictEqual(deMusica.length, 1, `el radar musical no posteo nada: el barrido no corrio`);
        assert.strictEqual(deLibros.length, 1,
            'el radar de libros no posteo nada: o `claves` no extrajo las keywords, o el barrido no corrio');
        assert.strictEqual(deLibros[0].url, books.apiWishlist,
            `el radar de libros posteo a ${deLibros[0].url}, no a su tablon`);
        assert.strictEqual(deLibros[0].item.author_string, 'Berserk',
            'el radar de libros dejo de mandar author_string: `enriquecer` no corrio');
        assert.ok(!('priority' in deLibros[0].item) && !('added_by' in deLibros[0].item),
            'el radar de libros manda campos que WishlistItem no tiene: '
            + JSON.stringify(deLibros[0].item));
        assert.strictEqual(books.carpeta, 'books',
            'la carpeta de estrategias de libros apunta al modulo equivocado');

        // Lo que de verdad se manda por el cable, no lo que la config dice que se mandaria.
        assert.strictEqual(deCine[0].item.priority, 'MED',
            'el radar de cine dejo de mandar priority');
        assert.strictEqual(deCine[0].item.added_by, 'scraper',
            'el radar de cine dejo de mandar added_by');
        assert.ok(!('priority' in deMusica[0].item) && !('added_by' in deMusica[0].item),
            'el radar musical manda campos que MusicWishlist no tiene: '
            + JSON.stringify(deMusica[0].item));

        // Cada radar escribe en SU tablon, y la URL exacta: `includes('/movies/')` daba VERDE
        // al cambiar el POST a `cfg.apiWatchers`, porque esa URL tambien nombra el modulo.
        // Lo que se defiende es que el cuerpo postea al WISHLIST, no a cualquier ruta del modulo.
        assert.strictEqual(deCine[0].url, movie.apiWishlist,
            `el radar de cine posteo a ${deCine[0].url}, no a su tablon`);
        assert.strictEqual(deMusica[0].url, music.apiWishlist,
            `el radar musical posteo a ${deMusica[0].url}, no a su tablon`);

        // Las carpetas de estrategias de las configs de verdad (la sonda las sustituye arriba).
        assert.ok(movie.carpeta === 'movies' && music.carpeta === 'music',
            'una carpeta de estrategias apunta al modulo equivocado');

        // --- La sede compartida: el agente y el interceptor viven en radar.js para las OCHO ---
        // Se comprueba DESPUES de requerir radar.js y sobre la instancia que ve una estrategia
        // cualquiera (`require('axios')` devuelve la misma, por la cache de modulos de Node).
        //
        // NO se comprueba leyendo el fichero: un assert de texto sobre `radar.js` pasa igual
        // aunque la linea este dentro de un `if (false)`. Y NO se comprueba mirando
        // `agente.autoSelectFamily`, que es `undefined` — https.Agent guarda las opciones en
        // `.options`, y leer el nombre en vez del sitio da un rojo falso. Costo una ronda.
        const agente = require('axios').defaults.httpsAgent;
        assert.ok(agente, 'radar.js ya no instala un httpsAgent compartido');
        assert.strictEqual(agente.options.autoSelectFamily, false,
            'happy-eyeballs vuelve a estar activo: cualquier host a mas de 250 ms de RTT fallara '
            + 'con ETIMEDOUT y mensaje VACIO, que es como hhv_vinyl llevaba semanas muerta');

        // El interceptor, conducido de verdad: se le pasa el error que el defecto produce.
        const manejadores = require('axios').interceptors.response.handlers.filter(h => h && h.rejected);
        assert.ok(manejadores.length >= 1, 'radar.js ya no instala el interceptor de mensajes vacios');
        const agregado = new AggregateError(
            [Object.assign(new Error('connect ETIMEDOUT 1.2.3.4:443'), { code: 'ETIMEDOUT' }),
             Object.assign(new Error('connect ENETUNREACH ::1:443'), { code: 'ENETUNREACH' })]);
        agregado.message = '';                       // asi llega de axios: VACIO
        agregado.code = 'ETIMEDOUT';
        let rellenado = null;
        await manejadores[0].rejected(agregado).catch(e => { rellenado = e.message; });
        assert.ok(rellenado && rellenado.length > 0,
            'el interceptor dejo pasar un error con mensaje vacio: el fallo volveria a imprimirse '
            + "como `[!] Error en Vinyl Store para 'Daft Punk': ` y sin causa");
        assert.ok(rellenado.includes('ETIMEDOUT') && rellenado.includes('ENETUNREACH'),
            `el mensaje no nombra los sub-errores del AggregateError: ${JSON.stringify(rellenado)}`);

        // --- Ninguna estrategia INVENTA el año ------------------------------------------
        // El defecto no era que el año fuese incorrecto: es que se fabricaba. Las cinco
        // estrategias de cine escribian `new Date().getFullYear()`, o sea el año del BARRIDO, y
        // por eso las 13 filas del tablon dicen 2026 — incluida The Thing, de 1982.
        // Importa porque el filtro de novedad de `radar.js` juzga `release_year`: medido contra
        // un año inventado sale verde en las dos direcciones y no defiende nada.
        const dirEstrategias = path.join(RAIZ, 'strategies');
        const culpables = [];
        for (const modulo of fs.readdirSync(dirEstrategias)) {
            const sub = path.join(dirEstrategias, modulo);
            if (!fs.statSync(sub).isDirectory()) continue;
            for (const f of fs.readdirSync(sub).filter(x => x.endsWith('.js'))) {
                if (fs.readFileSync(path.join(sub, f), 'utf8').includes('getFullYear')) {
                    culpables.push(`${modulo}/${f}`);
                }
            }
        }
        // Suelo anti-vacuidad: si el barrido no encontro ficheros, el bucle de arriba pasa por
        // vacio y este check felicita a un directorio inexistente.
        assert.ok(fs.readdirSync(dirEstrategias).length >= 3,
            'el barrido de estrategias no vio los tres modulos: el check de arriba es vacuo');
        assert.strictEqual(culpables.length, 0,
            `estas estrategias vuelven a fabricar release_year con la fecha del barrido: ${culpables.join(', ')}`);

        // --- `soloCatalogo` mantiene una estrategia fuera del ciclo de 12 h -----------------
        // Conducido, no leido: un assert de texto sobre `radar.js` pasa igual aunque la guardia
        // este dentro de un `if (false)`. Se planta una estrategia marcada y se comprueban las
        // DOS direcciones — omitida sin `catalogo`, desplegada con el. Una sola direccion no
        // distingue "la guardia funciona" de "la estrategia no producia nada".
        const dirSolo = path.join(RAIZ, 'strategies', '_sonda_catalogo');
        fs.mkdirSync(dirSolo, { recursive: true });
        fs.writeFileSync(path.join(dirSolo, 'solo.js'), `
module.exports = {
    name: 'SondaSoloCatalogo',
    soloCatalogo: true,
    scrape: async () => [{ title: 'ZZSonda Edicion Fisica 99' }],
};
`);
        try {
            enviados.length = 0;
            formaWatchers = [{ keyword: 'objetivo' }];
            await barrer({ ...movie, carpeta: '_sonda_catalogo' });
            assert.strictEqual(enviados.length, 0,
                'una estrategia soloCatalogo posteo en el ciclo de 12 h: bluray_com inundaria el '
                + 'tablon con variantes de formato cada noche');

            enviados.length = 0;
            await barrer({ ...movie, carpeta: '_sonda_catalogo', catalogo: true });
            assert.strictEqual(enviados.length, 1,
                'una estrategia soloCatalogo NO corrio en modo catalogo: la guardia la excluye '
                + 'siempre y bluray_com no se desplegaria nunca');
        } finally {
            fs.rmSync(dirSolo, { recursive: true, force: true });
        }

        // `bluray_com` lee el ATRIBUTO, no el texto. El textContent de a.hoverlink esta VACIO
        // —envuelve una portada—, asi que leer texto da 0 filas sobre la pagina BUENA, que es
        // como el selector viejo se leia como "pagina vacia" en vez de "selector podrido".
        const br = fs.readFileSync(path.join(RAIZ, 'strategies', 'movies', 'bluray_com.js'), 'utf8');
        assert.ok(br.includes("getAttribute('title')"),
            'bluray_com dejo de leer el atributo title: volveria a devolver 0 filas en silencio');
        assert.ok(!/querySelectorAll\('a\.title'\)|\$\('a\.title'\)/.test(br),
            'bluray_com volvio al selector muerto a.title');
        assert.ok(br.includes('soloCatalogo: true'),
            'bluray_com volvio al ciclo automatico de 12 h');

        console.log('OK: los tres radares comparten cuerpo, y cada uno manda lo suyo por el cable');
        console.log('OK: soloCatalogo excluye del ciclo de 12 h y despliega en --catalogo');
        console.log('OK: el agente y el interceptor compartidos estan puestos y son portantes');
        console.log('OK: ninguna estrategia inventa el año de lanzamiento');
    } finally {
        fs.rmSync(dirSonda, { recursive: true, force: true });
    }
})().catch((e) => { console.error(e.message); process.exit(1); });
