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
};

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
    respuesta = await fetch(url, { headers: { 'Accept': 'application/json' } });
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
