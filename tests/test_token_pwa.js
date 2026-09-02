// El token de la API en la PWA, y las TRES salidas HTTP que tiene — no una.
//
// El plan sólo nombraba `pedir()`. Contadas en el árbol el 2026-08-31, las salidas son tres y
// las tres van a `/api/`:
//   · estado.js:pedir()  — las lecturas del panel
//   · app.js:cargarEstado() — el estado de lectura entero del teléfono
//   · queue.js:vaciar()  — LA QUE ESCRIBE: las capturas, por sus nueve rutas
// Con sólo la primera, en cuanto la Tarea 5 encienda el middleware las capturas responden 403,
// vuelven a la cola y el chip se queda clavado en "N SIN TRANSMITIR" para siempre — que es
// exactamente el modo de fallo que el comentario de queue.js:96 existe para describir.
//
// Corre en el HOST: ninguno de los tres toca el DOM al cargarse.
// Run: node tests/test_token_pwa.js        (ver cli/doctor.py)
import assert from 'node:assert';

const almacen = new Map();
globalThis.localStorage = {
  getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)),
  removeItem: (k) => almacen.delete(k),
};
const elemento = () => ({ innerHTML: '', textContent: '', className: '', hidden: false,
                          dataset: {}, classList: { add() {}, remove() {} }, style: {},
                          setAttribute() {} });
globalThis.document = {
  querySelector: () => elemento(), getElementById: () => elemento(),
  createElement: elemento, addEventListener() {},
};
globalThis.window = { CSRF_TOKEN: 'csrf-abc' };

let vistas = [];
let respuesta = { ok: true, status: 200, json: async () => ({ ok: true }) };
globalThis.fetch = async (url, opciones = {}) => {
  vistas.push({ url, headers: opciones.headers || {} });
  return respuesta;
};

const E = await import('../bunker_core/static/movil/estado.js');
const Cola = await import('../bunker_core/static/movil/queue.js');
const App = await import('../bunker_core/static/movil/app.js');

let fallos = 0;
let corridos = 0;
const caso = (n, f) => { corridos++;
                         try { f(); console.log(`  ok   ${n}`); }
                         catch (e) { console.log(`  FALLA ${n}: ${e.message}`); fallos++; } };
const tokenDe = (v) => (v.headers && (v.headers['X-Bunker-Api-Token']
                                      ?? (v.headers.get && v.headers.get('X-Bunker-Api-Token'))));

const TOKEN = 'secreto-123';
E.guardarToken(TOKEN);

// VACUIDAD PRIMERO. En la Tarea 2 una comprobación de esta forma salió VERDE con el defecto
// presente porque comparaba `undefined` con `undefined`. Aquí el token se planta arriba, así
// que lo que hay que fijar es que de verdad quedó guardado antes de comparar nada con él.
caso('el token guardado no está vacío (si no, todo lo de abajo es vacío)',
  () => assert.ok(E.token() && E.token() === TOKEN));
caso('el token sobrevive a una recarga (localStorage)',
  () => assert.strictEqual(E.token(), TOKEN));

// --- 1. pedir(): las lecturas del panel ------------------------------------------------------
vistas = [];
await E.pedir('/api/stats/timeline/', elemento());
caso('pedir() manda X-Bunker-Api-Token', () => {
  assert.strictEqual(vistas.length, 1, 'pedir() no llegó a fetch');
  assert.strictEqual(tokenDe(vistas[0]), TOKEN);
});
caso('pedir() conserva su Accept: application/json',
  () => assert.strictEqual(vistas[0].headers['Accept'], 'application/json'));

// --- 2. queue.js: LA QUE ESCRIBE -------------------------------------------------------------
vistas = [];
respuesta = { ok: true, status: 201, json: async () => ({}) };
Cola.encolar('paginas', { book_id: 1, pages: 10 });
await Cola.vaciar();
caso('vaciar() manda el token en la captura', () => {
  assert.strictEqual(vistas.length, 1, 'vaciar() no posteó: la cola estaba vacía');
  assert.strictEqual(tokenDe(vistas[0]), TOKEN);
});
caso('vaciar() NO pierde el X-CSRFToken al ganar el suyo',
  () => assert.strictEqual(vistas[0].headers['X-CSRFToken'], 'csrf-abc'));
