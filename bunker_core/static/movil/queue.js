// The capture queue.
//
// Captures are held here until the server acknowledges them with a 2xx, and only then are
// they removed. This is the only file in the app whose bugs are invisible: an item deleted
// without an acknowledgement is a capture silently lost. It has its own check at
// /movil/selftest/.
//
// ponytail: localStorage, not IndexedDB, and flushed from the page rather than the service
// worker. A service worker cannot read localStorage, so moving the flush there means moving
// the store too. The upgrade is worth it only when captures must sync without the app being
// opened, or when the queue has to carry images.
const Cola = (() => {
  const LLAVE = 'transmisor_cola';

  // Wire verb -> endpoint. The phone writes to the real endpoints; only barcodes go to an
  // inbox, because a barcode is an incomplete fact and the Purgatorio exists for exactly that.
  // All eleven resolve against the URL conf. Do not write that number anywhere else: the
  // count in this comment used to say eleven while the map held twelve. /movil/selftest/
  // asserts the exact key set instead, so a route added or removed here fails there.
  const RUTAS = {
    paginas:        '/api/books/tracker/pages/',
    terminar_libro: '/api/books/tracker/finish/',
    terminar_peli:  '/api/movies/tracker/finish/',
    terminar_disco: '/api/music/tracker/finish/',
    habito:         '/posada/api/habits/complete/',
    escaneo_libro:  '/api/books/inbox/',
    escaneo_peli:   '/api/movies/inbox/',
    escaneo_disco:  '/api/music/inbox/',
    wishlist_libro: '/api/books/wishlist/add/',
    wishlist_peli:  '/api/movies/wishlist/',
    wishlist_disco: '/api/music/wishlist/',
  };

  const leer = () => JSON.parse(localStorage.getItem(LLAVE) || '[]');
  const escribir = (items) => localStorage.setItem(LLAVE, JSON.stringify(items));

  // The device's local date. Assumed America/Santiago, same as the server; capturing from
  // another timezone can land a capture one day off, which is recorded in the spec.
  const hoyLocal = () => {
    const d = new Date();
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  };

  function encolar(verbo, payload) {
    if (!RUTAS[verbo]) throw new Error(`verbo desconocido: ${verbo}`);
    const items = leer();
    items.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      verbo,
      payload: { occurred_on: hoyLocal(), ...payload },
      creado: new Date().toISOString(),
      error: null,
    });
    escribir(items);
    return items.length;
  }

  // Two flushes overlapping would POST every pending capture twice — the reconnect handler
  // and a manual tap are enough to cause it, and the server would happily log both.
  let vaciando = false;

  async function vaciar(fetchImpl) {
    if (vaciando) return { enviados: 0, pendientes: leer().length, ocupado: true };
    vaciando = true;
    try {
      const enviar = fetchImpl || ((url, opts) => fetch(url, opts));
      const items = leer();
      const quedan = [];
      // "The server answered" and "the capture was accepted" are different facts, and the
      // chip needs the first one. A queue rejected wholesale with 409s has enviados === 0
      // while the link is perfectly fine; without this the app would report SIN ENLACE while
      // talking to the server.
      let alcanzoElServidor = false;

      let retirados = 0;

      for (const item of items) {
        // A verb this version no longer knows can never be accepted: its route is gone from
        // the URL conf too. Without this it POSTs to `undefined` — literally `/undefined` —
        // gets a 404, is re-queued, and pins the chip at "1 SIN TRANSMITIR" for ever, with
        // DESCARTAR as the only escape. This is the one exception to "an item leaves only on
        // a 2xx", and it is narrow on purpose: the item cannot succeed, now or later.
        if (!RUTAS[item.verbo]) { retirados++; continue; }
        try {
          const resp = await enviar(RUTAS[item.verbo], {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN || '' },
            body: JSON.stringify(item.payload),
          });
          alcanzoElServidor = true;
          if (resp.ok) continue;  // 2xx: the only reason an item ever leaves this queue.
          let detalle = `HTTP ${resp.status}`;
          try {
            const cuerpo = await resp.json();
            // Three shapes reach here. The hand-written views answer {message} or {error},
            // but the ModelViewSets answer DRF's field-error dict —
            // {"isbn": ["scan inbox with this isbn already exists."]} — which is exactly what
            // a barcode scanned twice produces. Without the third branch Despachos shows a
            // bare "HTTP 400" and the reason is only in a network tab the phone has not got.
            const campo = Object.values(cuerpo || {})
              .find((v) => Array.isArray(v) && v.length && typeof v[0] === 'string');
            detalle = cuerpo.message || cuerpo.error || (campo && campo[0]) || detalle;
          } catch (_) { /* the body was not JSON; the status is all we have */ }
          quedan.push({ ...item, error: detalle });
        } catch (e) {
          quedan.push({ ...item, error: 'Sin enlace con el Bunker.' });
        }
      }

      // Re-read before writing. Every await above is a window in which the user can tap a
      // sheet, and that capture lands in localStorage but not in `items` — writing `quedan`
      // alone would erase it. This is the silent loss this whole file exists to prevent.
      const procesados = new Set(items.map((i) => i.id));
      const llegadosDurante = leer().filter((i) => !procesados.has(i.id));
      escribir([...quedan, ...llegadosDurante]);

      return {
        // `retirados` is subtracted rather than folded in: a dropped verb was not transmitted,
        // and reporting it as sent would be the app lying about a capture reaching the Bunker.
        enviados: items.length - quedan.length - retirados,
        pendientes: quedan.length + llegadosDurante.length,
        retirados,
        alcanzoElServidor,
      };
    } finally {
      vaciando = false;
    }
  }

  const descartar = (id) => escribir(leer().filter((i) => i.id !== id));

  return {
    RUTAS,
    encolar,
    vaciar,
    descartar,
    items: leer,
    pendientes: () => leer().length,
  };
})();
