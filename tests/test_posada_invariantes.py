"""Data invariants for the Posada: what the database itself refuses. Runs inside the container:

    docker compose exec -T web python -m tests.test_posada_invariantes

Every probe plants a violation against the REAL database inside a savepoint that is always
rolled back, so this check leaves no row behind. A probe reports the exception class and the
constraint name, never a bare True/False: a write refused by the WRONG constraint is a
different fact from a write refused by the right one, and a boolean cannot tell them apart.

Phase 2 of `context/specs/posada-robusta.md`. Until its migrations land, EVERY probe here is
expected to fail with `fue ACEPTADA` — that red is the deliverable, not a defect.
"""
import logging
import os

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from django.db import connection, transaction  # noqa: E402

from posada.models import Adventurer, GuildProfile, InventorySlot, Item  # noqa: E402

fallos = []
comprobaciones = 0


class _Deshacer(Exception):
    """Raised to force a nested atomic() to roll back a plant the database ACCEPTED."""


def plantar(descripcion, fn):
    """Run `fn` in a nested atomic that is ALWAYS rolled back. Return the exception or None.

    MEASURED TWICE, both times against the running container, because the obvious version of
    this function is wrong in two different ways:

    1. Outside an atomic block Django runs in autocommit, where `transaction.savepoint()` is a
       NO-OP returning None. `savepoint_rollback(None)` then rolls back nothing and every
       planted row SURVIVES in the live database. Hence the guard below.
    2. A hand-rolled `savepoint()` / `savepoint_rollback()` pair CANNOT recover from a plant
       the database refused. When a statement fails inside a transaction Django sets
       `needs_rollback = True`, and from that moment every query raises
       `TransactionManagementError` — including `savepoint_rollback` itself. The first probe to
       be refused would take the whole check down with it, and the traceback blames the
       constraint rather than this function.

    A nested `transaction.atomic()` is the version that works: on exception it rolls back to
    its savepoint AND clears `needs_rollback`, so the next probe still runs. `_Deshacer` is how
    the accepted case takes the same exit — an accepted plant must be undone too.
    """
    if not connection.in_atomic_block:
        raise RuntimeError(
            "plantar() fuera de transaction.atomic(): el savepoint seria un no-op y las filas "
            "plantadas quedarian en la base VIVA.")
    try:
        with transaction.atomic():
            fn()
            raise _Deshacer
    except _Deshacer:
        return None
    except Exception as exc:
        return exc


def exige_rechazo(descripcion, fn, nombre_constraint):
    """Assert the plant is refused AND that the refusal names the expected constraint."""
    global comprobaciones
    comprobaciones += 1
    exc = plantar(descripcion, fn)
    if exc is None:
        fallos.append(f"FALLO: {descripcion} fue ACEPTADA; esperaba rechazo de {nombre_constraint}")
        return
    if nombre_constraint not in str(exc):
        fallos.append(
            f"FALLO: {descripcion} fue rechazada por el constraint EQUIVOCADO.\n"
            f"       esperaba: {nombre_constraint}\n"
            f"       recibio : {exc.__class__.__name__}: {exc}")


def _un_aventurero():
    adv = Adventurer.objects.first()
    if adv is None:
        raise RuntimeError("PRECONDICION ROTA: no hay ningun Adventurer. "
                           "Este check no puede plantar nada y su verde no significa nada.")
    return adv


def _un_item():
    item = Item.objects.first()
    if item is None:
        raise RuntimeError("PRECONDICION ROTA: no hay ningun Item en el catalogo.")
    return item


def diagnostico():
    """Dump what this instrument can see, BEFORE any assertion runs.

    Phase 1's rule, earned three times in one session: a guard that is green has not been
    tested by the fact that it is green. These numbers are what makes a later green readable.
    Read the `InventorySlot` line especially: at 0 rows, every cross-table statement this file
    could make is vacuously true.
    """
    adv = Adventurer.objects.first()
    print("== lo que este instrumento tiene delante ==")
    print(f"  GuildProfile   : {GuildProfile.objects.count()} filas, "
          f"ids={list(GuildProfile.objects.values_list('id', flat=True))}")
    print(f"  Adventurer     : {Adventurer.objects.count()} filas")
    print(f"  InventorySlot  : {InventorySlot.objects.count()} filas")
    print(f"  Item           : {Item.objects.count()} filas")
    if adv:
        equipados = [f.name for f in adv._meta.fields
                     if f.name.startswith('equip_') and getattr(adv, f.name + '_id')]
        print(f"  aventurero de prueba: {adv.name} hp={adv.current_hp}/{adv.max_hp} "
              f"equipado={equipados or 'NADA'} slots={adv.inventory.count()}")
    print()


def probar_invariantes():
    """Six impossible states. Each must be refused by a constraint that names itself."""
    adv = _un_aventurero()
    item = _un_item()

    exige_rechazo(
        "un segundo GuildProfile",
        lambda: GuildProfile.objects.create(prestige=0, prestige_level=1),
        "guildprofile_singleton")

    exige_rechazo(
        "un aventurero con HP negativo",
        lambda: Adventurer.objects.filter(id=adv.id).update(current_hp=-1),
        "adventurer_hp_no_negativo")

    exige_rechazo(
        "un aventurero con HP por encima del maximo",
        lambda: Adventurer.objects.filter(id=adv.id).update(current_hp=adv.max_hp + 1),
        "adventurer_hp_bajo_maximo")

    exige_rechazo(
        "un slot de inventario con cantidad cero",
        lambda: InventorySlot.objects.create(adventurer=adv, item=item, quantity=0),
        "inventoryslot_cantidad_positiva")

    exige_rechazo(
        "un slot de inventario sin dueno",
        lambda: InventorySlot.objects.create(adventurer=None, guild=None, item=item, quantity=1),
        "inventoryslot_un_solo_dueno")

    exige_rechazo(
        "un slot de inventario con dos duenos",
        lambda: InventorySlot.objects.create(
            adventurer=adv, guild=GuildProfile.objects.get(id=1), item=item, quantity=1),
        "inventoryslot_un_solo_dueno")


