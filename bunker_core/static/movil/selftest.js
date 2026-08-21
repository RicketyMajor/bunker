// A SECOND entry point, and it exists because one bundle could not serve both pages.
//
// /movil/selftest/ is a bare page with none of the app's markup. Importing app.js there
// registers its `DOMContentLoaded` handler, which calls `$('#ft-buscar').addEventListener(...)`
// on eight elements that do not exist — it throws on the first one — and then fires
// `cargarEstado()`, a network request that pollutes the very queue the check is measuring.
// Measured before it was written: app.js:626 is the handler, and selftest.html has no `#ft-*`.
//
// So the check gets the queue and nothing else, which is also exactly what it used to load.
import * as Cola from './queue.js';

window.Cola = Cola;
