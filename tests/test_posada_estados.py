"""Two guards over the Posada engine's status vocabulary. Runs inside the container:

    docker compose exec -T web python -m tests.test_posada_estados

Guard 1 is a static AST contract: every status written must be read, and every status read
must be written, PER CONTAINER. Guard 2 is a runtime anti-no-op harness over the 132 skills.

This file exists because `bunker doctor` was green for months over six dead mechanics.
`test_posada_skills` runs every skill and asserts it neither raises nor returns the wrong
type — all of which is true of a function that does nothing.
"""
import ast
import os
import pathlib

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from posada.engine.estados import AVENTURERO, MONSTRUO

_checks = 0


def check(condicion, etiqueta):
    global _checks
    _checks += 1
    assert condicion, f"FALLÓ: {etiqueta}"
    print(f"  ok  {etiqueta}")


def test_vocabulario_es_coherente():
    """The vocabulary declares every code the engine and the models already use."""
    from posada.engine.estados import (
        ESTADOS, CODIGOS_AVENTURERO, CODIGOS_MONSTRUO, es_preexistente)
    from posada.models import OnHitEffect

    # Every OnHitEffect that lands in a status tracker must be declared. NON is the
    # sentinel, LFS heals and THN retaliates: all three are inline branches, never stored.
    for codigo in OnHitEffect.values:
        if codigo in INLINE:
            continue
        check(codigo in ESTADOS,
              f"OnHitEffect.{codigo} está declarado en estados.py")

    check(CODIGOS_AVENTURERO <= set(ESTADOS),
          "todo código de aventurero está en ESTADOS")
    check(CODIGOS_MONSTRUO <= set(ESTADOS),
          "todo código de monstruo está en ESTADOS")
    check(all(e.contenedor for e in ESTADOS.values()),
          "ningún estado se declara sin contenedor")
    check(all(es_preexistente(c) for c in ESTADOS),
          "la Fase 1 no introduce ningún estado nuevo")



# ---------------------------------------------------------------------------
# Guard 1: the static AST contract.
# ---------------------------------------------------------------------------
# Statuses are reached through FIVE forms, and a contract that knows fewer invents
# defects where there are none and hides the ones there are. Measured, not assumed:
#
#   ctx.adv_status_tracker[x]        the engine, adventurer container
#   context['adv_status'][x]         the skills, THE SAME adventurer container
#   adv_status[x] / status_list      the skills again, after a local rebind
#   m['status'] / target_m['status'] the monster container
#   .add(eff_m) with eff_m a VARIABLE, never a literal
#
# The last one is why STN and BLN look unwritten: `on_hit_effect` is a database
# column, so `combat.py:145` and `combat.py:313` write whatever the row holds. A
# literals-only sweep misses those four writes and then reports PSN, BLD and BRN
# as orphan readers — four defects hidden, five invented.
INLINE = {'NON', 'LFS', 'THN'}

_NOMBRES_AVENTURERO = ('adv_status', 'adv_status_tracker', 'status_list')
_NOMBRES_MONSTRUO = ('m', 'target_m', 'f_mon')


def _literal(nodo):
    return nodo.value if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str) else None


def _contenedor_de(nodo):
    """Return 'aventurero' | 'monstruo' | None for the object being subscripted.

    Reads EVERY literal key on the way down the subscript chain, not only the base name.
    `context['adv_status'][caster.id]` is the adventurer container and unwrapping it to
    `context` loses exactly that — which is how the sweep behind this plan's parent design
    reported RAGING dead when it works (`skills.py:131`).
    """
    claves = []
    base = nodo
    while isinstance(base, ast.Subscript):
        clave = _literal(base.slice)
        if clave:
            claves.append(clave)
        base = base.value
    if isinstance(base, ast.Attribute):
        claves.append(base.attr)
    elif isinstance(base, ast.Name):
        claves.append(base.id)
    for clave in claves:
        if clave in _NOMBRES_AVENTURERO:
            return AVENTURERO
        if clave in _NOMBRES_MONSTRUO:
            return MONSTRUO
    return None


def _fuente_de(valor):
    """The single name a value can be an ALIAS of, following only the value spine.

    Taking every `ast.Name` in the right-hand side instead leaks: measured on `combat.py`,
    `m_raw_roll`, `is_hit`, `crit_msg`, `fail_msg` and `a_raw_roll` all inherited
    {BLN, DODGING, RECKLESS} through `adv_on_attack`. Nothing writes those names today, so
    no phantom write existed — but the instrument was one `.add(is_hit)` away from
    certifying a dead mechanic as repaired, which is the exact failure it was built to stop.
    """
    n = valor
    while True:
        if isinstance(n, ast.Subscript):
            n = n.value
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ('get', 'pop')):
            n = n.func.value
        elif isinstance(n, (ast.ListComp, ast.SetComp, ast.GeneratorExp)) and n.generators:
            n = n.generators[0].iter
        else:
            break
    return n.id if isinstance(n, ast.Name) else None


