// El diálogo del token, EJECUTANDO EL BUNDLE QUE SE SIRVE — no leyendo el fuente.
//
// `tests/test_token_pwa.js` fija el token en las tres salidas HTTP, pero comprueba el cableado
// de `main.js` con una expresión regular sobre el fichero. Nadie EJECUTABA main.js: es el punto
// de entrada, no lo importa ningún test, y su lógica («abre el diálogo si no hay token, y NUNCA
// dentro del APK») sólo existe ahí. Este proyecto ha enviado tres veces una suite verde sobre
// una pantalla en blanco — `37a9359` fue una TUI muerta dos días. Un regex sobre el fuente es
// exactamente esa clase de verde.
//
// Carga `dist/main.js` (formato IIFE) contra un DOM mínimo, así que además prueba que el BUILD
// no se dejó nada por el camino.
//
// Corre en el HOST. Run: node tests/test_dialogo_token.js        (ver cli/doctor.py)
import assert from 'node:assert';
import fs from 'node:fs';
import vm from 'node:vm';

let fallos = 0, corridos = 0;
const caso = (n, f) => { corridos++;
                         try { f(); console.log(`  ok   ${n}`); }
                         catch (e) { console.log(`  FALLA ${n}: ${e.message}`); fallos++; } };

const BUNDLE = fs.readFileSync('bunker_core/static/movil/dist/main.js', 'utf8');

// Un escenario = un mundo nuevo. El bundle guarda `PUENTE` en una constante de módulo, así que
// reutilizar el contexto haría que el segundo caso midiera el estado del primero.
function correr({ token = null, apk = false } = {}) {
  const almacen = new Map();
  if (token !== null) almacen.set('bunker_token', token);
  const registro = { showModal: 0, close: 0, recargas: 0 };

  const nodo = (id) => ({
    id, value: '', textContent: '', innerHTML: '', className: '', hidden: false,
    dataset: {}, style: {}, open: false,
    classList: { add() {}, remove() {}, toggle() {} },
    setAttribute() {}, getAttribute: () => null, append() {}, appendChild() {}, remove() {},
    addEventListener(ev, fn) { (this.oyentes ||= {})[ev] = fn; },
    querySelector: () => nodo('p'), querySelectorAll: () => [],
    showModal() { registro.showModal++; this.open = true; },
    close() { registro.close++; this.open = false; },
  });
  const porId = new Map();
  const dame = (id) => { if (!porId.has(id)) porId.set(id, nodo(id)); return porId.get(id); };

  const doc = {
    getElementById: dame,
    querySelector: (s) => dame(s), querySelectorAll: () => [],
    createElement: (t) => nodo(t), createElementNS: (ns, t) => nodo(t),
    addEventListener() {}, body: nodo('body'),
  };
  const ventana = {
    CSRF_TOKEN: 'csrf', addEventListener() {},
    localStorage: {
      getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
      setItem: (k, v) => almacen.set(k, String(v)),
      removeItem: (k) => almacen.delete(k),
    },
    location: { pathname: '/panel/', search: '', href: '', reload: () => registro.recargas++ },
    navigator: { vibrate() {}, mediaDevices: {} },
    document: doc,
    fetch: async () => ({ ok: true, status: 200, json: async () => ({}) }),
    setTimeout, clearTimeout, setInterval, clearInterval, console,
    // APIs del navegador que el bundle usa al montar. No son parte de lo que se prueba: sin
    // ellas el fallo nombraría al stub y no al comportamiento.
    URLSearchParams, URL, TextEncoder, TextDecoder,
    history: { replaceState() {} },
    MutationObserver: class { observe() {} disconnect() {} },
  };
  if (apk) ventana.Bunker = { encolar: () => {}, listar: () => '[]', pendientes: () => 0,
                              estado: () => JSON.stringify({ estado: {}, en_linea: false }),
                              sincronizar() {} };
  ventana.window = ventana;
  ventana.globalThis = ventana;
  ventana.localStorage = ventana.localStorage;

  vm.createContext(ventana);
  vm.runInContext(BUNDLE, ventana, { filename: 'dist/main.js' });
  return { registro, dame, ventana, almacen };
}

// --- 1. Sin token: el diálogo SALE ------------------------------------------------------------
const vacio = correr({ token: null });
caso('sin token guardado, el diálogo se abre solo',
  () => assert.strictEqual(vacio.registro.showModal, 1));

// --- 2. Con token: NO molesta -----------------------------------------------------------------
const conToken = correr({ token: 'ya-lo-tengo' });
caso('con token guardado, el diálogo NO se abre',
  () => assert.strictEqual(conToken.registro.showModal, 0));

// --- 3. Dentro del APK: NUNCA, ni sin token ---------------------------------------------------
// El JS del APK no hace una sola petición (queue.js delega en el puente, app.js sale antes de
// su fetch), así que pedirle el token taparía la pantalla de captura por nada.
const apk = correr({ token: null, apk: true });
caso('dentro del APK el diálogo NO se abre aunque no haya token',
  () => assert.strictEqual(apk.registro.showModal, 0));

// --- 4. Guardar: persiste y recarga ------------------------------------------------------------
const g = correr({ token: null });
g.dame('tk-valor').value = '  token-tecleado  ';
g.dame('tk-guardar').oyentes.click();
caso('al guardar, el token queda en localStorage sin espacios',
  () => assert.strictEqual(g.almacen.get('bunker_token'), 'token-tecleado'));
caso('al guardar, la página se recarga para rehacer las peticiones',
  () => assert.strictEqual(g.registro.recargas, 1));

// --- 5. Un campo vacío no guarda nada ni recarga -----------------------------------------------
const v = correr({ token: null });
v.dame('tk-valor').value = '   ';
v.dame('tk-guardar').oyentes.click();
caso('un campo vacío no guarda ni recarga',
  () => assert.ok(!v.almacen.has('bunker_token') && v.registro.recargas === 0));

// --- 6. "AHORA NO" cierra ----------------------------------------------------------------------
const c = correr({ token: null });
c.dame('tk-cerrar').oyentes.click();
caso('AHORA NO cierra el diálogo', () => assert.strictEqual(c.registro.close, 1));

console.log(fallos === 0
  ? `\ntest_dialogo_token: ${corridos} casos · 0 fallos`
  : `\ntest_dialogo_token: ${corridos} casos · ${fallos} FALLOS`);
process.exit(fallos === 0 ? 0 : 1);
