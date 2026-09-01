// La cifra dominante del panel: el recuento del mes en curso y su delta contra el anterior.
//
// Existe porque el foco de esta pantalla ERA el prestigio y se fue con la Posada el 2026-08-27,
// dejando `.p-cifra` y `.p-delta` en app.html sin un solo consumidor durante cuatro dias. Al
// devolverle el foco al panel el 2026-08-31, las ramas del signo y el caso de una sola serie son
// lo unico que no es obvio de un vistazo — y el signo NO puede vivir solo en el color (regla de
// app.html: el validador de `dataviz` reprobo la paleta categorica). Aqui se comprueba que el
// texto lo lleva.
//
// Corre en el HOST: panel.js solo importa './estado.js', que no toca el DOM al cargarse.
// Run: node tests/test_cifra.js        (ver cli/doctor.py)
import assert from 'node:assert';

// El minimo que `cifra()` toca, y nada mas: un stub de mas convierte un fallo real en un fallo
// del stub. `dataset` es un objeto plano porque es lo que el navegador expone.
const nodo = () => ({
  className: '', textContent: '', dataset: {}, hijos: [],
  append(...n) { this.hijos.push(...n); },
});
globalThis.document = { createElement: nodo };

const { cifra } = await import('../bunker_core/static/movil/panel.js');

const serie = (...cuentas) => cuentas.map((count, i) => ({
  period: `2026-${String(i + 1).padStart(2, '0')}`, count, amount: 0,
}));

let fallos = 0;
function caso(nombre, fn) {
  try { fn(); console.log(`  ok   ${nombre}`); }
  catch (e) { console.log(`  FALLA ${nombre}: ${e.message}`); fallos++; }
}

caso('la cifra es el ULTIMO periodo, no el maximo ni la suma', () => {
  const c = cifra(serie(9, 9, 4));
  assert.strictEqual(c.hijos[0].className, 'p-cifra');
  assert.strictEqual(c.hijos[0].textContent, 4);
});

caso('sube: signo en el TEXTO ademas del color', () => {
  const d = cifra(serie(7, 12)).hijos[1];
  assert.strictEqual(d.dataset.signo, 'sube');
  assert.match(d.textContent, /^\+5 vs /, `texto sin '+5': ${d.textContent}`);
});

caso('baja: el menos lo pone el propio numero', () => {
  const d = cifra(serie(12, 7)).hijos[1];
  assert.strictEqual(d.dataset.signo, 'baja');
  assert.match(d.textContent, /^-5 vs /, `texto sin '-5': ${d.textContent}`);
});

caso('igual: ni "+0" ni "-0", y su propio signo', () => {
  const d = cifra(serie(7, 7)).hijos[1];
  assert.strictEqual(d.dataset.signo, 'igual');
  assert.match(d.textContent, /^0 vs /, `texto raro: ${d.textContent}`);
});

caso('el mes previo va en palabras, y sin off-by-one', () => {
  // '2026-01' es ENERO. Es el caso que importa: `new Date(anno, m, 1)` sin el `- 1` daria
  // 'febrero', y con cualquier otro mes el error pasaria por un nombre plausible.
  // Sale de `Intl`, que no lee el reloj: formatea el periodo que le dan.
  assert.match(cifra(serie(1, 2)).hijos[1].textContent, /enero$/);
});

caso('una serie de UN periodo no inventa delta', () => {
  const c = cifra(serie(3));
  assert.strictEqual(c.hijos.length, 1, 'no debe haber .p-delta con un solo periodo');
});

console.log(fallos === 0 ? `\ntest_cifra: 6 casos · 0 fallos` : `\ntest_cifra: ${fallos} FALLOS`);
process.exit(fallos === 0 ? 0 : 1);
