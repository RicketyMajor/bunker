// The five states the spec makes non-negotiable, and the ONE function that produces them.
//
// Motivated by §1's `m`-key finding: an action whose non-200 fell through with no notify and no
// refresh, whose `except Exception: pass` swallowed the connection error, and which read as a
// dead key. Nothing in the panel may fetch except through here, so "a catch that swallows" has
// exactly one place it could live.

const ESTADOS = {
  CARGANDO: 'cargando',
  SIN_ENLACE: 'sin-enlace',
  RECHAZADO: 'rechazado',
  ROTO: 'roto',
  VACIO: 'vacio',
  LISTO: 'listo',
  // El sexto. Un 403 no es `roto` (el servidor está bien) ni `rechazado` (la petición está
  // bien): es "este Búnker no te conoce". Separarlo es lo que permite que el diálogo del token
  // aparezca solo, en vez de pedirle al dueño que interprete un "Rechazado (403)".
  SIN_TOKEN: 'sin-token',
};

// EL TOKEN DE LA API. Se TECLEA y se guarda aquí; Django NO lo inyecta en la página.
// `/movil/` tiene que seguir cargándose sin token para que el teléfono pueda pedirlo, así que
// un token escrito en ese HTML —como `window.CSRF_TOKEN` en app.html:352— sería un token
// regalado a cualquiera en la LAN que abra la página. El CSRF puede ir ahí porque es por
// sesión y no abre nada; éste abre los 18 ViewSets.
const LLAVE_TOKEN = 'bunker_token';

export const token = () => {
  try { return localStorage.getItem(LLAVE_TOKEN) || ''; } catch { return ''; }
};

// Devuelve si PERSISTIÓ. No se traga el fallo: en modo privado `setItem` lanza, el token no
// sobrevive a la recarga, y recargar igualmente lo perdería sin decir nada — que es justo el
// fallo silencioso que `test_panel.py` existe para prohibir.
export const guardarToken = (t) => {
  try { localStorage.setItem(LLAVE_TOKEN, t || ''); return true; } catch { return false; }
};

/**
 * Las cabeceras de `extra` MÁS la del token.
 *
 * Existe porque la PWA tiene TRES salidas HTTP, no una: `pedir()` aquí, `cargarEstado()` en
 * app.js y `vaciar()` en queue.js — y la tercera es la que ESCRIBE las capturas. Ponerlo sólo
 * en `pedir()` dejaba las capturas en 403 tras la Tarea 5, devueltas a la cola, con el chip
 * clavado en "N SIN TRANSMITIR" — el modo de fallo que queue.js:96 describe.
 *
 * Las del llamador ganan, como en `cli/sede.py`: el mismo módulo no debe poder pisar en
 * silencio un valor que el llamador puso a propósito.
 */
export const cabeceras = (extra = {}) => ({ 'X-Bunker-Api-Token': token(), ...extra });

// Un hueco, no un `document.querySelector`: este módulo se prueba sin DOM y `pedir()` no debe
// saber que existe un diálogo. main.js lo rellena; si nadie lo rellena, no pasa nada.
let alSinToken = () => {};
export const cuandoFalteToken = (fn) => { alSinToken = fn || (() => {}); };

function pintar(destino, estado, mensaje) {
  destino.dataset.estado = estado;
  destino.setAttribute('aria-busy', estado === ESTADOS.CARGANDO ? 'true' : 'false');
  if (mensaje !== undefined) destino.textContent = mensaje;
}

/**
 * Fetch `url` and leave `destino` in exactly one of the five states.
 *
 * Returns the parsed body on success and `null` otherwise, so a caller can render without ever
 * having to decide what a failure looks like — that decision is here and only here.
 */
export async function pedir(url, destino, { vacio = (d) => !d || d.length === 0 } = {}) {
  pintar(destino, ESTADOS.CARGANDO, 'Cargando…');
  let respuesta;
  try {
    respuesta = await fetch(url, { headers: cabeceras({ 'Accept': 'application/json' }) });
  } catch (err) {
    // The ONLY catch in the panel that swallows nothing: it produces a state, not a console line.
    // `err` is named in the message because "sin enlace" with no detail is what made the m-key
    // unreadable.
    pintar(destino, ESTADOS.SIN_ENLACE, `Sin enlace — la consulta no salió (${err.name}).`);
    return null;
  }
  if (respuesta.status >= 500) {
    pintar(destino, ESTADOS.ROTO, `El servidor falló (${respuesta.status}).`);
    return null;
  }
  // El 403 se separa ANTES del caso general: si no, cae en `rechazado` y el dueño lee
  // "Rechazado (403)" en vez de que le pidan el token. Sólo el 403 — un 400 sigue siendo
  // `rechazado`, porque mapear todo no-ok aquí borraría el quinto estado.
  if (respuesta.status === 403) {
    pintar(destino, ESTADOS.SIN_TOKEN, 'Este Búnker no te conoce. Introduce su token.');
    alSinToken();
    return null;
  }
  if (!respuesta.ok) {
    let detalle = '';
    // Deliberately empty, and the ONE exception to the rule above: the state is already decided
    // by the status code and this body is decoration. Task 11's grep allows this site by name.
    try { detalle = (await respuesta.json()).error || ''; } catch { detalle = ''; }
    pintar(destino, ESTADOS.RECHAZADO, `Rechazado (${respuesta.status}). ${detalle}`.trim());
    return null;
  }
  // A 200 carrying a body that is not JSON is `roto`, not a thrown promise nobody catches.
  // Measured 2026-08-21: Django's own 404/500 pages answer with HTML, and one of them reached
  // this function during Task 4's verification.
  let datos;
  try {
    datos = await respuesta.json();
  } catch (err) {
    pintar(destino, ESTADOS.ROTO, `El servidor respondió 200 con algo que no es JSON (${err.name}).`);
    return null;
  }
  if (vacio(datos)) {
    pintar(destino, ESTADOS.VACIO, 'Nada todavía.');
    return null;
  }
  pintar(destino, ESTADOS.LISTO);
  return datos;
}

export { ESTADOS };
