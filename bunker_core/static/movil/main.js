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

window.Cola = Cola;
window.App = App;
window.Panel = Panel;

Panel.montar();
