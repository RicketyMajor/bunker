package cl.alonso.bunker

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.net.Uri
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

    // The same file AssetStore writes to, and for the same reason: it is what survives the
    // process being killed between a capture and the flush.
    private val prefs = context.getSharedPreferences("transmisor", Context.MODE_PRIVATE)

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

    /**
     * Mirrors the queue into Documents/ through MediaStore, which needs no permission on API 29+.
     *
     * The KDoc here used to add "and outlives an uninstall", which was the whole reason this
     * exists. **The file does; the app's access to it does not** — measured on the phone
     * 2026-08-17. See `crearRespaldo`. What this buys today is a copy readable by the user and by
     * other apps, and one that survives clearing the app's data. It does not buy a restore, and
     * nothing calls `leerRespaldo()`.
     *
     * Returns false rather than throwing: a backup that cannot be written must never cost a
     * capture. The queue is the source of truth; this is a copy.
     */
    fun respaldar(): Boolean = try {
        val guardado = prefs.getString(URI_RESPALDO, null)
        val destino = guardado?.let { Uri.parse(it) } ?: crearRespaldo()
        // "wt" truncates and "w" does not, and the queue SHRINKS on every successful flush:
        // writing a shorter JSON over a longer one without truncating leaves the tail of the
        // previous one behind — valid bytes, invalid JSON. A file just created is empty, so the
        // create path keeps "w", which is also the only mode this phone has ever exercised: the
        // name probe never matched, so the "wt" branch that lived here never ran on the device.
        val modo = if (guardado != null) "wt" else "w"
        if (destino == null) false
        else {
            context.contentResolver.openOutputStream(destino, modo)!!
                .use { it.write(serializar().toByteArray()) }
            true
        }
    } catch (e: Exception) {
        false
    }

    /**
     * Creates the backup row and remembers its `Uri`, which is what makes the write above
     * repeatable.
     *
     * It was found by `DISPLAY_NAME` until 2026-08-17, and that was the defect. An uninstall
     * clears `owner_package_name`, so the query stops matching a file that is still on disk;
     * `insert` then runs, MediaStore de-duplicates the name to `bunker-cola (1).json` **and
     * stores the suffixed name as the row's `DISPLAY_NAME`** — so the next probe misses again,
     * and every capture inserts one more file, for ever. Measured on the phone: `(1)` … `(5)`.
     *
     * This bounds that at one file per install. It does **not** make the backup readable after a
     * reinstall — the prefs are cleared with the app, so the remembered `Uri` goes with them.
     * That half is SAF (`ACTION_OPEN_DOCUMENT`) and a design decision; see `state-of-the-project`.
     *
     * ponytail: a `Uri` that goes stale — the user deletes the file from Documents/ — silently
     * stops backing up for ever. Deliberately not retried: a retry that re-inserts turns a full
     * disk into the very unbounded growth this replaced. Upgrade the day something actually reads
     * the backup, because today nothing calls `leerRespaldo()`.
     */
    private fun crearRespaldo(): Uri? {
        val nuevo = context.contentResolver.insert(
            MediaStore.Files.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
            ContentValues().apply {
                put(MediaStore.MediaColumns.DISPLAY_NAME, NOMBRE_RESPALDO)
                put(MediaStore.MediaColumns.MIME_TYPE, "application/json")
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOCUMENTS)
            }
        ) ?: return null
        prefs.edit().putString(URI_RESPALDO, nuevo.toString()).apply()
        return nuevo
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

        /**
         * Where the backup's `Uri` is remembered. The name is NOT enough to find the row again —
         * that is the 2026-08-17 defect, and it is the one thing about this file worth knowing.
         */
        const val URI_RESPALDO = "uri_respaldo"
    }
}