def _cadenas(nodo):
    return {n.value for n in ast.walk(nodo)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _vocabularios(arbol, conocidos, almacenables):
    """Map each local name to the status codes it can hold.

    `eff_m = getattr(base_m, 'on_hit_effect', 'NON')` can hold any storable OnHitEffect;
    `bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]` can hold only
    those three. Both vocabularies are declared in the source, just not at the call site.

    ponytail: names are merged per FILE, not per function. Harmless here — `eff`, `s`,
    `cured` and `status_list` mean the same thing in every function that binds them. If two
    functions in one file ever bind the same name to different status codes, scope this to
    the enclosing ast.FunctionDef.
    """
    directo, depende = {}, {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign):
            objetivos, valor = nodo.targets, nodo.value
        elif isinstance(nodo, (ast.For, ast.comprehension)):
            objetivos, valor = [nodo.target], nodo.iter
        else:
            continue
        cadenas = _cadenas(valor)
        codigos = set(almacenables) if 'on_hit_effect' in cadenas else set()
        codigos |= cadenas & conocidos
        fuente = _fuente_de(valor)
        for objetivo in objetivos:
            if isinstance(objetivo, ast.Name):
                directo.setdefault(objetivo.id, set()).update(codigos)
                if fuente:
                    depende.setdefault(objetivo.id, set()).add(fuente)
    for _ in range(len(directo) + 1):          # fixpoint; `for s in bad_status` needs one hop
        cambio = False
        for nombre, fuentes in depende.items():
            for fuente in fuentes:
                nuevos = directo.get(fuente, set()) - directo.get(nombre, set())
                if nuevos:
                    directo.setdefault(nombre, set()).update(nuevos)
                    cambio = True
        if not cambio:
            break
    return directo


def _codigos_del_argumento(nodo, vocabularios):
    codigo = _literal(nodo)
    if codigo:
        return {codigo}
    if isinstance(nodo, ast.Name):
        return set(vocabularios.get(nodo.id, set()))
    return set()


def escritores_y_lectores():
    """Cross-reference every status write against every status read, per container.

    Reads the SOURCE, not the runtime: a mechanic no test ever exercises still has its
    writer and its reader here, which is exactly the class of defect this catches.
    """
    from posada.engine.estados import ESTADOS
    from posada.models import OnHitEffect

    almacenables = frozenset(OnHitEffect.values) - INLINE
    conocidos = set(ESTADOS) | almacenables
    escriben = {AVENTURERO: set(), MONSTRUO: set()}
    leen = {AVENTURERO: set(), MONSTRUO: set()}
    raiz = pathlib.Path(__file__).resolve().parent.parent / 'posada'

    for archivo in sorted(raiz.rglob('*.py')):
        if 'migrations' in archivo.parts:
            continue
        arbol = ast.parse(archivo.read_text(encoding='utf-8', errors='ignore'))
        vocabularios = _vocabularios(arbol, conocidos, almacenables)
        for nodo in ast.walk(arbol):
            # --- writes: <contenedor>[x].add('CODIGO') / .remove(...) / .discard(...)
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr in ('add', 'remove', 'discard') and nodo.args):
                cont = _contenedor_de(nodo.func.value)
                codigos = _codigos_del_argumento(nodo.args[0], vocabularios)
                if cont and codigos:
                    # A cleanse is a READ, never a write. Counting `remove`/`discard` on the
                    # write side lets a status stay "produced" purely because something
                    # deletes it: drop `combat.py:148` and PSN/BLD/BRN would still register
                    # as written, from the five cure loops in `skills.py` alone — every DoT
                    # unapplicable and all three guards green. That is the failure this file
                    # exists to stop, so only `add` produces.
                    if nodo.func.attr == 'add':
                        escriben[cont] |= codigos
                    else:
                        leen[cont] |= codigos
            # --- reads: 'CODIGO' in <contenedor>[x]
            if isinstance(nodo, ast.Compare) and len(nodo.ops) == 1 and isinstance(
                    nodo.ops[0], (ast.In, ast.NotIn)):
                # Symmetric with the write side on purpose: `any(s in status_list ...)`
                # at `skills.py:230` and four siblings read through a variable, and a
                # literals-only reader would report those statuses as written-but-unread.
                codigos = _codigos_del_argumento(nodo.left, vocabularios)
                cont = _contenedor_de(nodo.comparators[0])
                if cont and codigos:
                    leen[cont] |= codigos
    return escriben, leen


def test_ningun_nombre_fuera_del_vocabulario():
    """Every name the engine actually uses is declared. Catches STUNNED / BLINDED."""
    from posada.engine.estados import ESTADOS
    escriben, leen = escritores_y_lectores()
    for cont in (AVENTURERO, MONSTRUO):
        for codigo in sorted(escriben[cont] | leen[cont]):
            check(codigo in ESTADOS,
                  f"'{codigo}' (usado en '{cont}') está declarado en estados.py")


