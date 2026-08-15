package cl.alonso.bunker

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.os.Environment
import android.provider.MediaStore
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

data class Despacho(
    val id: String,
    val verbo: String,
    val payload: String,
    val creado: Long,
    val error: String?,
)

/**
 * The queue. This is the only class in the project whose bugs lose something that cannot be
 * recovered: a dispatch deleted without the server acknowledging it is a capture that never
 * happened, and nothing anywhere else will notice.
 *
 * SQLite through the platform API rather than Room: this is one table with five columns and no
 * relations, and a migration framework for it would be more code than the table.
 */
class ColaStore(private val context: Context) {

    private val helper = object : SQLiteOpenHelper(context, "cola.db", null, 1) {
        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL(
                """CREATE TABLE despachos (
                     id TEXT PRIMARY KEY, verbo TEXT NOT NULL, payload TEXT NOT NULL,
                     creado INTEGER NOT NULL, error TEXT
                   )"""
            )
        }
        // A no-op is correct at version 1 and a trap at version 2: `items()` reads columns with
        // getColumnIndexOrThrow, so shipping a schema change without a migration here makes the
        // WHOLE queue unreadable, not just the new column. Policy: any bump to the version above
        // must add its ALTER TABLE here. Room is still not worth it; this comment is.
        override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) = Unit
    }

    /**
     * Returns the new queue length. Throws if the write failed — see the class contract.
     *
     * `insertOrThrow` and not `insert`: the latter reports failure by returning -1, which a
     * caller can ignore by accident, and the caller's whole job here is to keep the capture
     * sheet open when the write does not land. There is deliberately no `== -1L` check below —
     * `insertOrThrow` never returns it, and a branch that cannot run reads as a fallback that
     * does not exist.
     */
    fun encolar(verbo: String, payload: String): Int {
        // The pair `queue.js` guards and this port had dropped: `Transmisor.vaciar` DELETES a
        // dispatch whose verb has no route, on the reasoning that it can never be accepted. That
        // reasoning only holds if an unknown verb could never be enqueued in the first place —
        // otherwise a typo at a call site is a capture the UI accepts, shows as pending, and
        // then deletes on the next flush with nothing reported anywhere. Refused here, loudly,
        // for the same reason `insertOrThrow` throws: the sheet must stay open.
        //
        // The direction of this dependency is backwards on paper — storage naming transport —
        // but the guard has to sit where every caller routes through, and that is here.
        require(verbo in Transmisor.RUTAS) { "verbo desconocido: $verbo" }
        val valores = ContentValues().apply {
            put("id", UUID.randomUUID().toString())
            put("verbo", verbo)
            put("payload", payload)
            put("creado", System.currentTimeMillis())
        }
        helper.writableDatabase.insertOrThrow("despachos", null, valores)
        respaldar()
        return pendientes()
    }

    fun items(): List<Despacho> {
        val salida = mutableListOf<Despacho>()
        helper.readableDatabase.query(
            // rowid breaks the tie: `creado` is currentTimeMillis(), two taps land in the same
            // millisecond, and SQLite's order for equal keys is unspecified. Flush order is not
            // cosmetic — two `paginas` captures sent out of order leave the stored position at
            // the LOWER page, and the next capture counts the gap twice.
            "despachos", null, null, null, null, null, "creado ASC, rowid ASC"
        ).use { c ->
            while (c.moveToNext()) {
                salida.add(
                    Despacho(
                        id = c.getString(c.getColumnIndexOrThrow("id")),
                        verbo = c.getString(c.getColumnIndexOrThrow("verbo")),
                        payload = c.getString(c.getColumnIndexOrThrow("payload")),
                        creado = c.getLong(c.getColumnIndexOrThrow("creado")),
                        error = c.getString(c.getColumnIndexOrThrow("error")),
                    )
                )
            }
        }
        return salida
    }

    fun pendientes(): Int = items().size

    fun marcarError(id: String, motivo: String) {
        helper.writableDatabase.update(
            "despachos", ContentValues().apply { put("error", motivo) },
            "id = ?", arrayOf(id)
        )
    }

    fun descartar(id: String) {
        helper.writableDatabase.delete("despachos", "id = ?", arrayOf(id))
        respaldar()
    }

    /**
     * Mirrors the queue into Documents/ through MediaStore, which needs no permission on API 29+
     * and outlives an uninstall — unlike Android/data/<pkg>/files/, which is deleted with the app
     * and would therefore fail in the one case this exists for.
     *
     * Returns false rather than throwing: a backup that cannot be written must never cost a
     * capture. The queue is the source of truth; this is a copy.
     */
    /**
     * The queue as the JSON the backup file holds. Split out from `respaldar` because it is the
     * half that can be wrong by logic — a dropped field, a payload double-encoded — while the
     * other half is one platform call. Robolectric's ContentResolver accepts a MediaStore write
     * and then cannot find it again by DISPLAY_NAME, so the round trip is not checkable off the
     * device; this is, exactly.
     */
    fun serializar(): String = JSONArray().apply {
        items().forEach {
            put(JSONObject().apply {
                put("id", it.id); put("verbo", it.verbo)
                put("payload", JSONObject(it.payload)); put("creado", it.creado)
            })
        }
    }.toString()

    // Block body, not `= try {...}`: this function returns early twice (from inside the
    // `use` lambda, and on a null `insert`), and Kotlin forbids `return` in an expression body.
    //
    // ponytail: the MediaStore round trip is verified by hand on the phone, not by a check —
    // Robolectric cannot query back what it accepted. Upgrade path is an instrumented test,
    // which this plan's constraints rule out. Verify it once Task 10 makes a capture reachable.
    fun respaldar(): Boolean {
      return try {
        val json = serializar()

        val resolver = context.contentResolver
        val uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        val donde = "${MediaStore.MediaColumns.DISPLAY_NAME} = ?"
        resolver.query(uri, arrayOf(MediaStore.MediaColumns._ID), donde,
            arrayOf(NOMBRE_RESPALDO), null).use { c ->
            if (c != null && c.moveToFirst()) {
                val existente = ContentUris.withAppendedId(uri, c.getLong(0))
                resolver.openOutputStream(existente, "wt")!!.use { it.write(json.toByteArray()) }
                return true
            }
        }
        val nuevo = resolver.insert(uri, ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, NOMBRE_RESPALDO)
            put(MediaStore.MediaColumns.MIME_TYPE, "application/json")
            put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOCUMENTS)
        }) ?: return false
        resolver.openOutputStream(nuevo)!!.use { it.write(json.toByteArray()) }
        true
      } catch (e: Exception) {
        false
      }
    }

    fun leerRespaldo(): String = try {
        val resolver = context.contentResolver
        val uri = MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        resolver.query(uri, arrayOf(MediaStore.MediaColumns._ID),
            "${MediaStore.MediaColumns.DISPLAY_NAME} = ?", arrayOf(NOMBRE_RESPALDO), null)
            .use { c ->
                if (c != null && c.moveToFirst()) {
                    val f = ContentUris.withAppendedId(uri, c.getLong(0))
                    resolver.openInputStream(f)!!.bufferedReader().readText()
                } else ""
            }
    } catch (e: Exception) {
        ""
    }

    companion object {
        const val NOMBRE_RESPALDO = "bunker-cola.json"
    }
}
