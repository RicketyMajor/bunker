import { pedir } from './estado.js';

// The consultation surface: "¿cómo voy?", answered in under five seconds, one-handed, at night.
//
// Design decisions worth not re-litigating:
//
// · ONE dominant figure (the prestige total) and everything else demoted. A grid of equal metric
//   boxes is the default this rejects — it has no focal point, so the eye has nowhere to go.
// · Gruvbox, the system the TUI and the PWA already share. Not a new palette.
// · Status is NEVER colour alone. `dataviz`'s validator was run on --yellow/--green/--red/--blue
//   as a categorical set and FAILED: green↔yellow is ΔE 3.6 under protanopia and 10.2 with normal
//   vision. So `[✓]`/`[ ]`/`[!]` and a word carry the state; the colour only agrees with them.
// · The chart is ONE series in ONE hue, no legend (the title names it), no gridlines, no axes,
//   two direct labels. A second series here would need a categorical palette this one cannot pass.

// 'posada' and 'chess' left with the 2026-08-27 split, and `/api/stats/timeline/` 400s on a
// module it does not know — which is why this list is validated against, not trusted.
const MODULOS = ['books', 'movies', 'music'];

export function montar() {
  if (!location.pathname.startsWith('/panel')) return;
  document.body.dataset.superficie = 'panel';
  // `cargarDatos()` and its four blocks — prestige, habits, achievements, the session log —
  // stood here until the 2026-08-27 split. All four read `/api/panel/`, which was entirely
  // Posada and left with it. The series below is books, movies and music, and it stays.
  // Deep-link: el módulo sale de la URL si viene, y si no del primero. Se valida contra la
  // lista antes de usarlo — la URL es de quien la escribe, y el endpoint 400ea lo desconocido.
  const pedido = new URLSearchParams(location.search).get('modulo');
  const inicial = MODULOS.includes(pedido) ? pedido : MODULOS[0];
  montarModulos(inicial);
  cargarSerie(inicial);
}

function montarModulos(inicial) {
  const fila = document.getElementById('p-modulos');
  if (!fila) return;
  for (const modulo of MODULOS) {
    const boton = document.createElement('button');
    boton.type = 'button';
    boton.textContent = modulo;
    boton.setAttribute('aria-pressed', String(modulo === inicial));
    boton.addEventListener('click', () => {
      for (const otro of fila.children) otro.setAttribute('aria-pressed', 'false');
      boton.setAttribute('aria-pressed', 'true');
      // La URL refleja el estado: recargar, o volver al enlace, muestra el mismo módulo.
      // `replaceState` y no `pushState` — cambiar de pestaña no es navegar hacia atrás.
      const u = new URL(location.href);
      u.searchParams.set('modulo', modulo);
      history.replaceState(null, '', u);
      cargarSerie(modulo);
    });
    fila.append(boton);
  }
}

async function cargarSerie(modulo) {
  const destino = document.getElementById('p-serie');
  if (!destino) return;
  // The override exists for this block too, and for the same reason: its `rechazado` state has
  // no other trigger, because the chips only ever offer the five modules the endpoint accepts.
  const url = override('serie') || `/api/stats/timeline/?module=${modulo}&period=monthly`;
  const datos = await pedir(url, destino, {
    // An all-zero series is not "no answer", it is the answer "nothing happened" — and a chart
    // of twelve zero-height bars reads as a rendering bug. Empty by SUM, not by length.
    vacio: (d) => !d || !d.series || d.series.reduce((t, p) => t + p.count, 0) === 0,
  });
  // Only on success. Clearing unconditionally after the await ERASED the message `pintar` had
  // just written, so `vacio` and `rechazado` rendered as an empty box with a coloured border —
  // the hard criterion ("every failure path has a visible state") failing in the one place it
  // was supposed to hold. Found by reading `textContent`, which was empty while `data-estado`
  // said `rechazado`: the attribute was right and the screen was blank.
  if (!datos) return;
  destino.innerHTML = '';
  destino.append(barras(datos.series, modulo), lectura());
}