def test_cada_codigo_se_usa_en_su_contenedor():
    """`contenedor` was declared per status in Task 1 and nothing enforced it.

    Without this, `m['status'].add('RAGING')` plus one monster-side reader passes all three
    guards while `estados.py` declares RAGING adventurer-only — the "per container" promise
    in its docstring had no test behind it.
    """
    from posada.engine.estados import ESTADOS
    escriben, leen = escritores_y_lectores()
    for cont in (AVENTURERO, MONSTRUO):
        for codigo in sorted(escriben[cont] | leen[cont]):
            estado = ESTADOS.get(codigo)
            if not estado:
                continue
            check(cont in estado.contenedor,
                  f"'{codigo}' se usa en '{cont}', y estados.py lo declara para ese contenedor")


def test_ningun_estado_escrito_sin_leer():
    """A status written and never read is a mechanic that silently does nothing."""
    from posada.engine.estados import ESTADOS
    escriben, leen = escritores_y_lectores()
    for cont in (AVENTURERO, MONSTRUO):
        for codigo in sorted(escriben[cont]):
            if codigo not in ESTADOS:
                continue  # Task 3 makes undeclared names impossible; not this check's job.
            check(codigo in leen[cont],
                  f"{codigo} se escribe en '{cont}' y ALGUIEN lo lee")


def test_ningun_lector_huerfano():
    """A status read and never written is a branch that can never be taken."""
    from posada.engine.estados import ESTADOS
    escriben, leen = escritores_y_lectores()
    for cont in (AVENTURERO, MONSTRUO):
        for codigo in sorted(leen[cont]):
            if codigo not in ESTADOS:
                continue
            check(codigo in escriben[cont],
                  f"{codigo} se lee en '{cont}' y ALGUIEN lo escribe")



# ---------------------------------------------------------------------------
# Runtime checks: the mechanic OBSERVABLY does something.
# ---------------------------------------------------------------------------
# The static contract proves a writer and a reader agree on a name. It cannot prove the
# branch behind that name changes anything, which is the whole reason `test_posada_skills`
# was green over six dead mechanics: "it did not raise" is also true of a function that
# does nothing.
def test_un_monstruo_aturdido_pierde_el_turno():
    """The observable change, not the absence of a crash: a stunned monster does not attack,
    and the stun is consumed so it does not last for ever."""
    import random
    from posada.engine.context import SessionContext, ScriptList
    from posada.engine.states.combat import _monster_turn

    ctx = SessionContext()
    ctx.script = ScriptList(lambda: "COMBAT")
    ctx.current_second = 60
    monstruo = {'name': 'Maniquí', 'hp': 50, 'max_hp': 50, 'status': {'STN'},
                'stats': {'str': 2, 'dex': 2, 'con': 2}, 'base': None}

    random.seed(1)
    # Sin aventureros. Ojo: esto NO es una red de seguridad — si el stun no cortara el
    # turno, `_monster_turn` saldría limpio en `if not valid_targets: return` sin reventar.
    # Lo que prueba la regresión es el mensaje, y la inversión se vio fallar por su nombre.
    _monster_turn(ctx, monstruo, [])

    mensajes = " ".join(e.get("message", "") for e in ctx.script)
    check("aturdido" in mensajes, "el monstruo aturdido anuncia que pierde el turno")
    check('STN' not in monstruo['status'], "el aturdimiento se consume en un turno")



def test_temerario_concede_ventaja_de_verdad():
    """RECKLESS must reach roll_d20(advantage=True). Asserting the set contains the string
    proves only that a string was added — that is the no-op this whole spec exists for."""
    import random
    from posada.engine.context import SessionContext, ScriptList
    from posada.engine.states.combat import _basic_attack

    class Adv:
        id = 1; name = "Bárbaro"; adv_class = "BBN"; level = 1; max_hp = 100
        def get_stat_modifiers(self):
            return {'str': 0, 'dex': 0, 'con': 0, 'armor': 0, 'damage': 0,
                    'on_hit_effect': 'NON', 'effect_chance': 0,
                    'weapon_dice_sides': 4, 'weapon_dice_count': 1}

    def golpes(estados):
        # dex 20 y armor 20 dan evasión 28: un d20 pelado casi nunca acierta, así que la
        # ventaja es MEDIBLE. Un maniquí al que se le pega siempre no puede mostrar la
        # diferencia — los handoffs 021 y 022 perdieron una sesión cada uno con un check
        # apuntado donde el defecto no podía aparecer.
        ctx = SessionContext()
        ctx.current_second = 60
        adv = Adv()
        ctx.temp_hp = {1: 100}
        ctx.adv_status_tracker = {1: set(estados)}
        ctx.active_monsters_group = [{'name': 'Maniquí', 'hp': 10_000, 'max_hp': 10_000,
                                      'status': set(),
                                      'stats': {'str': 0, 'dex': 20, 'con': 0, 'armor': 20}}]
        aciertos = 0
        for semilla in range(200):
            random.seed(semilla)
            ctx.script = ScriptList(lambda: "COMBAT")
            _basic_attack(ctx, adv, adv.get_stat_modifiers(), [adv])
            aciertos += sum(1 for e in ctx.script if "asesta" in e.get("message", ""))
        return aciertos

    sin, con = golpes(set()), golpes({'RECKLESS'})
    check(con > sin,
          f"RECKLESS sube los aciertos contra una evasión alta ({sin} → {con})")



