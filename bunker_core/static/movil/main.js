// The app bundle's entry point.
//
// Everything the page reaches for by name is attached here and nowhere else, so there is ONE
// list of what is global and why. `window.CSRF_TOKEN` is not in it: the template sets that in
// an inline script above this one, because it is the only value Django has to inject.
//
// The two `window.*` assignments below are not decoration. The inline script at the bottom of
// app.html reads `window.Bunker` (the APK bridge) to decide about the service worker, and
// queue.js binds that same bridge at load — so the bundle must run BEFORE that inline script,
// which is why the tag order in app.html is not free to change.
import * as Cola from './queue.js';
import * as App from './app.js';
import * as Panel from './panel.js';
import { token, guardarToken, cuandoFalteToken } from './estado.js';

window.Cola = Cola;
window.App = App;
window.Panel = Panel;

// El token, antes de montar: sin él las tres salidas HTTP responden 403 en cuanto la Tarea 5
// encienda el middleware, y el dueño vería tres bloques rotos sin saber por qué.
//
// PERO NO DENTRO DEL APK. Con el puente nativo presente, el JS no hace UNA SOLA petición:
// `queue.js:67` delega las capturas en `PUENTE.encolar` y las vacía WorkManager en nativo, y
// `app.js:cargarEstado` sale por la rama del puente ANTES de su `fetch`. El APK lleva su token
// en BuildConfig (Tarea 4), no en localStorage. Sin esta guarda, el diálogo taparía la pantalla
// de captura en cada arranque pidiendo un token que esa WebView no usa jamás.
const enElApk = typeof window !== 'undefined' && !!window.Bunker;
const hoja = enElApk ? null : document.getElementById('pedir-token');
if (hoja) {
  const abrir = () => { if (!hoja.open) hoja.showModal(); };
  cuandoFalteToken(abrir);
  document.getElementById('tk-guardar')?.addEventListener('click', () => {
    const v = document.getElementById('tk-valor').value.trim();
    if (!v) return;
    if (!guardarToken(v)) {
      // Recargar aquí perdería el token que acaba de teclear y volvería a preguntar, sin decir
      // por qué. Se le dice, y se deja el diálogo abierto.
      const aviso = hoja.querySelector('p');
      if (aviso) aviso.textContent = 'Este navegador no deja guardar (¿modo privado?). '
                                   + 'El token no sobreviviría a la recarga.';
      return;
    }
    location.reload();  // lo más simple que rehace las tres peticiones con el token puesto
  });
  document.getElementById('tk-cerrar')?.addEventListener('click', () => hoja.close());
  if (!token()) abrir();
}

Panel.montar();
