// Screens, sheets and rendering. All capture goes through Cola.encolar; nothing here talks
// to the network except cargarEstado() and the flush it triggers.
import * as Cola from './queue.js';
// The lists every sheet reads. Cached in localStorage because /api/movil/estado/ is the one
// thing the app cannot fetch with the desktop off, and without a copy a cold start offline
// opens an app with no book, no habits and nothing to finish — which is every capture except
// loose pages and the scanner. That is not a degraded mode, it is the normal one.
//
// The service worker still must NOT cache that response (see sw.js). A response cache would
// be invalidated only by the network; this copy is invalidated by our own captures, which is
// what stops a finished book from being offered again while offline.
const LLAVE_ESTADO = 'transmisor_estado';
// Every list the sheets read belongs here, and a MISSING key is not harmless: a cold start
// offline reads this object, `estadoCacheado()` answers "{}" — which is truthy — so the guard
// in cargarEstado() hands VACIO straight to the sheets, and an absent key reads `undefined`.
// `aventureros` and `habitos_pendientes` were two more until the 2026-08-27 Posada split.
const VACIO = {
  leyendo: null, libros: [], peliculas: [], albums: [],
};

// Same bridge queue.js binds, bound the same way and for the same reason. Inside the APK the
// snapshot lives in native storage next to the queue, because a WebView serving local assets
// has origin appassets.androidplatform.net and every call to the tailnet would be cross-origin.
const PUENTE = typeof window !== 'undefined' && window.Bunker ? window.Bunker : null;

function leerCache() {
  try {
    const crudo = JSON.parse(localStorage.getItem(LLAVE_ESTADO) || 'null');
    return crudo && crudo.estado ? crudo : null;
  } catch (_) { return null; }
}