def test_un_aventurero_aturdido_pierde_el_turno():
    """No attack event, no skill event, and the stun consumed. Asserting only that nothing
    raised would pass against the broken version, which is the whole point."""
    import random
    from posada.engine.context import SessionContext, ScriptList
    from posada.engine.states.combat import _adventurer_turn

    # El doble NO declara `current_hp` a propósito: sin él la evaluación de habilidades
    # falla y el turno cae a BASIC_ATTACK de forma determinista, que es justo la conducta
    # contra la que hay que asertar. Dárselo dejaría que una skill dispare en su lugar y
    # "asesta" podría no aparecer — la inversión pasaría en verde sin reparar nada.
    class Adv:
        id = 1; name = "Aturdido"; adv_class = "FTR"; level = 1; max_hp = 100
        class_resources = {}
        def get_stat_modifiers(self):
            return {'str': 5, 'dex': 5, 'con': 0, 'armor': 0, 'damage': 5,
                    'on_hit_effect': 'NON', 'effect_chance': 0,
                    'weapon_dice_sides': 6, 'weapon_dice_count': 1}

    ctx = SessionContext()
    ctx.script = ScriptList(lambda: "COMBAT")
    ctx.current_second = 60
    adv = Adv()
    # temp_hp al máximo a propósito: por debajo del 30 % el turno entra en la auto-poción,
    # que consulta InventorySlot y reventaría contra este aventurero de mentira.
    ctx.temp_hp = {1: 100}
    ctx.adv_status_tracker = {1: {'STN'}}
    ctx.combat_skills_tracker = {1: set()}
    ctx.active_monsters_group = [{'name': 'Maniquí', 'hp': 100, 'max_hp': 100, 'status': set(),
                                  'stats': {'str': 0, 'dex': 0, 'con': 0, 'armor': 0}}]

    random.seed(7)
    _adventurer_turn(ctx, adv, [adv])

    mensajes = " ".join(e.get("message", "") for e in ctx.script)
    check("aturdido" in mensajes, "el aventurero aturdido anuncia que pierde el turno")
    check("asesta" not in mensajes, "el aventurero aturdido NO ataca")
    check(ctx.active_monsters_group[0]['hp'] == 100, "el monstruo no recibe daño del aturdido")
    check('STN' not in ctx.adv_status_tracker[1], "el aturdimiento se consume en un turno")



# ---------------------------------------------------------------------------
# Guard 2: the runtime anti-no-op harness.
# ---------------------------------------------------------------------------
# The static contract proves a name is read somewhere. It CANNOT prove the read does
# anything, and it cannot see reachability at all. This plants each skill's precondition
# and demands an observable change.
class _Aventurero:
    """Same shape as MockAdventurer in test_posada_skills.py, plus the two things that file
    forgot: `base_luk` (read by the loot path) and a real `adv_class` taken from the skill's
    own allowed_classes — with no 'FGT' fallback, because 'FGT' is not a class."""

    def __init__(self, id_, nombre, adv_class, level=10):
        self.id = id_
        self.name = nombre
        self.adv_class = adv_class
        self.level = level
        self.max_hp = 100
        self.current_hp = 100
        self.base_luk = 10
        self.class_resources = {}

    def get_stat_modifiers(self):
        return {'str': 3, 'dex': 3, 'con': 3, 'int': 3, 'wis': 3, 'cha': 3,
                'armor': 0, 'damage': 0, 'on_hit_effect': 'NON', 'effect_chance': 0,
                'weapon_dice_sides': 6, 'weapon_dice_count': 1}


def _montar_contexto(datos):
    """Build one skill's context. The caster's class comes from the skill itself, so every
    skill is evaluated by someone who can actually cast it."""
    adv_class = datos['allowed_classes'][0]
    caster = _Aventurero(1, "Lanzador", adv_class)
    aliados = [_Aventurero(2, "Aliado1", "CLR"),
               _Aventurero(3, "Aliado2", "ROG"),
               _Aventurero(4, "Aliado3", "WIZ")]
    enemigos = [{'id': 100 + i, 'name': f"Maniquí {i}", 'hp': 200, 'max_hp': 200,
                 'status': set(),
                 'stats': {'str': 12, 'dex': 12, 'con': 12, 'int': 12, 'wis': 12,
                           'cha': 12, 'armor': 14}}
                for i in range(2)]
    contexto = {
        'caster': caster,
        'allies': [caster] + aliados,   # el caster va en su propio grupo: sin eso un
        'enemies': enemigos,            # auto-buff parece un no-op
        'adv_status': {a.id: set() for a in [caster] + aliados},
        'log': [],
        'current_second': 10,
        'eval_mode': True,
        'session_duration': 7200,
        'base_gold': 500,
    }
    return caster, aliados, enemigos, contexto