caso('vaciar() NO pierde su Content-Type',
  () => assert.strictEqual(vistas[0].headers['Content-Type'], 'application/json'));

// --- 3. app.js: el estado de lectura del teléfono --------------------------------------------
vistas = [];
respuesta = { ok: true, status: 200, json: async () => ({ leyendo: null }) };
await App.cargarEstado();
caso('cargarEstado() manda el token', () => {
  assert.strictEqual(vistas.length, 1, 'cargarEstado() no llegó a fetch');
  assert.strictEqual(tokenDe(vistas[0]), TOKEN);
});

// --- 4. El sexto estado: un 403 no es `roto` ni `rechazado` -----------------------------------
respuesta = { ok: false, status: 403, json: async () => ({}) };
const d = elemento();
await E.pedir('/api/stats/timeline/', d);
caso('un 403 deja el bloque en sin-token, no en rechazado',
  () => assert.strictEqual(d.dataset.estado, E.ESTADOS.SIN_TOKEN));
caso('ESTADOS.SIN_TOKEN existe y vale "sin-token"',
  () => assert.strictEqual(E.ESTADOS.SIN_TOKEN, 'sin-token'));

// Un 400 SIGUE siendo `rechazado`: mapear todo no-ok a sin-token borraría el quinto estado.
respuesta = { ok: false, status: 400, json: async () => ({ error: 'x' }) };
const d400 = elemento();
await E.pedir('/api/stats/timeline/', d400);
caso('un 400 sigue siendo rechazado, no sin-token',
  () => assert.strictEqual(d400.dataset.estado, E.ESTADOS.RECHAZADO));

// --- 5. Sin token guardado, no se inventa cabecera vacía que parezca válida -------------------
almacen.clear();
vistas = [];
respuesta = { ok: true, status: 200, json: async () => ({ ok: true }) };
await E.pedir('/api/stats/timeline/', elemento());
caso('sin token guardado, token() es cadena vacía y no revienta',
  () => assert.strictEqual(E.token(), ''));

// El número lo cuenta el propio bucle. Escrito a mano decía 11 cuando corrían 12.
// guardarToken NO se traga el fallo de localStorage: lo devuelve. `test_panel.py` prohíbe un
// catch vacío en estas fuentes, y con razón — recargar tras un guardado fallido pierde el token.
caso('guardarToken devuelve true cuando persiste',
  () => assert.strictEqual(E.guardarToken('otro-token'), true));
const setItemReal = globalThis.localStorage.setItem;
globalThis.localStorage.setItem = () => { throw new Error('modo privado'); };
caso('guardarToken devuelve false si localStorage lanza, en vez de tragárselo',
  () => assert.strictEqual(E.guardarToken('x'), false));
globalThis.localStorage.setItem = setItemReal;
E.guardarToken(TOKEN);

// --- 6. EL APK: el puente nativo hace que el JS no pida nada, así que no se le pregunta ------
// Con `window.Bunker` presente, queue.js:67 delega en nativo y app.js sale por la rama del
// puente antes de su fetch. El diálogo taparía la captura en cada arranque por un token que esa
// WebView no usa. Se comprueba sobre el fichero porque main.js sí toca el DOM al cargarse.
const fs = await import('node:fs');
const main = fs.readFileSync('bunker_core/static/movil/main.js', 'utf8');
caso('main.js no abre el diálogo dentro del APK (mira window.Bunker)',
  () => assert.ok(/window\.Bunker/.test(main) && /enElApk \? null :/.test(main)));

globalThis.window.Bunker = { encolar: () => {}, listar: () => '[]', pendientes: () => 0 };
const Cola2 = await import('../bunker_core/static/movil/queue.js?apk=1');
vistas = [];
Cola2.encolar('paginas', { book_id: 1, pages: 3 });
await Cola2.vaciar();
caso('con el puente, vaciar() no hace NINGUNA petición desde el JS',
  () => assert.strictEqual(vistas.length, 0));
delete globalThis.window.Bunker;

console.log(fallos === 0
  ? `\ntest_token_pwa: ${corridos} casos · 0 fallos`
  : `\ntest_token_pwa: ${corridos} casos · ${fallos} FALLOS`);
process.exit(fallos === 0 ? 0 : 1);