// The device's local date, as a string that can be compared. Same convention as the queue's
// occurred_on, deliberately: both answer "which day is this device on".
const diaLocal = (d = new Date()) => {
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

const cache = leerCache();
let estado = cache ? cache.estado : { ...VACIO };
let sincronizado = cache ? cache.sincronizado : null;
let enLinea = false;

// `habitos_pendientes` was the one day-dependent list in the snapshot and it was dropped past
// midnight for that reason. It left with the Posada split on 2026-08-27; every list that
// remains is an inventory and none of them expire. `diaLocal` stays: `pintarInstantanea` uses
// it to say how old the snapshot is.

// Failing to persist must never cost a capture: the queue has its own key and is written
// first everywhere in this file.
function guardarEstado() {
  try {
    localStorage.setItem(LLAVE_ESTADO, JSON.stringify({ estado, sincronizado }));
  } catch (_) { /* quota or private mode; the app keeps working against memory */ }
}

const $ = (sel) => document.querySelector(sel);

function toast(mensaje, tipo) {
  const t = $('#toast');
  t.textContent = mensaje;
  t.style.borderLeftColor = tipo === 'error' ? 'var(--red)' : 'var(--green)';
  t.classList.add('show');
  clearTimeout(t._id);
  t._id = setTimeout(() => t.classList.remove('show'), 3600);
}

// Three states, each with a glyph AND a word. SIN ENLACE is the normal condition whenever
// the desktop is off — it is deliberately not worded as an error, because if the app reads
// as broken every evening you stop trusting the queue.
function refrescarChip() {
  const chip = $('#chip');
  const n = Cola.pendientes();
  if (n > 0) {
    chip.className = 'pend';
    chip.textContent = `◐ ${n} SIN TRANSMITIR`;
  } else if (enLinea) {
    chip.className = 'ok';
    chip.textContent = '● EN LÍNEA';
  } else {
    chip.className = 'off';
    chip.textContent = '○ SIN ENLACE';
  }
}

// Takes the envelope when the caller already has one. `cargarEstado` parses it two lines above,
// and re-reading would cost a second bridge crossing, a second serialisation of the WHOLE
// snapshot on the native side and a second AlarmManager call — on the UI thread, for one
// boolean already in hand. Only the return-from-Settings path has nothing to pass.
//
// `!== false` and not `!`: in a plain browser there is no bridge and the key does not exist,
// and an absent key must read as "nothing to warn about". Same for a phone running a NEWER
// app.js against an OLDER APK, which the over-the-air asset update makes a real shape and not
// a hypothetical. That is the missing-key trap `VACIO` hit twice — `{}` is truthy and
// `undefined` is not `false`.
function pintarAvisoAlarma(sobre) {
  if (!PUENTE) return;
  const s = sobre || JSON.parse(PUENTE.estado());
  $('#aviso-alarma').hidden = s.alarma_exacta !== false;
}

async function cargarEstado() {
  if (PUENTE) {
    // The bridge answering is NOT evidence of a link: it hands back the cached snapshot, which
    // may be three days old. Freshness is a separate fact and the native side is the only thing
    // that knows it, so it is reported alongside rather than inferred here.
    const sobre = JSON.parse(PUENTE.estado());
    estado = sobre.estado && Object.keys(sobre.estado).length ? sobre.estado : { ...VACIO };
    sincronizado = sobre.sincronizado || null;
    enLinea = !!sobre.en_linea;
    pintarHome();
    refrescarChip();
    pintarInstantanea();
    pintarAvisoAlarma(sobre);
    return;
  }
  try {
    const r = await fetch('/api/movil/estado/', { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    estado = await r.json();
    sincronizado = new Date().toISOString();
    enLinea = true;
    guardarEstado();
  } catch (e) {
    enLinea = false;
  }
  pintarHome();
  refrescarChip();
}

async function transmitir() {
  if (Cola.pendientes() === 0) { await cargarEstado(); return; }
  if (PUENTE) {
    // `Cola.vaciar` is the localStorage flush and the APK's queue is not there. Asking the
    // worker is the only correct move, and its answer does not come back here: it arrives as a
    // notification and as the next snapshot. So the wording promises a request, not a result —
    // claiming "transmitido" for something that has not left the phone is precisely the lie
    // this whole project is built to avoid.
    PUENTE.sincronizar();
    toast('Transmisión pedida. El Búnker responde cuando haya enlace.');
    await cargarEstado();
    pintarDespachos();
    return;
  }
  const { enviados, pendientes, retirados, alcanzoElServidor, ocupado } = await Cola.vaciar();
  // A flush already running is not evidence about the link either way; leave the chip alone.
  if (ocupado) return;
  // Only when something was actually attempted. A flush that did nothing but discard retired
  // verbs never opened a socket, so it is no more evidence about the link than a flush that
  // was already running — and without this guard the chip flips to SIN ENLACE on a phone
  // that is online, and stays there until the next capture.
  if (enviados > 0 || pendientes > 0) enLinea = alcanzoElServidor;

  // One toast, never two: `toast()` writes into a single shared element, so a second call in
  // the same task erases the first before the browser has painted it. The retired-verb line
  // leads because it is the only path that removes a capture the server never saw, and it is
  // exactly the message that was being erased — a flush that discarded three captures used
  // to report "Sin enlace. Guardado igual.", which was the opposite of what happened.
  const retiro = retirados > 0
    ? `${retirados} despacho(s) de una función retirada, descartado(s). ` : '';
  const tono = retirados > 0 ? 'error' : undefined;
  if (enviados > 0) toast(`${retiro}${enviados} despacho(s) transmitido(s).`, tono);
  else if (alcanzoElServidor) toast(`${retiro}${pendientes} despacho(s) rechazado(s). Mira DESPACHOS.`, 'error');
  else if (pendientes > 0) toast(`${retiro}Sin enlace. Guardado igual.`, 'error');
  else if (retiro) toast(retiro.trim(), 'error');
  pintarDespachos();
  refrescarChip();
  // The link can drop with the app already open, and this is one of the two places that
  // learns it. Without the repaint the staleness line stays blank all evening — it would
  // only ever appear on a cold start, which is not when you need to be told.
  pintarInstantanea();
  if (enviados > 0) await cargarEstado();
}

function pintarHome() {
  const c = $('#leyendo');
  if (estado.leyendo) {
    const { title, author, current_page, page_count } = estado.leyendo;
    const pct = page_count ? Math.min(100, Math.round((current_page / page_count) * 100)) : 0;
    c.innerHTML = `
      <h2>Leyendo ahora</h2>
      <p class="title">${escapar(title)}</p>
      <p class="author">${escapar(author || '')}</p>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <p class="pos">${current_page} / ${page_count || '?'}</p>
      <button class="act" data-verb="paginas" style="margin-top:12px">+ PÁGINAS</button>`;
  } else {
    c.innerHTML = `
      <h2>Leyendo ahora</h2>
      <p class="title">Ningún libro en curso</p>
      <p class="author">Elige uno y empieza a marcar la página.</p>
      <button class="act" data-verb="elegir-libro" style="margin-top:12px">ELEGIR LIBRO</button>`;
  }
  pintarInstantanea();
}

// Cached lists are worth trusting for a day and worth doubting after a week. Naming when the
// snapshot was taken is the whole warning: nothing shown is wrong, it is just old. Silent
// while online, because then the lists are the server's.
function pintarInstantanea() {
  const el = $('#instantanea');
  if (!el) return;
  if (enLinea || !sincronizado) { el.textContent = ''; return; }
  // Calendar days, not 24-hour blocks: a snapshot taken at 23:00 and read at 08:00 is from
  // yesterday, and saying "de hoy" there is the same day-boundary lie that makes the cached
  // habit list wrong. Both now answer to diaLocal().
  const tomada = new Date(sincronizado);
  const dias = Math.round(
    (new Date(diaLocal()) - new Date(diaLocal(tomada))) / 86400000);
  el.textContent = dias <= 0
    ? 'inventario de hoy'
    : `inventario de hace ${dias} día${dias === 1 ? '' : 's'}`;
}

function pintarDespachos() {
  const ul = $('#lista-despachos');
  const items = Cola.items();
  if (items.length === 0) {
    ul.innerHTML = '<li style="color:var(--dim)">Nada pendiente. Todo transmitido.</li>';
    return;
  }
  // DESCARTAR is the only way to lose a capture on purpose, so it asks twice. A two-step
  // button rather than a confirm(): a native dialog blocks the page, and this queue is
  // often flushed from a phone that is halfway through something else.
  ul.innerHTML = items.map((i) => `
    <li style="border-bottom:1px solid var(--bg-alt);padding:10px 0">
      <div>${i.error ? '✗' : '◐'} ${escapar(resumir(i))}</div>
      ${i.error ? `<div style="color:var(--red);font-size:14px">${escapar(i.error)}</div>` : ''}
      <button data-descartar="${i.id}"
              style="min-height:48px;background:none;border:1px solid var(--bg-alt);
                     color:var(--dim);font:inherit;margin-top:6px">DESCARTAR</button>
    </li>`).join('');
}

const resumir = (i) => `${i.verbo} · ${i.payload.occurred_on}`;
const escapar = (s) => String(s).replace(/[&<>"]/g, (m) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[m]));

function abrirHoja(id) { document.getElementById(id).showModal(); }

// The sheet asks which page you reached, not how many you read: the book is open in front
// of you at 272, whereas "how many" makes you subtract from memory. The server computes
// the delta against the last known position.
//
// It also absorbs the empty state, which is the normal path on this database rather than
// the exception. With no book in progress the home card offers ELEGIR LIBRO, and choosing
// a book *is* marking a page in it — movil_estado derives `leyendo` from the last session
// that carries one, so there is nothing else to record. Two buttons, one sheet.
function pintarDelta() {
  const leyendo = estado.leyendo;
  const v = parseInt($('#pg').value, 10);
  const salida = $('#pg-delta');
  if ($('#pg-sueltas').checked) {
    salida.textContent = 'páginas sueltas';
  } else if (!leyendo) {
    // Nothing to compare against here: the previous position of a book chosen from the
    // picker lives on the server, which is what computes its delta.
    salida.textContent = (estado.libros || []).length ? '' : 'no hay libros por leer en el vault';
  } else if (isNaN(v)) {
    salida.textContent = `eran ${leyendo.current_page}`;
  } else {
    const d = v - leyendo.current_page;
    salida.textContent = d >= 0
      ? `eran ${leyendo.current_page} · +${d} páginas`
      : `eran ${leyendo.current_page} · relectura, cuenta 0`;
  }
}

function abrirHojaPaginas() {
  const leyendo = estado.leyendo;
  const libros = estado.libros || [];
  $('#pg-libro-campo').style.display = leyendo ? 'none' : 'block';
  if (!leyendo) {
    const sel = $('#pg-libro');
    sel.innerHTML = '';
    // new Option() sets the title as text, not markup. This is the one list in the app
    // that carries user data without going through escapar(), and it is safe for that
    // reason rather than by luck.
    for (const l of libros) sel.add(new Option(l.title, l.id));
  }
  $('#pg').value = '';
  // Loose pages are the only mode left when there is no book in progress and nothing to
  // pick — an ebook or anything outside the vault.
  $('#pg-sueltas').checked = !leyendo && libros.length === 0;
  pintarDelta();
  abrirHoja('hoja-paginas');
}

// One sheet for the three collections: the verb is the same gesture, only the endpoint and
// the id key change.
//
// `is_owned` is sent for books and only for books. finish_book gates Book.is_read on it,
// while finish_movie and finish_album mark their flag whenever the id resolves — measured,
// not assumed. Anything picked here came out of the vault, so it is owned by definition;
// without this a finished book keeps being offered by movil_estado forever.
const FT = {
  libro: { lista: 'libros',    verbo: 'terminar_libro', id: 'book_id',  extra: { is_owned: true } },
  peli:  { lista: 'peliculas', verbo: 'terminar_peli',  id: 'movie_id', extra: {} },
  disco: { lista: 'albums',    verbo: 'terminar_disco', id: 'album_id', extra: {} },
};
const FT_VACIO = {
  libro: 'No hay libros por leer en el vault.',
  peli: 'No hay películas por ver en el inventario.',
  disco: 'No hay discos por escuchar en el inventario.',
};
let ftTipo = 'libro';

function pintarFT() {
  const cfg = FT[ftTipo];
  const todos = estado[cfg.lista] || [];
  const q = $('#ft-buscar').value.trim().toLowerCase();
  const items = todos.filter((i) => i.title.toLowerCase().includes(q)).slice(0, 40);
  // An empty inventory and a query nothing matches are different problems. Telling you to
  // sync when there is simply nothing there sends you looking for a fault that isn't real —
  // and with zero movies in the inventory today, that is the branch this app opens on.
  const vacio = todos.length === 0 ? FT_VACIO[ftTipo] : `Nada coincide con “${escapar(q)}”.`;
  $('#ft-lista').innerHTML = items.length
    ? items.map((i) => `<li><button data-ft="${i.id}"
         style="width:100%;text-align:left;min-height:52px;background:none;border:0;
                border-bottom:1px solid var(--bg-alt);color:var(--fg);
                font:inherit">${escapar(i.title)}</button></li>`).join('')
    : `<li style="color:var(--dim)">${vacio}</li>`;
  document.querySelectorAll('.tsel').forEach((b) => {
    const activo = b.dataset.tipo === ftTipo;
    b.setAttribute('aria-pressed', String(activo));
    b.style.borderColor = activo ? 'var(--yellow)' : 'var(--bg-alt)';
  });
}

function abrirHojaTerminar() {
  ftTipo = 'libro';
  $('#ft-buscar').value = '';
  pintarFT();
  abrirHoja('hoja-terminar');
}

// --- Escáner -------------------------------------------------------------------------
// Native BarcodeDetector, not a library. Chrome on Android has shipped it since 83, which
// is why the three templates this replaces pulled html5-qrcode from unpkg.com — and why
// they could never work without signal, in a feature whose whole point is a shop basement.
const SC = { libro: 'escaneo_libro', peli: 'escaneo_peli', disco: 'escaneo_disco' };
const SC_CAMPO = { libro: 'isbn', peli: 'barcode', disco: 'barcode' };
let scStream = null;
let scLoop = null;
let scTipo = 'libro';
const scVistos = new Set();

// Split from the camera deliberately: everything in here can be exercised without one,
// which is the only reason this sheet has a check at all. The camera's own job — turning
// photons into a string — is the part that needs a real device.
function registrarCodigo(valor) {
  // Keyed by type: the same barcode is a different capture for a different collection,
  // and switching tabs mid-session must not be silently ignored.
  const clave = `${scTipo}:${valor}`;
  if (!valor || scVistos.has(clave)) return false;
  scVistos.add(clave);
  Cola.encolar(SC[scTipo], { [SC_CAMPO[scTipo]]: valor });
  $('#sc-lista').insertAdjacentHTML('afterbegin',
    `<li style="border-bottom:1px solid var(--bg-alt);padding:8px 0">✓ ${escapar(valor)} → Purgatorio</li>`);
  $('#sc-estado').textContent = 'Capturado. Sigue escaneando.';
  if (navigator.vibrate) navigator.vibrate(50);
  refrescarChip();
  return true;
}

function marcarSel(selector, atributo, valor) {
  document.querySelectorAll(selector).forEach((b) => {
    const activo = b.dataset[atributo] === valor;
    b.setAttribute('aria-pressed', String(activo));
    b.style.borderColor = activo ? 'var(--yellow)' : 'var(--bg-alt)';
  });
}

async function abrirEscaner() {
  if (!('BarcodeDetector' in window)) {
    toast('Este navegador no trae lector de códigos.', 'error');
    return;
  }
  scVistos.clear();
  // The TUI opens this from Biblioteca, Videoclub or Disquera and says which one in the
  // URL. Without it every entry point defaults to LIBRO, and a CD scanned from Disquera
  // goes to the book Purgatorio where its barcode can never resolve.
  const pedido = new URLSearchParams(location.search).get('scan');
  scTipo = SC[pedido] ? pedido : 'libro';
  marcarSel('.ssel', 'scan', scTipo);
  $('#sc-lista').innerHTML = '';
  $('#sc-estado').textContent = 'Apunta al código de barras.';
  abrirHoja('hoja-escaner');

  // The try covers play() and the srcObject assignment too, not just getUserMedia: if
  // playback is what fails, the sheet would otherwise sit on "Apunta al código de barras"
  // over a black rectangle for ever, with the reason only in a console the phone has not.
  let detector;
  const video = $('#sc-video');
  try {
    detector = new BarcodeDetector({ formats: ['ean_13', 'ean_8', 'upc_a'] });
    scStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
    });
    video.srcObject = scStream;
    await video.play();
  } catch (e) {
    // Permission refused, no camera, a device that cannot decode these formats, or a
    // playback the browser blocked. The sheet stays open so the message can be read.
    $('#sc-estado').textContent = 'Sin acceso a la cámara.';
    toast('Sin acceso a la cámara.', 'error');
    return;
  }

  scLoop = setInterval(async () => {
    try {
      const [codigo] = await detector.detect(video);
      if (codigo) registrarCodigo(codigo.rawValue);
    } catch (_) { /* no decodable frame this tick */ }
  }, 400);
}

// Bound to the dialog's `close` event rather than to the CERRAR button: showModal() also
// closes on Escape and on Android's back gesture, and neither goes through the button. A
// camera left streaming is the same discipline as the engine processes that used to leak,
// only this one lights a lamp on the phone to announce it.
function cerrarEscaner() {
  clearInterval(scLoop);
  scLoop = null;
  if (scStream) scStream.getTracks().forEach((t) => t.stop());
  scStream = null;
  const video = $('#sc-video');
  if (video) video.srcObject = null;
  transmitir();
}

// --- Wishlist ------------------------------------------------------------------------
const WL = { libro: 'wishlist_libro', peli: 'wishlist_peli', disco: 'wishlist_disco' };
let wlTipo = 'libro';

function alPulsarDescartar(e) {
  const boton = e.target.closest('[data-descartar]');
  if (!boton) return;
  if (boton.dataset.confirmando !== 'si') {
    boton.dataset.confirmando = 'si';
    boton.textContent = '¿SEGURO? DESCARTAR';
    boton.style.color = 'var(--red)';
    boton.style.borderColor = 'var(--red)';
    return;
  }
  Cola.descartar(boton.dataset.descartar);
  pintarDespachos();
  refrescarChip();
  toast('Despacho descartado.', 'error');
}

document.addEventListener('DOMContentLoaded', () => {
  $('#chip').addEventListener('click', () => { pintarDespachos(); abrirHoja('despachos'); });

  // The escape hatch, and it only exists inside the APK. A bad deploy from the laptop installs
  // itself on the phone by design; without a way back, the only cure is reinstalling the APK —
  // the exact fragility the APK was built to remove. A long press, not a button: it must be
  // hard to hit by accident and impossible to miss once you know it is there.
  if (PUENTE) {
    let reloj;
    const chip = $('#chip');
    const soltar = () => clearTimeout(reloj);
    chip.addEventListener('touchstart', () => {
      reloj = setTimeout(() => {
        PUENTE.revertirAssets();
        // "On the next launch" and not "done": the assets are resolved once at start, so
        // saying anything else would be describing a screen the user is not looking at.
        toast('Interfaz revertida a la del APK. Cierra y abre la app.', 'error');
      }, 1500);
    }, { passive: true });
    ['touchend', 'touchmove', 'touchcancel'].forEach((ev) =>
      chip.addEventListener(ev, soltar, { passive: true }));

    $('#permitir-alarma').addEventListener('click', () => {
      // `false` means no screen opened at all — an OEM that ships none. A button that looks
      // alive and does nothing for ever is the failure this banner exists to remove, so it
      // says so instead of repeating the trip.
      if (!PUENTE.pedirAlarmaExacta()) {
        toast('Este teléfono no trae la pantalla de alarmas exactas.', 'error');
      }
    });
    // Coming back from Settings is the only moment the answer can change, and the page is not
    // reloaded when it happens — without this the banner keeps nagging for a permission already
    // granted, until the app is closed and opened again.
    //
    // No `document.hidden` guard, deliberately. Nothing in `MainActivity` calls
    // `WebView.onPause()/onResume()`, so the document's visibility may never flip inside the
    // APK at all — which is why the Activity ALSO dispatches this event on window focus, the
    // signal this app already trusts for "the user is here". A repaint on a genuine hide costs
    // one prefs read; a repaint that never happens costs the whole feature.
    document.addEventListener('visibilitychange', () => pintarAvisoAlarma());
  }
  $('#cerrar-despachos').addEventListener('click', () => $('#despachos').close());
  // There used to be a `close` listener here re-rendering the list, so that a half-armed
  // DESCARTAR could not survive into the next opening. It never ran — `close` does not
  // fire, see the observer on the scanner below — and it was never needed: the chip
  // repaints the list before opening the dialog, which is what actually clears the arming.
  // Removed rather than left in place, because dead code that looks like a safety net
  // is worse than no safety net.
  $('#btn-transmitir').addEventListener('click', transmitir);
  $('#lista-despachos').addEventListener('click', alPulsarDescartar);
  window.addEventListener('online', transmitir);
  window.addEventListener('offline', () => {
    enLinea = false;
    refrescarChip();
    pintarInstantanea();  // the other place that learns the link dropped
  });

  // Delegated: pintarHome() replaces the card's markup on every sync, so a listener bound
  // to the button itself would survive exactly one refresh.
  document.addEventListener('click', (e) => {
    const boton = e.target.closest('[data-verb]');
    if (!boton) return;
    const verbo = boton.dataset.verb;
    if (verbo === 'paginas' || verbo === 'elegir-libro') abrirHojaPaginas();
    else if (verbo === 'terminar') abrirHojaTerminar();
    else if (verbo === 'escanear') abrirEscaner();
    else if (verbo === 'wishlist') {
      wlTipo = 'libro';
      marcarSel('.wsel', 'wl', wlTipo);
      $('#wl-titulo').value = '';
      abrirHoja('hoja-wishlist');
    }
  });

  // Escáner
  $('#hoja-escaner').addEventListener('click', (e) => {
    const b = e.target.closest('[data-scan]');
    if (b) { scTipo = b.dataset.scan; marcarSel('.ssel', 'scan', scTipo); }
  });
  $('#sc-cerrar').addEventListener('click', () => $('#hoja-escaner').close());
  // The camera has to stop on every way out of this sheet, and the `close` event cannot be
  // trusted to deliver that: measured in Chrome 151, no <dialog> in this app fires `close`
  // at all — not this one, not the pre-existing Despachos dialog, not a freshly created
  // element. Watching the dialog's own `open` attribute is DOM state rather than an event,
  // so the CERRAR button, Escape and Android's back gesture collapse into one fact: `open`
  // went away. A camera left streaming is the engine-process leak again, with a lamp on it.
  new MutationObserver(() => {
    if (!$('#hoja-escaner').open && scStream) cerrarEscaner();
  }).observe($('#hoja-escaner'), { attributes: true, attributeFilter: ['open'] });

  // Wishlist. A repeat is harmless on purpose: all three endpoints answer 200 without
  // saving, so the phone carries no dedup of its own and cannot disagree with the server.
  $('#hoja-wishlist').addEventListener('click', (e) => {
    const b = e.target.closest('[data-wl]');
    if (b) { wlTipo = b.dataset.wl; marcarSel('.wsel', 'wl', wlTipo); }
  });
  $('#wl-guardar').addEventListener('click', () => {
    const titulo = $('#wl-titulo').value.trim();
    if (!titulo) { toast('Escribe un título.', 'error'); return; }
    Cola.encolar(WL[wlTipo], { title: titulo });
    toast(`“${titulo}” anotado.`);
    $('#hoja-wishlist').close();
    refrescarChip();
    transmitir();
  });
  $('#wl-cerrar').addEventListener('click', () => $('#hoja-wishlist').close());

  // Scoped to the sheet rather than to document: the plan adds one document-level listener
  // per sheet, and five of them all running closest() on every tap in the app is noise.
  $('#hoja-terminar').addEventListener('click', (e) => {
    const pestana = e.target.closest('[data-tipo]');
    if (pestana) { ftTipo = pestana.dataset.tipo; pintarFT(); return; }
    const fila = e.target.closest('[data-ft]');
    if (!fila) return;
    const cfg = FT[ftTipo];
    const item = (estado[cfg.lista] || []).find((i) => String(i.id) === fila.dataset.ft);
    if (!item) return;
    Cola.encolar(cfg.verbo, { title: item.title, [cfg.id]: item.id, ...cfg.extra });
    // Drop it from the cached list too. Online the next cargarEstado() would do it; offline
    // nothing else will, and the same book would keep being offered — and finished — on every
    // opening until the desktop comes back.
    estado[cfg.lista] = (estado[cfg.lista] || []).filter((i) => i.id !== item.id);
    // `leyendo` is a separate field and the server keeps it consistent with a `is_read=False`
    // filter we cannot run here. Finishing the book you are reading has to clear it by hand,
    // or the home card goes on offering + PÁGINAS on a closed book across restarts, and every
    // page captured after that is logged against a book already queued as finished.
    if (ftTipo === 'libro' && estado.leyendo && estado.leyendo.book_id === item.id) {
      estado.leyendo = null;
    }
    guardarEstado();
    pintarHome();
    toast(`“${item.title}” registrado.`);
    $('#hoja-terminar').close();
    refrescarChip();
    transmitir();
  });
  $('#ft-buscar').addEventListener('input', pintarFT);
  $('#ft-cerrar').addEventListener('click', () => $('#hoja-terminar').close());
  $('#pg').addEventListener('input', pintarDelta);
  $('#pg-sueltas').addEventListener('change', pintarDelta);
  $('#pg-cerrar').addEventListener('click', () => $('#hoja-paginas').close());

  $('#pg-guardar').addEventListener('click', () => {
    const v = parseInt($('#pg').value, 10);
    if (isNaN(v) || v <= 0) { toast('Escribe un número.', 'error'); return; }
    if ($('#pg-sueltas').checked) {
      Cola.encolar('paginas', { pages: v });
      toast(`${v} páginas guardadas.`);
    } else {
      const libroId = estado.leyendo
        ? estado.leyendo.book_id
        : parseInt($('#pg-libro').value, 10);
      if (!libroId) { toast('Elige un libro.', 'error'); return; }
      Cola.encolar('paginas', { book_id: libroId, current_page: v });
      // Only the current book has a position this device knows about. For one just chosen
      // from the picker the delta is the server's to compute, so the toast reports where
      // you are rather than inventing a count.
      toast(estado.leyendo
        ? `${Math.max(v - estado.leyendo.current_page, 0)} páginas guardadas.`
        : `Vas en la página ${v}.`);
      // Advance the local position AFTER the toast has read the old one. Without this a
      // second capture before the next sync shows "eran 100" all evening; with it in the
      // wrong order the toast reports zero pages every time. The server recomputes the real
      // delta from its own row either way.
      if (estado.leyendo && estado.leyendo.book_id === libroId && v > estado.leyendo.current_page) {
        estado.leyendo.current_page = v;
        guardarEstado();
      }
    }
    $('#hoja-paginas').close();
    refrescarChip();
    transmitir();
  });

  cargarEstado().then(transmitir);
});

// `segundosSobrevividos` was exported here to be driven — the only arithmetic in this file that
// could be wrong in a way the interface would not show. It went with the Expedición block in the
// 2026-08-27 Posada split, and nothing that remains does arithmetic over time.
//
// `estado` was a getter (`get estado() { return estado; }`) while this file was an IIFE. A module
// export of a `let` is a LIVE BINDING, so a plain export reproduces the getter exactly — readers
// still see reassignments. This is the one line of the IIFE-to-module move that is not a pure
// move, and it is why it is called out here rather than left to be rediscovered.
export { toast, refrescarChip, abrirHoja, transmitir, cargarEstado, estado };