/** Twelve monthly counts as a bare bar strip: one hue, one baseline, two direct labels. */
function barras(serie, modulo) {
  const NS = 'http://www.w3.org/2000/svg';
  const W = 320, H = 96, BASE = H - 16, TECHO = 18, HUECO = 3;
  const ancho = (W - HUECO * (serie.length - 1)) / serie.length;
  const tope = Math.max(...serie.map((p) => p.count));
  const iMax = serie.findIndex((p) => p.count === tope);

  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label',
    `${modulo}, ${serie.length} meses. Máximo ${tope} en ${serie[iMax].period}. ` +
    `Último ${serie[serie.length - 1].count} en ${serie[serie.length - 1].period}.`);

  const base = document.createElementNS(NS, 'line');
  base.setAttribute('x1', 0); base.setAttribute('x2', W);
  base.setAttribute('y1', BASE); base.setAttribute('y2', BASE);
  base.setAttribute('class', 'p-base');
  svg.append(base);

  serie.forEach((punto, i) => {
    const x = i * (ancho + HUECO);
    // A zero month paints NOTHING. A 2px stub is a mark where there is no data, and at this
    // size it is indistinguishable from a real count of one — measured: nine of these twelve
    // months are zero and every one of them was drawing a 3px bar.
    const alto = punto.count === 0 ? 0 : Math.max(2, ((BASE - TECHO) * punto.count) / tope);
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'p-barra');
    g.setAttribute('tabindex', '0');
    // Tap, not hover: this is a phone. `<title>` also gives the screen reader the same fact.
    const titulo = document.createElementNS(NS, 'title');
    titulo.textContent = `${punto.period}: ${punto.count}`;
    // The hit target is the whole COLUMN, not the mark. Measured before this existed: a bar for
    // a count of 1 was 30×4 px and a zero month was 30×3 — untappable, and the zero months are
    // exactly the ones you want to ask about. Transparent, full height, painted first so the
    // visible bar sits on top of it.
    const blanco = document.createElementNS(NS, 'rect');
    blanco.setAttribute('x', x - HUECO / 2);
    blanco.setAttribute('y', 0);
    blanco.setAttribute('width', ancho + HUECO);
    blanco.setAttribute('height', BASE);
    blanco.setAttribute('class', 'p-blanco');
    g.append(titulo, blanco);
    if (alto > 0) {
      const r = Math.min(4, ancho / 2, alto);
      const d = document.createElementNS(NS, 'path');
      d.setAttribute('d', `M${x},${BASE} V${BASE - alto + r} q0,${-r} ${r},${-r} ` +
                          `h${ancho - 2 * r} q${r},0 ${r},${r} V${BASE} Z`);
      g.append(d);
    }
    const mostrar = () => { lecturaTexto(`${punto.period} · ${punto.count}`); };
    g.addEventListener('click', mostrar);
    g.addEventListener('focus', mostrar);
    svg.append(g);

    // Selective direct labels: the peak and the latest. A number on every bar is noise.
    if (punto.count > 0 && (i === iMax || i === serie.length - 1)) {
      const t = document.createElementNS(NS, 'text');
      t.setAttribute('x', x + ancho / 2);
      t.setAttribute('y', BASE - alto - 4);
      t.setAttribute('class', 'p-etiqueta');
      t.textContent = punto.count;
      svg.append(t);
    }
  });

  const eje = document.createElementNS(NS, 'text');
  eje.setAttribute('x', 0); eje.setAttribute('y', H - 3);
  eje.setAttribute('class', 'p-etiqueta');
  eje.textContent = `${serie[0].period} → ${serie[serie.length - 1].period}`;
  svg.append(eje);
  return svg;
}

function lectura() {
  const p = document.createElement('p');
  p.id = 'p-lectura';
  p.className = 'p-meta';
  p.setAttribute('aria-live', 'polite');
  p.textContent = 'Toca una barra para su mes.';
  return p;
}

function lecturaTexto(texto) {
  const p = document.getElementById('p-lectura');
  if (p) p.textContent = texto;
}

/** A per-block URL override, so a state can be forced without rebuilding the bundle.
 *
 * ONE parameter per block — `?datos=` and `?serie=` — and not one shared `?fuente=`. Shared, both
 * blocks claimed it: pointing it at the timeline's 400 put the PRESTIGE block into `rechazado`
 * too, which makes it impossible to tell which block is being tested. Measured, not predicted.
 *
 * Confined to `/api/…` on this origin. A query parameter that reaches `fetch` verbatim is a trust
 * boundary: `?datos=https://…` would make the panel call out to whatever a link says and paint
 * the answer.
 */
function override(bloque) {
  const valor = new URLSearchParams(location.search).get(bloque);
  return valor && valor.startsWith('/api/') ? valor : null;
}
