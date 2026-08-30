package cl.alonso.bunker

import androidx.test.core.app.ApplicationProvider
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.shadows.ShadowAlarmManager

/**
 * The bridge is the only door between the interface and everything that can lose data, so the
 * rule under test throughout is the same one `ColaStore` and `Transmisor` are held to: a capture
 * the UI has confirmed must be on disk, and a capture that was not stored must never look stored.
 */
@RunWith(RobolectricTestRunner::class)
class PuenteTest {

    private val ctx = ApplicationProvider.getApplicationContext<android.content.Context>()

    private fun store() = ColaStore(ctx)

    // `avisar` is injected for the same reason `Transmisor` injects `poster`: SyncWorker.ahora
    // needs a WorkManager, and pulling in androidx.work:work-testing to observe one call would
    // be a new dependency for a fact a lambda already reports.
    private fun puente(s: ColaStore, avisos: MutableList<Unit> = mutableListOf()) =
        Puente(ctx, s, AssetStore(ctx) { "" }, { avisos.add(Unit) })

    @Test
    fun `encolar guarda y devuelve el total pendiente`() {
        val s = store()
        val p = puente(s)
        assertEquals(1, p.encolar("paginas", """{"pages":12}"""))
        assertEquals(2, p.encolar("paginas", """{"pages":30}"""))
        assertEquals(2, s.pendientes())
    }

    @Test
    fun `encolar pide un vaciado inmediato`() {
        // The reason a capture reaches Django in seconds instead of waiting for the alarm. If
        // this stops happening nothing breaks visibly — captures just get slow — which is
        // exactly the kind of regression that survives for months.
        val avisos = mutableListOf<Unit>()
        val s = store()
        puente(s, avisos).encolar("paginas", """{"pages":12}""")
        assertEquals(1, avisos.size)
    }

    @Test
    fun `un verbo desconocido lanza y NO avisa`() {
        // The exception is deliberately allowed to escape into JS: the sheet must stay open
        // rather than tell the user a capture was saved when it was not. And a flush must not be
        // scheduled for a capture that does not exist.
        val avisos = mutableListOf<Unit>()
        val s = store()
        val e = runCatching { puente(s, avisos).encolar("verbo_inventado", "{}") }.exceptionOrNull()
        assertTrue("debio lanzar, no devolver un total", e != null)
        assertEquals(0, s.pendientes())
        assertEquals("no debio programar un vaciado para nada", 0, avisos.size)
    }

    @Test
    fun `sincronizar pide un vaciado sin tocar la cola`() {
        // The chip tap. It must reach the worker — an inert control on a queue that looks stuck
        // is worse than no control — and it must not invent, drop or reorder anything.
        val avisos = mutableListOf<Unit>()
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        puente(s, avisos).sincronizar()
        assertEquals(1, avisos.size)
        assertEquals(1, s.pendientes())
    }

    @Test
    fun `listar entrega el payload como objeto, no como texto`() {
        // app.js reads `item.payload.pages`. Handing it the raw string would make every field
        // read `undefined` in the Purgatorio, with no error anywhere.
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        val fila = JSONArray(puente(s).listar()).getJSONObject(0)
        assertEquals(12, fila.getJSONObject("payload").getInt("pages"))
        assertEquals("paginas", fila.getString("verbo"))
        assertTrue("falta el id, y DESCARTAR no tiene otro asidero", fila.getString("id").isNotEmpty())
    }

    @Test
    fun `descartar saca exactamente uno`() {
        val s = store()
        s.encolar("paginas", """{"pages":12}""")
        s.encolar("paginas", """{"pages":30}""")
        val p = puente(s)
        p.descartar(JSONArray(p.listar()).getJSONObject(0).getString("id"))
        assertEquals(1, s.pendientes())
        assertEquals(30, JSONArray(p.listar()).getJSONObject(0).getJSONObject("payload").getInt("pages"))
    }

    @Test
    fun `estado es un sobre, y el puente respondiendo no es prueba de enlace`() {
        // The whole reason `estado()` is not a bare payload. The bridge always answers; whether
        // the snapshot inside it is three days old is a separate fact, and only the native side
        // knows it.
        val assets = AssetStore(ctx) { """{"libros":[{"id":1,"title":"Rayuela"}]}""" }
        assertTrue(assets.refrescarEstado())
        val sobre = JSONObject(Puente(ctx, store(), assets) {}.estado())
        assertEquals("Rayuela", sobre.getJSONObject("estado").getJSONArray("libros")
            .getJSONObject(0).getString("title"))
        assertTrue("un refresco exitoso debio dejar constancia", sobre.getBoolean("en_linea"))
        assertTrue("sincronizado debio quedar fechado", sobre.getLong("sincronizado") > 0)
    }

    @Test
    fun `un refresco fallido no borra el sobre pero si baja en_linea`() {
        // The normal condition with the laptop off. The snapshot must survive; the claim of a
        // link must not.
        val ok = AssetStore(ctx) { """{"libros":[{"id":1,"title":"Rayuela"}]}""" }
        assertTrue(ok.refrescarEstado())
        val caido = AssetStore(ctx) { throw java.io.IOException("sin ruta") }
        assertFalse(caido.refrescarEstado())

        val sobre = JSONObject(Puente(ctx, store(), caido) {}.estado())
        assertEquals("el snapshot anterior debio sobrevivir", "Rayuela",
            sobre.getJSONObject("estado").getJSONArray("libros").getJSONObject(0).getString("title"))
        assertFalse("no debio seguir diciendo que hay enlace", sobre.getBoolean("en_linea"))
    }

    @Test
    fun `sin nada cacheado el sobre sigue siendo legible`() {
        // A first launch offline. app.js falls back to `vacio()` here and must not be handed
        // something JSON.parse throws on.
        val sobre = JSONObject(Puente(ctx, store(), AssetStore(ctx) { "" }) {}.estado())
        assertEquals(0, sobre.getJSONObject("estado").length())
        assertEquals(0L, sobre.getLong("sincronizado"))
        assertFalse(sobre.getBoolean("en_linea"))
    }

    @Test
    fun `el sobre dice cuando falta el permiso de alarma exacta`() {
        // `app.js` paints the banner on `alarma_exacta === false` and on nothing else, so the two
        // values this key can take ARE the contract.
        //
        // Driven through the REAL grant check. An earlier draft injected a lambda instead, on the
        // stated grounds that "Robolectric runs at minSdk 29 and the branch is unreachable" —
        // false, and `DespertadorTest` in this same module already disproved it by shadowing this
        // very call. That draft cost a constructor parameter, three rewritten call sites, and a
        // check that only proved a hand-written Boolean survives a trip through JSON.
        ShadowAlarmManager.setCanScheduleExactAlarms(false)
        assertFalse(
            "no aviso que faltaba el permiso",
            JSONObject(puente(store()).estado()).getBoolean("alarma_exacta"),
        )

        ShadowAlarmManager.setCanScheduleExactAlarms(true)
        assertTrue(
            "aviso de un permiso que ya estaba dado",
            JSONObject(puente(store()).estado()).getBoolean("alarma_exacta"),
        )
    }
}
