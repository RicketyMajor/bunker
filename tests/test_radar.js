// Guard for the ONE thing the radar unification could silently change: which extra fields each
// radar attaches to an item before POSTing it. `MovieWishlist` has `priority`/`added_by` columns
// (movies/models.py:89-90); `MusicWishlist` has neither (disquera/models.py:62-73). Merging the
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

// --- Estrategia de sonda, plantada en disco porque `barrer` las lee de ahi ---------------
const CARPETA = '_sonda';
const dirSonda = path.join(RAIZ, 'strategies', CARPETA);
fs.mkdirSync(dirSonda, { recursive: true });
fs.writeFileSync(path.join(dirSonda, 'sonda.js'), `
module.exports = {
    name: 'Sonda',
    scrape: async () => [{ title: 'Disco de prueba' }],
};
`);

// --- axios apuñalado: `require` devuelve la MISMA instancia que ve radar.js --------------
const axios = require('axios');
const enviados = [];
axios.get = async () => ({ data: [{ keyword: 'objetivo' }] });
axios.post = async (url, item) => { enviados.push({ url, item }); return { status: 201 }; };

const { barrer } = require(path.join(RAIZ, 'radar.js'));

async function conducir(cfg) {
    enviados.length = 0;
    await barrer({ ...cfg, carpeta: CARPETA });
    // Una COPIA, no el array vivo: devolverlo tal cual hacia que la segunda llamada vaciara y
    // rellenara el resultado de la primera, y las dos comprobaciones miraban el item musical.
    return [...enviados];
}

(async () => {
    try {
        const deCine = await conducir(movie);
        const deMusica = await conducir(music);

        // Vacuidad primero: si `barrer` no llego a postear nada, todo lo de abajo pasa por vacio.
        assert.strictEqual(deCine.length, 1, `el radar de cine no posteo nada: el barrido no corrio`);
        assert.strictEqual(deMusica.length, 1, `el radar musical no posteo nada: el barrido no corrio`);

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

        console.log('OK: los dos radares comparten cuerpo, y cada uno manda lo suyo por el cable');
    } finally {
        fs.rmSync(dirSonda, { recursive: true, force: true });
    }
})().catch((e) => { console.error(e.message); process.exit(1); });
