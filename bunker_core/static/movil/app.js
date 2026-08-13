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
    cargarEstado().then(transmitir);
  });

  return {
    toast, refrescarChip, abrirHoja, transmitir, cargarEstado,
    get estado() { return estado; },
  };
})();