# Skills gate in BOTH directions on HP, so no single value can fire them all: 16 score only
# when the party is under 20-40 % (`indomable` needs <= 0.2), while `ataque_temerario` scores
# its high branch only above 50 %. A harness with one HP level reports one of those groups as
# dead — measured: half HP silenced exactly 16 skills, every one of them gated below it.
# So each skill is tried at every level and is only "muda" if none of them fires it.
_VIDAS = (0.1, 0.5, 1.0)


# The same shape as _VIDAS, for the other axis the SESSION context moves along.
# `_montar_contexto` fixed `current_second` at 10 against a `session_duration` of 7200, so a
# skill scoring only in the session's second half reads as dead at every HP level. The loot
# family is gated exactly that way, so one value would report six skills unreachable right
# after they were fixed. Early, middle and late, because a skill may gate in either direction.
_SEGUNDOS = (10, 3600, 7000)


def _precondicion(contexto, caster, aliados, fraccion):
    """Plant what a skill needs in order to be able to do anything at all.

    A harness that cannot fire a skill's trigger reports the skill as dead, and is
    indistinguishable from one that found a real defect. That already happened: six
    cleansing skills were reported never-eligible by a pass that never planted a status.

    Deliberately over-inclusive — plant everything on everyone. A skill that ignores what
    it does not need loses nothing; a skill whose trigger we forgot is reported as a no-op
    and gets read by a human, which is the correct failure.
    """
    for aliado in aliados:
        contexto['adv_status'][aliado.id] |= {'PSN', 'BRN', 'BLD'}
    caster.class_resources = {'mana': 99, 'ki': 99, 'furia': 99,
                              'stamina': 99, 'sanacion': 99}
    for adv in [caster] + aliados:
        adv.current_hp = max(1, int(adv.max_hp * fraccion))


def _instantanea(contexto, caster, aliados, enemigos):
    """Everything a skill could legitimately move. Equality of two snapshots is the
    definition of "did nothing" — the thing `test_posada_skills` cannot see."""
    return (
        tuple(a.current_hp for a in [caster] + aliados),
        tuple(sorted(caster.class_resources.items())),
        tuple(e['hp'] for e in enemigos),
        tuple(frozenset(e['status']) for e in enemigos),
        tuple(frozenset(contexto['adv_status'][a.id]) for a in [caster] + aliados),
        len(contexto['log']),
    )


def test_ninguna_skill_es_un_no_op():
    """Every skill must produce an OBSERVABLE change when its precondition holds.

    `test_posada_skills` asserts each skill neither raises nor returns the wrong type — all
    of which is true of `return True` and nothing else. This asserts the change.
    """
    import random
    from posada.skills import SkillRegistry

    skills = SkillRegistry.get_all_skills()
    inertes, sin_disparar, reventaron = [], [], []

    for skill_id, datos in sorted(skills.items()):
        disparo = False
        # Both axes, not just HP: the loot family scores only in the session's second half and
        # `_montar_contexto` pins `current_second` at 10, so sweeping _VIDAS alone reported six
        # skills muted right after they were fixed. See _SEGUNDOS.
        for fraccion, segundo in [(f, sg) for f in _VIDAS for sg in _SEGUNDOS]:
            caster, aliados, enemigos, contexto = _montar_contexto(datos)
            _precondicion(contexto, caster, aliados, fraccion)
            contexto['current_second'] = segundo

            antes = _instantanea(contexto, caster, aliados, enemigos)
            try:
                contexto['eval_mode'] = True
                random.seed(11)
                if not datos['execute'](contexto):
                    continue
                disparo = True
                contexto['eval_mode'] = False
                random.seed(11)
                datos['execute'](contexto)
            except Exception as exc:
                # Recogido, no tragado: una skill que revienta con la precondición puesta es
                # un hallazgo, y abortar aquí escondería a las 131 restantes.
                reventaron.append(f"{skill_id} @{fraccion}/{segundo}s: {type(exc).__name__} {exc}")
                disparo = True
                break
            if _instantanea(contexto, caster, aliados, enemigos) != antes:
                break
            inertes.append(skill_id)
            break
        if not disparo:
            sin_disparar.append(skill_id)

    check(not reventaron,
          f"ninguna skill revienta con su precondición plantada; revientan: {reventaron}")
    check(not sin_disparar,
          f"toda skill puntúa >0 con su precondición plantada; mudas: {sin_disparar}")
    check(not inertes,
          f"toda skill cambia algo observable al ejecutarse; inertes: {inertes}")
    check(len(skills) == 132, f"el harness recorrió las 132 skills, no {len(skills)}")



# Los dos despachadores arrancan en `best_score = 50` y seleccionan con `score > best_score`
# (`exploring.py:256`, `combat.py:224`), así que una skill que nunca supera 50 no puede ser
# elegida jamás y su cuerpo entero es código muerto.
#
# Empty since 2026-08-22. It held 18 ids from 2026-08-21, frozen rather than fixed because
# changing an eval score changes skill selection, which is balance work. They were fixed in
# four families: five recategorised to COMBAT, five heals to 65, six loot skills to
# 50 + req_level gated on the session's second half, two combat basics to 55.
# The guard below still earns its place: it fails on any NEW unreachable skill, and it fails
# equally if a name is added here without being unreachable.
_INALCANZABLES_CONOCIDAS = set()


