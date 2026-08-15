"""Standalone check for the endpoint that files a Deep Work session after the fact.

Run: docker compose exec -T web python test_session_record.py

The assertion that matters is the third: a session pays prestige and loot, it is transmitted by
a background worker with nobody watching, and a retry after a lost response must not be able to
invent economy. Everything else here is guarding that one.
"""
import os
import uuid
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework.test import APIRequestFactory  # noqa: E402

from posada.models import Adventurer, DeepWorkSession, GuildProfile  # noqa: E402
from posada.views import record_session  # noqa: E402

HOY = timezone.localdate()
f = APIRequestFactory()
fallos = 0


class Rollback(Exception):
    """Sentinel that unwinds `atomic()` once a test has asserted.

    A custom class rather than one of Django's: raising `TransactionManagementError` as a
    rollback signal would swallow a real one raised by the ORM inside the same block, and that
    is precisely the failure a test must not be able to hide.
    """


def _post(payload):
    return record_session(f.post("/", payload, format="json"))


def _despacho(**extra):
    base = {
        "client_uuid": str(uuid.uuid4()),
        "category": "Programación",
        "duration_minutes": 50,
        "survived_seconds": 3000,
        "adventurer_ids": [],
        "surrendered": False,
    }
    base.update(extra)
    return base


def prueba(fn):
    """Runs one test inside a transaction that is always rolled back.

    Any exception is caught, not just AssertionError: a view that starts raising IntegrityError
    would otherwise kill the run on the first test and hide every result after it — which is
    exactly what happened the first time the idempotency guard was removed to see it fail.
    """
    global fallos
    try:
        with transaction.atomic():
            fn()
            raise Rollback
    except Rollback:
        pass
    except AssertionError as exc:
        fallos += 1
        print(f"FALLÓ · {fn.__name__}: {exc}")
    except Exception as exc:
        fallos += 1
        print(f"REVENTÓ · {fn.__name__}: {type(exc).__name__}: {str(exc).splitlines()[0]}")
    return fn


def test_una_sesion_se_archiva_bajo_su_fecha():
    anteayer = HOY - timedelta(days=2)
    antes = DeepWorkSession.objects.count()
    resp = _post(_despacho(occurred_on=anteayer.isoformat()))
    assert resp.status_code == 201, f"esperaba 201, llegó {resp.status_code}: {resp.data}"
    assert DeepWorkSession.objects.count() == antes + 1, "no creó exactamente una fila"

    s = DeepWorkSession.objects.latest("id")
    assert s.completed, "la sesión quedó sin cerrar"
    assert timezone.localdate(s.start_time) == anteayer, (
        f"archivó bajo {timezone.localdate(s.start_time)}, se esperaba {anteayer}")
    assert s.survived_minutes == 50, f"guardó {s.survived_minutes} minutos sobrevividos"
    assert isinstance(resp.data.get("feedback"), str) and resp.data["feedback"].strip(), (
        f"feedback vacío o no textual: {resp.data.get('feedback')!r}")
    print("OK · una sesión se archiva cerrada, bajo occurred_on, con lo sobrevivido")


def test_el_mismo_uuid_dos_veces_crea_una_sola_fila():
    d = _despacho()
    antes = DeepWorkSession.objects.count()
    primera = _post(d)
    segunda = _post(d)
    assert primera.status_code == 201, f"la primera dio {primera.status_code}"
    assert segunda.status_code == 200, f"la repetición dio {segunda.status_code}, no 200"
    assert DeepWorkSession.objects.count() == antes + 1, "la repetición creó otra fila"
    assert segunda.data["feedback"] == primera.data["feedback"], (
        f"la repetición respondió otro hecho: {segunda.data['feedback']!r} "
        f"en vez de {primera.data['feedback']!r}")
    print("OK · el mismo uuid dos veces: una fila, 201 y luego 200, mismo feedback")


def test_una_repeticion_no_paga_dos_veces():
    """The reason client_uuid exists. Without this assertion the decision is unproven."""
    d = _despacho()
    guild, _ = GuildProfile.objects.get_or_create(id=1)
    _post(d)
    guild.refresh_from_db()
    prestigio_tras_una, monedas_tras_una = guild.prestige, guild.sueldo

    for _ in range(3):
        _post(d)
    guild.refresh_from_db()

    assert guild.prestige == prestigio_tras_una, (
        f"el prestigio se movió de {prestigio_tras_una} a {guild.prestige} en la repetición")
    assert guild.sueldo == monedas_tras_una, (
        f"el botín se movió de {monedas_tras_una} a {guild.sueldo} en la repetición")
    print("OK · tres repeticiones no mueven ni prestigio ni botín")


def test_fuera_de_rango_es_400_y_no_escribe():
    antes = DeepWorkSession.objects.count()
    resp = _post(_despacho(duration_minutes=25, survived_seconds=25 * 60 + 1))
    assert resp.status_code == 400, f"sobrevivir de más dio {resp.status_code}"

    for malo, etiqueta in ((0, "duración 0"), (481, "duración 481")):
        r = _post(_despacho(duration_minutes=malo))
        assert r.status_code == 400, f"{etiqueta} dio {r.status_code}"
    for payload, etiqueta in (({"category": "  "}, "categoría vacía"),
                              ({"client_uuid": ""}, "sin uuid"),
                              ({"client_uuid": "no-soy-un-uuid"}, "uuid basura"),
                              ({"occurred_on": "ayer"}, "fecha basura"),
                              ({"survived_seconds": "mucho"}, "segundos no numéricos")):
        r = _post(_despacho(**payload))
        assert r.status_code == 400, f"{etiqueta} dio {r.status_code}"

    assert DeepWorkSession.objects.count() == antes, "alguna rama rechazada escribió igual"
    print("OK · ocho entradas inválidas son 400 y ninguna deja rastro")


def test_un_aventurero_que_ya_no_existe_no_bloquea_la_sesion():
    # `race` is required and has no default — verified against the model, not assumed. The
    # three non-nullable fields without defaults are name, adv_class and race.
    vivo = Adventurer.objects.create(name="Aventurero de prueba", adv_class="CLR",
                                     race="HUM", level=1, max_hp=30, current_hp=30)
    fantasma = vivo.id + 10_000
    resp = _post(_despacho(adventurer_ids=[vivo.id, fantasma]))
    assert resp.status_code == 201, f"llegó {resp.status_code}: {resp.data}"
    s = DeepWorkSession.objects.latest("id")
    assert list(s.adventurers_involved.values_list("id", flat=True)) == [vivo.id], (
        "no resolvió exactamente los aventureros que existen")
    assert "1" in resp.data["message"], (
        f"no avisó del aventurero ausente: {resp.data['message']!r}")
    print("OK · un id fantasma se ignora, se reporta, y la sesión se archiva igual")


if __name__ == "__main__":
    PRUEBAS = [
        test_una_sesion_se_archiva_bajo_su_fecha,
        test_el_mismo_uuid_dos_veces_crea_una_sola_fila,
        test_una_repeticion_no_paga_dos_veces,
        test_fuera_de_rango_es_400_y_no_escribe,
        test_un_aventurero_que_ya_no_existe_no_bloquea_la_sesion,
    ]
    for p in PRUEBAS:
        prueba(p)
    print(f"\ntest_session_record: {len(PRUEBAS) - fallos}/{len(PRUEBAS)}")
    raise SystemExit(1 if fallos else 0)
