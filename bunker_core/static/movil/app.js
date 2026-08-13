// Screens, sheets and rendering. All capture goes through Cola.encolar; nothing here talks
// to the network except cargarEstado() and the flush it triggers.
const App = (() => {
  let estado = { leyendo: null, habitos_pendientes: [], libros: [], peliculas: [], albums: [] };
  let enLinea = false;

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

  async function cargarEstado() {
    try {
      const r = await fetch('/api/movil/estado/', { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      estado = await r.json();
      enLinea = true;
    } catch (e) {
      enLinea = false;
    }
    pintarHome();
    refrescarChip();
  }

  async function transmitir() {
    if (Cola.pendientes() === 0) { await cargarEstado(); return; }
    const { enviados, pendientes, alcanzoElServidor, ocupado } = await Cola.vaciar();
    // A flush already running is not evidence about the link either way; leave the chip alone.
    if (ocupado) return;
    enLinea = alcanzoElServidor;
    if (enviados > 0) toast(`${enviados} despacho(s) transmitido(s).`);
    else if (alcanzoElServidor) toast(`${pendientes} despacho(s) rechazado(s). Mira DESPACHOS.`, 'error');
    else toast('Sin enlace. Guardado igual.', 'error');
    pintarDespachos();
    refrescarChip();
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
    $('#n-habitos').textContent = estado.habitos_pendientes.length || '';
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
    $('#cerrar-despachos').addEventListener('click', () => $('#despachos').close());
    // Re-render on close so a half-armed DESCARTAR never survives into the next opening.
    $('#despachos').addEventListener('close', pintarDespachos);
    $('#btn-transmitir').addEventListener('click', transmitir);
    $('#lista-despachos').addEventListener('click', alPulsarDescartar);
    window.addEventListener('online', transmitir);
    window.addEventListener('offline', () => { enLinea = false; refrescarChip(); });

    // Delegated: pintarHome() replaces the card's markup on every sync, so a listener bound
    // to the button itself would survive exactly one refresh.
    document.addEventListener('click', (e) => {
      const boton = e.target.closest('[data-verb]');
      if (!boton) return;
      const verbo = boton.dataset.verb;
      if (verbo === 'paginas' || verbo === 'elegir-libro') abrirHojaPaginas();
      else if (verbo === 'terminar') abrirHojaTerminar();
    });

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
      }
      $('#hoja-paginas').close();
      refrescarChip();
      transmitir();
    });

    cargarEstado().then(transmitir);
  });

  return {
    toast, refrescarChip, abrirHoja, transmitir, cargarEstado,
    get estado() { return estado; },
  };
})();