_UMBRAL_DESPACHADOR = 50


def test_ninguna_skill_nueva_es_inalcanzable():
    """A skill that cannot out-score the dispatcher's threshold is dead code, however
    correct its body is.

    This is what the static contract and the no-op harness both miss: `infusiones_basicas`
    writes INFUSED_WEAPON, the contract counts the write and goes green, and the harness
    fires the skill by hand with a context the engine never builds. Reachability needs the
    DISPATCHER's context shape — `enemies: []` for SESSION — and its threshold.
    """
    import random
    from posada.skills import SkillRegistry

    inalcanzables = set()
    for skill_id, datos in sorted(SkillRegistry.get_all_skills().items()):
        mejor = 0
        # Both axes. Sweeping _VIDAS alone pins `current_second` at 10 and reports the whole
        # loot family unreachable the moment it is gated on the session's second half.
        for fraccion, segundo in [(f, sg) for f in _VIDAS for sg in _SEGUNDOS]:
            caster, aliados, enemigos, contexto = _montar_contexto(datos)
            _precondicion(contexto, caster, aliados, fraccion)
            if datos['type'] == 'SESSION':
                contexto['enemies'] = []      # la forma real del despachador SESSION
            contexto['current_second'] = segundo
            contexto['eval_mode'] = True
            random.seed(11)
            try:
                puntaje = datos['execute'](contexto)
            except Exception:
                puntaje = 0
            if isinstance(puntaje, bool):
                puntaje = 0
            mejor = max(mejor, puntaje or 0)
        if mejor <= _UMBRAL_DESPACHADOR:
            inalcanzables.add(skill_id)

    nuevas = inalcanzables - _INALCANZABLES_CONOCIDAS
    resueltas = _INALCANZABLES_CONOCIDAS - inalcanzables
    check(not nuevas, f"ninguna skill NUEVA es inalcanzable; nuevas: {sorted(nuevas)}")
    check(not resueltas,
          f"la línea base está al día; ya alcanzables, bórralas de la lista: {sorted(resueltas)}")


def test_ninguna_session_lee_enemies():
    """A skill whose body reads `enemies` cannot be a SESSION skill.

    The SESSION dispatcher always passes `'enemies': []` (`exploring.py:241`), so such a body
    either returns False immediately or picks from an empty list. Registering it SESSION is a
    categorisation error, not a balance one, and no score can repair it. Measured 2026-08-22,
    before the fix, this found exactly five: blindaje_runico, infusiones_basicas,
    presencia_intimidante, senda_furia, zancada_poderosa.
    """
    import inspect
    from posada.skills import SkillRegistry

    malas = []
    for skill_id, datos in sorted(SkillRegistry.get_all_skills().items()):
        if datos['type'] != 'SESSION':
            continue
        try:
            fuente = inspect.getsource(datos['execute'])
        except (OSError, TypeError):
            continue
        if "'enemies'" in fuente or '"enemies"' in fuente:
            malas.append(skill_id)

    check(not malas,
          f"ninguna skill SESSION lee 'enemies' en su cuerpo; las que lo hacen: {malas}")


def test_cada_clase_nivel_1_puede_actuar():
    """A class whose only session skill cannot fire spends the session doing nothing.

    `exploring.py` has no default action — `best_action = None` — unlike combat, which falls back
    to "BASIC_ATTACK". Measured 2026-08-22: ART, CLR, DRD and RGR each had exactly one session
    skill at level 1 and all four were under the floor. Classes with NO session skill at level 1
    (BRD, FTR, ROG, WIZ) are out of scope: nothing is dead, there is simply nothing yet.
    """
    import random
    from posada.skills import SkillRegistry

    todas = SkillRegistry.get_all_skills()
    ses = [d for d in todas.values() if d['type'] == 'SESSION']
    clases = sorted({c for d in todas.values() for c in d['allowed_classes']})

    hambrientas = []
    for clase in clases:
        disponibles = [d for d in ses
                       if clase in d['allowed_classes'] and d['req_level'] <= 1]
        if not disponibles:
            continue                      # nada que desbloquear todavia, no es un defecto
        vivas = []
        for datos in disponibles:
            for fraccion in _VIDAS:
                for segundo in _SEGUNDOS:
                    caster, aliados, enemigos, contexto = _montar_contexto(datos)
                    _precondicion(contexto, caster, aliados, fraccion)
                    contexto['enemies'] = []
                    contexto['current_second'] = segundo
                    contexto['eval_mode'] = True
                    random.seed(11)
                    try:
                        puntaje = datos['execute'](contexto)
                    except Exception:
                        puntaje = 0
                    if isinstance(puntaje, bool):
                        puntaje = 0
                    if (puntaje or 0) > _UMBRAL_DESPACHADOR:
                        vivas.append(datos['id'])
                        break
                else:
                    continue
                break
        if not vivas:
            hambrientas.append((clase, [d['id'] for d in disponibles]))

    check(not hambrientas,
          f"toda clase con una skill SESSION a nivel 1 puede lanzar al menos una; "
          f"sin nada que hacer: {hambrientas}")


