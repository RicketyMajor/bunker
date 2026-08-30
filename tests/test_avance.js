// Guard for the one thing the APK does that a browser never does: `cargarEstado()` replaces
// `estado` wholesale with the bridge's snapshot. That snapshot lives in native SharedPreferences
// (`AssetStore.estadoCacheado`) and only a COMPLETED sync writes it, while `#pg-guardar` advances
// `estado.leyendo.current_page` in memory and `PUENTE.sincronizar()` is fire-and-forget. Taking
// the envelope wholesale therefore discarded the capture's own advance and repainted the OLD page
// number — on the phone only, which is why the web paths look correct and the defect survived.
//
// This drives the REAL `cargarEstado()` against a stubbed bridge, not an extracted helper: the
// lesson of tests/test_radar.js is that inverting only the readers leaves the writer unproven.
// The local advance is planted the way the app plants it, through the localStorage cache that
// `leerCache()` reads at module load.
//
// Runs on the HOST: app.js has no npm dependencies, only './queue.js'.
// Run: node tests/test_avance.js        (see cli/doctor.py)
import assert from 'node:assert';
import { pathToFileURL } from 'node:url';

const LLAVE = 'transmisor_estado';
const almacen = new Map();
globalThis.localStorage = {
  getItem: (k) => (almacen.has(k) ? almacen.get(k) : null),
  setItem: (k, v) => almacen.set(k, String(v)),
  removeItem: (k) => almacen.delete(k),
};

// Every element cargarEstado() paints into, and nothing else: a null from querySelector would
// throw inside pintarHome and the failure would name the stub instead of the behaviour.
const elemento = () => ({ innerHTML: '', textContent: '', className: '', hidden: false,
                          classList: { add() {}, remove() {} }, style: {} });
const pintados = new Map();
globalThis.document = {
  querySelector: (sel) => { if (!pintados.has(sel)) pintados.set(sel, elemento()); return pintados.get(sel); },
  getElementById: (id) => pintados.get(`#${id}`) || elemento(),
  addEventListener() {},
};

// The snapshot the bridge will hand back. Swapped per case.
let snapshot = {};
globalThis.window = {
  Bunker: {
    estado: () => JSON.stringify({ estado: snapshot, sincronizado: null, en_linea: false, alarma_exacta: true }),
    pendientes: () => 0,
    listar: () => '[]',
    sincronizar() {},
  },
};

// The local advance, planted through the cache exactly as guardarEstado() writes it.
const LOCAL = { leyendo: { book_id: 7, title: 'Libro', current_page: 120, page_count: 300 },
                libros: [], peliculas: [], albums: [] };
almacen.set(LLAVE, JSON.stringify({ estado: LOCAL, sincronizado: null }));

const app = await import(pathToFileURL('bunker_core/static/movil/app.js').href);

// Vacuity guard, and it goes HERE rather than at the end: with the cases first, a missing
// export dies on the first `app.cargarEstado()` with a TypeError and this line never runs —
// a guard that cannot fire is not a guard.
assert.ok(app.estado && typeof app.cargarEstado === 'function',
          'app.js no expone `estado` y `cargarEstado`: la bateria no probaria nada');

let fallos = 0;
async function caso(nombre, snap, esperado) {
  snapshot = snap;
  await app.cargarEstado();
  const real = app.estado.leyendo ? app.estado.leyendo.current_page : null;
  if (real === esperado) { console.log(`  ok   ${nombre} -> ${real}`); }
  else { console.log(`  FALLA ${nombre}: esperaba ${esperado}, llego ${real}`); fallos++; }
}

// El defecto: el snapshot nativo va por detras del avance local. Gana el local.
await caso('el avance local sobrevive a un snapshot atrasado',
           { leyendo: { book_id: 7, title: 'Libro', current_page: 100, page_count: 300 }, libros: [] }, 120);

// El servidor por delante (registraste desde el escritorio). Gana el servidor.
await caso('un servidor por delante gana',
           { leyendo: { book_id: 7, title: 'Libro', current_page: 150, page_count: 300 }, libros: [] }, 150);

// Otro libro: la posicion vieja no se arrastra al libro nuevo.
await caso('la posicion no se arrastra a otro libro',
           { leyendo: { book_id: 9, title: 'Otro', current_page: 10, page_count: 200 }, libros: [] }, 10);

console.log(fallos === 0 ? `\ntest_avance: 3 casos · 0 fallos` : `\ntest_avance: ${fallos} FALLOS`);
process.exit(fallos === 0 ? 0 : 1);