def probar_unequip_atomico():
    """Drive `unequip_item` with the delivery FORCED to fail, and demand the item survive.

    An earlier version of this probe read `inspect.getsource(views.unequip_item)` and grepped it
    for `transaction.atomic`. It was measuring DRF: `@api_view` replaces the function, so
    `getsource` returns Django's `View.as_view()` inner `view` — nine lines of framework that
    have never contained the word `transaction`. The probe reported red for the whole session
    for a reason unrelated to `unequip_item`, and would have reported red just the same after
    the fix. A source grep cannot see behaviour; this drives it instead.
    """
    global comprobaciones
    comprobaciones += 1

    from django.test import Client

    import posada.engine as _engine
    from posada.models import Adventurer, Item, InventorySlot

    adv = _un_aventurero()
    arma = Item.objects.filter(item_type='W1H').first()
    if arma is None:
        fallos.append("FALLO: precondicion — no hay ningun item W1H con que equipar al aventurero")
        return

    original = _engine.add_item_to_inventory

    def _entrega_que_revienta(*a, **kw):
        raise RuntimeError("entrega forzada a fallar")

    # The forced failure makes the view answer 400, and Django's request logger prints
    # `Bad Request: ...` to stderr. That line is this probe working, but it reads like a
    # broken check sitting right above `8 comprobaciones OK`. Silence it for the one call.
    logging.getLogger('django.request').setLevel(logging.CRITICAL)
    try:
        with transaction.atomic():
            Adventurer.objects.filter(id=adv.id).update(equip_main_hand=arma)
            _engine.add_item_to_inventory = _entrega_que_revienta
            Client().post(f'/posada/api/adventurer/{adv.id}/unequip/',
                          {'slot_type': 'equip_main_hand'}, content_type='application/json')
            sigue_equipada = Adventurer.objects.get(id=adv.id).equip_main_hand_id
            en_mochila = InventorySlot.objects.filter(adventurer=adv, item=arma).exists()
            if sigue_equipada != arma.id and not en_mochila:
                fallos.append(
                    "FALLO: unequip_item DESTRUYO el objeto — la entrega fallo y el arma no quedo "
                    "ni equipada ni en la mochila; falta la transaccion que ate las dos mitades")
            raise _Deshacer
    except _Deshacer:
        pass
    finally:
        _engine.add_item_to_inventory = original
        logging.getLogger('django.request').setLevel(logging.NOTSET)


def probar_atomicidad():
    """The pay/deliver pair must be refused outside a transaction, at the choke point.

    MUST run OUTSIDE transaction.atomic() — what it proves is that `pay_with_change` refuses to
    be called there. That is the exact opposite of `probar_invariantes`'s requirement, which is
    why the two live in separate scopes in `__main__`.
    """
    global comprobaciones
    from posada.engine.legacy import pay_with_change

    comprobaciones += 1
    if connection.in_atomic_block:
        # A precondition is an assumption: inside a transaction this probe CANNOT fail, and its
        # green would mean nothing. Phase 1 shipped 16 skills reported as silent that were the
        # harness's own HP value.
        fallos.append("FALLO: la precondicion de esta prueba no se cumple — ya estamos dentro de "
                      "una transaccion, asi que no puede comprobar que pay_with_change la exija")
        return
    from posada.engine.legacy import can_afford

    adv = _un_aventurero()
    item = _un_item()
    # HAZARD, and it is not hypothetical: this call runs OUTSIDE a transaction by design, so if
    # the guard is absent (today) or removed (the Task 5 inversion) `pay_with_change` reaches
    # `adv.save()` and the debit COMMITS against the live adventurer. Refuse to run against an
    # adventurer who could actually pay. Today he holds 0 of every currency, which is luck, not
    # a property — so it gets checked every run.
    if can_afford(adv, item):
        fallos.append(
            f"FALLO: precondicion insegura — {adv.name} PUEDE pagar {item.name}, y esta prueba "
            f"corre fuera de transaccion: le cobraria de verdad. Elige un item mas caro.")
        return
    try:
        pay_with_change(adv, item)
        fallos.append("FALLO: pay_with_change acepto cobrar FUERA de una transaccion")
    except RuntimeError as exc:
        if 'transaction.atomic' not in str(exc):
            fallos.append(f"FALLO: pay_with_change se nego por otra razon: {exc}")


if __name__ == '__main__':
    diagnostico()
    # `probar_invariantes` MUST run inside a transaction (savepoints are a no-op outside one, and
    # the planted rows would survive). `probar_atomicidad` MUST run outside one, because what it
    # proves is that `pay_with_change` refuses to be called there. Opposites: separate scopes.
    with transaction.atomic():
        probar_invariantes()
    probar_unequip_atomico()
    probar_atomicidad()
    if fallos:
        print(f"\n{len(fallos)} de {comprobaciones} comprobaciones FALLARON:\n")
        for f in fallos:
            print(f"  {f}\n")
        raise SystemExit(1)
    print(f"{comprobaciones} comprobaciones OK")