def _party_de_sonda(clases, hp):
    """Planted party. The database holds ONE adventurer (a CLR), so a check that runs a
    session against `Adventurer.objects.all()` exercises a single class and reports green
    for the wrong reason. Callers wrap this in a transaction they roll back."""
    from posada.models import Adventurer
    return [Adventurer.objects.create(
        name=f"Sonda{i}", adv_class=c, race='HUM', level=10, max_hp=100, current_hp=hp,
        base_str=14, base_dex=14, base_con=14, base_int=14, base_wis=14, base_cha=14,
        base_luk=10, class_resources={}) for i, c in enumerate(clases)]


def test_la_ventana_de_hp_devuelve_lo_que_pidio_prestado():
    """The whole contract of `hp_vivos`, the window both dispatchers borrow HP through.

    Written this way after the obvious check failed to discriminate: asserting at session level
    that `current_hp` never comes back below where it started stays GREEN with the restore
    ripped out, because the live simulation ends healed anyway. Measured on seed 4242 --
    correct: `{MNK:100, ROG:73, PAL:46, FTR:57}`; leaking: `{MNK:99, ROG:100, PAL:98, FTR:100}`.
    Both satisfy "never below 20". A weak invariant over a real session is worth less than the
    exact contract over a fake one.

    The contract: inside the window a skill reads the live value; on the way out the live dict
    keeps whatever the skill wrote, and `current_hp` gets its own accumulated value plus that
    same delta -- which is what a skill doing `current_hp = min(max_hp, current_hp + heal)`
    produced before the window existed. `sesion.py:91` discards a negative net, so those direct
    writes are the only thing that persists healing; restoring the bare snapshot deletes it.
    """
    from types import SimpleNamespace
    from posada.engine.context import hp_vivos

    adv = SimpleNamespace(id=1, current_hp=50, max_hp=100)
    ctx = SimpleNamespace(temp_hp={1: 20})

    with hp_vivos(ctx, [adv]):
        visto = adv.current_hp
        adv.current_hp += 10          # a skill heals 10, computed off the live value

    check(visto == 20, f"dentro de la ventana la skill lee el valor VIVO; leyo {visto}")
    check(ctx.temp_hp[1] == 30, f"al salir, temp_hp se queda con lo que la skill escribio; "
                                f"es {ctx.temp_hp[1]}")
    check(adv.current_hp == 60, f"y current_hp recupera su propio valor mas el delta (50+10); "
                                f"es {adv.current_hp}")

    # A skill that raises must not leave the mirror behind: both dispatchers catch exceptions
    # around the call, and combat's basic-attack branch leaves through the same `finally`.
    adv2 = SimpleNamespace(id=2, current_hp=50, max_hp=100)
    ctx2 = SimpleNamespace(temp_hp={2: 20})
    try:
        with hp_vivos(ctx2, [adv2]):
            raise RuntimeError("una skill que revienta")
    except RuntimeError:
        pass
    check(adv2.current_hp == 50,
          f"una excepcion dentro de la ventana tampoco deja el espejo puesto; "
          f"quedo en {adv2.current_hp}")


def test_el_despachador_de_sesion_entrega_hp_vivos():
    """A SESSION skill must be chosen on the HP the engine is actually simulating.

    The assertion is on what the dispatcher DID, not on `current_hp` afterwards: the window
    restores it on the way out, so reading the field after the call proves nothing. A CLR at
    level 1 has exactly one SESSION skill, `dominio_divino`, and it is gated on being hurt.
    With the snapshot saying 100/100 it scores at or below the floor and nothing is dispatched;
    with the live value at 20/100 it clears the floor.

    Measured 2026-08-23 across the whole grid: 75 of 130 (class, level) pairs change which
    skill they dispatch once the live value reaches them.
    """
    from types import SimpleNamespace
    from posada.models import Adventurer
    from posada.engine.states.exploring import _session_skill_eval

    adv = Adventurer(id=8001, name="Sonda", adv_class='CLR', race='HUM', level=1,
                     max_hp=100, current_hp=100, base_str=14, base_dex=14, base_con=14,
                     base_int=14, base_wis=14, base_cha=14, base_luk=10,
                     class_resources={'mana': 3})
    ctx = SimpleNamespace(temp_hp={8001: 20},
                          session_skills_tracker={8001: set()},
                          adv_status_tracker={8001: set()},
                          script=[], current_second=2400, total_seconds=3600)

    _session_skill_eval(ctx, [adv])

    check(ctx.session_skills_tracker[8001],
          f"con HP vivos a 20/100 el CLR 1 despacha su unica skill SESSION; "
          f"despachadas: {ctx.session_skills_tracker[8001] or 'ninguna'}")
    check(adv.current_hp >= 100,
          f"y la ventana restaura current_hp al salir; quedo en {adv.current_hp}")


def _recursos_como_el_runner(clase, nivel):
    """Hand-copy of runner.py:43-56.

    ponytail: a hand-copy, because the runner seeds resources inline inside
    `generate_session_script` and there is no helper to call. Ceiling: a class whose seeding
    changes there and not here makes this probe measure a party the engine never builds --
    silent drift, in the one file whose job is catching drift. Upgrade: extract the runner's
    seeding into a function and call it from both, the day a class's resources change.
 `_precondicion` plants every resource at 99, which
    measures POSSIBILITY; this measures the real start of a session."""
    if clase in ['WIZ', 'SOR', 'WLK', 'CLR', 'DRD', 'BRD']:
        return {'mana': nivel * 3}
    if clase == 'PAL':
        return {'mana': nivel * 2, 'sanacion': nivel * 5}
    if clase == 'MNK':
        return {'ki': nivel * 2}
    if clase == 'BBN':
        return {'furia': 2 + nivel // 3}
    return {'stamina': nivel * 2}


def _pares_sin_despacho(hp_vivo, segundos=(1200, 2400, 3400)):
    """Drive the real dispatcher once per (class, level) and collect the pairs it leaves idle.

    Goes through `_session_skill_eval` rather than scoring skills by hand, because the thing
    under test is the dispatcher, not the skills. `current_hp` is the session-start snapshot at
    full health; `hp_vivo` is what the engine is simulating.

    Seconds are swept and not pinned: six SESSION skills gate on
    `current_second <= session_duration / 2`, so a single 1800 against a 3600-second session
    sits exactly on the excluded side of that boundary and reports 84 dry pairs where 1801
    reports 43.
    """
    from types import SimpleNamespace
    from posada.models import Adventurer, AdventurerClass
    from posada.engine.states.exploring import _session_skill_eval

    secos = []
    for clase in AdventurerClass.values:
        for nivel in range(1, 11):
            advs = [Adventurer(id=8100 + i, name=f"S{i}", adv_class=c, race='HUM',
                               level=nivel, max_hp=100, current_hp=100, base_str=14,
                               base_dex=14, base_con=14, base_int=14, base_wis=14,
                               base_cha=14, base_luk=10,
                               class_resources=_recursos_como_el_runner(c, nivel))
                    for i, c in enumerate([clase, 'FTR', 'CLR'])]
            ctx = SimpleNamespace(
                temp_hp={a.id: hp_vivo for a in advs},
                session_skills_tracker={a.id: set() for a in advs},
                adv_status_tracker={a.id: set() for a in advs},
                script=[], current_second=0, total_seconds=3600)
            for seg in segundos:
                ctx.current_second = seg
                _session_skill_eval(ctx, advs)
            if not ctx.session_skills_tracker[advs[0].id]:
                secos.append(f"{clase}{nivel}")
    return secos


def test_un_grupo_herido_despierta_las_skills_condicionadas_a_hp():
    """The harm this fix removes, measured through the dispatcher itself.

    A party is wounded by combat, which lives in `ctx.temp_hp`; `current_hp` stays at the
    session-start snapshot and only ever goes UP, because heals write it and damage does not.
    So the 68 skills conditioning on `caster.current_hp` are progressively silenced over a
    session and never re-armed. Measured 2026-08-23 over the whole grid, live value at 20/100
    against a snapshot of 100/100:

        without the dispatch window:  43 of 130 pairs dispatch NOTHING
        with it:                       6 of 130

    Both numbers measured by running this same function against the tree with and without
    `hp_vivos`, not derived.

    The threshold is 12 because the remaining pairs are a balance question, not a dispatch one:
    they have no SESSION skill that can clear the floor at any HP. That list is Alonso's.
    """
    secos = _pares_sin_despacho(hp_vivo=20)
    check(len(secos) <= 12,
          f"con el grupo herido, 12 pares (clase, nivel) o menos se quedan sin despachar; "
          f"son {len(secos)}: {' '.join(secos)}")


if __name__ == '__main__':
    test_vocabulario_es_coherente()
    test_ningun_nombre_fuera_del_vocabulario()
    test_cada_codigo_se_usa_en_su_contenedor()
    test_ningun_estado_escrito_sin_leer()
    test_ningun_lector_huerfano()
    test_un_monstruo_aturdido_pierde_el_turno()
    test_temerario_concede_ventaja_de_verdad()
    test_un_aventurero_aturdido_pierde_el_turno()
    test_ninguna_skill_es_un_no_op()
    test_ninguna_session_lee_enemies()
    test_cada_clase_nivel_1_puede_actuar()
    test_ninguna_skill_nueva_es_inalcanzable()
    test_la_ventana_de_hp_devuelve_lo_que_pidio_prestado()
    test_el_despachador_de_sesion_entrega_hp_vivos()
    test_un_grupo_herido_despierta_las_skills_condicionadas_a_hp()
    print(f"\n{_checks} comprobaciones OK.")
