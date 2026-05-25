# posada/skills.py
import random


class SkillRegistry:
    """Orquestador central para las habilidades de los aventureros."""
    _registry = {}

    @classmethod
    def register(cls, skill_id, name, skill_type, req_level, allowed_classes):
        def decorator(func):
            cls._registry[skill_id] = {
                "id": skill_id,
                "name": name,
                "type": skill_type,
                "req_level": req_level,
                "allowed_classes": allowed_classes,
                "execute": func
            }
            return func
        return decorator

    @classmethod
    def get_skill(cls, skill_id):
        return cls._registry.get(skill_id)

    @classmethod
    def get_all_skills(cls):
        return cls._registry

# ==========================================
# GRIMORIO: HABILIDADES MARCIALES Y DIVINAS
# ==========================================

# --- TEMPLATE HABILIDAD BASE ---
# @SkillRegistry.register(
#    skill_id="nombre_unico_sin_espacios",
#    name="Nombre Mostrado en UI",
#    skill_type="COMBAT", # O 'SESSION' o 'PASSIVE'
#    req_level=1,
#    allowed_classes=["WIZ", "SOR"] # Lista de clases permitidas
# )
# def plantilla_habilidad(context):
#    caster = context['caster']
#
#    # 1. IA DE UTILIDAD Y VERIFICACIÓN DE RECURSOS
#    if context.get('eval_mode'):
#        # Verifica si tiene la energía necesaria (mana, ki, furia, stamina, sanacion)
#        if caster.class_resources.get('mana', 0) < 1:
#            return 0
#
#       # Puntuación de utilidad (0 a 100). Ej: 60 si hay enemigos vivos.
#        return 60 if context['enemies'] else 0
#
#    # 2. CONSUMO DEL RECURSO
#    caster.class_resources['mana'] -= 1
#
#   # 3. EJECUCIÓN (Ejemplo: Dañar a un enemigo)
#    target = random.choice(context['enemies'])
#    target['hp'] -= 10
#
#    # 4. REGISTRO NARRATIVO
#    context['log'].append({"second": context['current_second'], "type": "flavor",
#                           "message": f"✨ {caster.name} lanza [bold yellow]Nombre Habilidad[/bold yellow]!"})
#    return True


@SkillRegistry.register(
    skill_id="curacion_menor", name="Curación Menor", skill_type="COMBAT", req_level=1, allowed_classes=["CLR", "PAL"]
)
def curacion_menor(context):
    caster = context['caster']
    allies = context['allies']

    # COSTO: 1 Maná
    if context.get('eval_mode'):
        if caster.class_resources.get('mana', 0) < 1:
            return 0
        wounded_allies = [a for a in allies if a.current_hp < a.max_hp]
        if not wounded_allies:
            return 0
        target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
        return 40 + min(60, (target.max_hp - target.current_hp) * 5)

    caster.class_resources['mana'] -= 1

    wounded_allies = [a for a in allies if a.current_hp < a.max_hp]
    target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
    heal_amount = random.randint(
        1, 8) + caster.get_stat_modifiers().get('wis', 0)
    target.current_hp = min(target.max_hp, target.current_hp + heal_amount)

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✨ {caster.name} gasta Maná y lanza [bold yellow]Curación Menor[/bold yellow] sobre {target.name} (+{heal_amount} HP)."})
    return True


@SkillRegistry.register(
    skill_id="golpe_brutal", name="Golpe Brutal", skill_type="COMBAT", req_level=1, allowed_classes=["FTR", "BBN"]
)
def golpe_brutal(context):
    caster = context['caster']

    # COSTO: 1 Stamina
    if context.get('eval_mode'):
        if caster.class_resources.get('stamina', 0) < 1 and caster.class_resources.get('furia', 0) < 1:
            return 0
        return 60 if context['enemies'] else 0

    if 'stamina' in caster.class_resources and caster.class_resources['stamina'] > 0:
        caster.class_resources['stamina'] -= 1

    target = random.choice(context['enemies'])
    adv_mods = caster.get_stat_modifiers()
    a_roll = random.randint(1, 20) + adv_mods['str'] - 2
    m_evasion = 10 + target['stats']['dex']

    if a_roll >= m_evasion:
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1
        dmg = sum(random.randint(1, sides) for _ in range(count + 1)
                  ) + adv_mods['damage'] + (adv_mods['str'] * 2)
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"💥 {caster.name} ejecuta un [bold yellow]Golpe Brutal[/bold yellow] aplastando a [bold red]{target['name']}[/bold red] por {dmg} de daño."})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"💨 {caster.name} intenta un [bold yellow]Golpe Brutal[/bold yellow] pero pierde el equilibrio."})
    return True


@SkillRegistry.register(
    skill_id="furia_feroz", name="Furia Feroz", skill_type="SESSION", req_level=1, allowed_classes=["BBN"]
)
def furia_feroz(context):
    caster = context['caster']

    # COSTO: 1 Furia
    if context.get('eval_mode'):
        if caster.class_resources.get('furia', 0) < 1:
            return 0
        return 90 if 'RAGING' not in context['adv_status'][caster.id] else 0

    caster.class_resources['furia'] -= 1
    context['adv_status'][caster.id].add('RAGING')
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💢 ¡{caster.name} gasta su Furia y entra en un [bold red]Trance Feroz[/bold red]!"})
    return True


@SkillRegistry.register(
    skill_id="accion_astuta", name="Acción Astuta", skill_type="COMBAT", req_level=2, allowed_classes=["ROG"]
)
def accion_astuta(context):
    caster = context['caster']

    # COSTO: 1 Stamina
    if context.get('eval_mode'):
        if caster.class_resources.get('stamina', 0) < 1:
            return 0
        if caster.current_hp < (caster.max_hp * 0.6) and 'DODGING' not in context['adv_status'][caster.id]:
            return 80
        return 0

    caster.class_resources['stamina'] -= 1
    context['adv_status'][caster.id].add('DODGING')
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💨 {caster.name} quema Stamina en una [bold blue]Acción Astuta[/bold blue] volviéndose escurridizo."})
    return True


@SkillRegistry.register(
    skill_id="golpe_aturdidor", name="Golpe Aturdidor", skill_type="COMBAT", req_level=5, allowed_classes=["MNK"]
)
def golpe_aturdidor(context):
    caster = context['caster']
    enemies = [m for m in context['enemies'] if 'STUNNED' not in m['status']]

    # COSTO: 1 Ki
    if context.get('eval_mode'):
        if caster.class_resources.get('ki', 0) < 1:
            return 0
        return 75 if enemies else 0

    caster.class_resources['ki'] -= 1
    target = random.choice(enemies)

    from posada.engine import calculate_save_dc, roll_d20
    save_dc = calculate_save_dc(caster)
    m_save = roll_d20() + target['stats']['con']

    if m_save < save_dc:
        target['status'].add('STUNNED')
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"⚡ {caster.name} gasta 1 Ki. ¡[bold red]{target['name']}[/bold red] queda [bold yellow]ATURDIDO[/bold yellow]!"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🛡️ {caster.name} intenta aturdir, pero [bold red]{target['name']}[/bold red] resiste."})
    return True


@SkillRegistry.register(
    skill_id="imposicion_manos", name="Imposición de Manos", skill_type="SESSION", req_level=1, allowed_classes=["PAL"]
)
def imposicion_manos(context):
    caster = context['caster']

    # COSTO: 5 Sanación
    wounded_allies = [a for a in context['allies'] if a.current_hp < a.max_hp]
    if context.get('eval_mode'):
        if caster.class_resources.get('sanacion', 0) < 5:
            return 0
        if not wounded_allies:
            return 0
        target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
        return 50 + min(40, (target.max_hp - target.current_hp) * 4)

    caster.class_resources['sanacion'] -= 5
    target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
    heal = 5
    target.current_hp = min(target.max_hp, target.current_hp + heal)
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✋ {caster.name} drena su energía sagrada para [bold yellow]Imposición de Manos[/bold yellow] sobre {target.name} (+{heal} HP)."})
    return True


@SkillRegistry.register(
    skill_id="castigo_divino", name="Castigo Divino", skill_type="COMBAT", req_level=2, allowed_classes=["PAL"]
)
def castigo_divino(context):
    caster = context['caster']

    # COSTO: 1 Maná
    if context.get('eval_mode'):
        if caster.class_resources.get('mana', 0) < 1:
            return 0
        return 70 if context['enemies'] else 0

    target = random.choice(context['enemies'])
    adv_mods = caster.get_stat_modifiers()
    a_roll = random.randint(1, 20) + max(adv_mods['str'], adv_mods['dex'])
    m_evasion = 10 + target['stats']['dex']

    if a_roll >= m_evasion:
        caster.class_resources['mana'] -= 1  # Solo cobra si acierta
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1
        base_dmg = sum(random.randint(1, sides) for _ in range(
            count)) + adv_mods['damage'] + adv_mods['str']
        smite_dmg = sum(random.randint(1, 8) for _ in range(2))

        target['hp'] -= (base_dmg + smite_dmg)
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"☀️ ¡Gasto de Maná! [bold yellow]Castigo Divino[/bold yellow] de {caster.name} arrasa a [bold red]{target['name']}[/bold red] ({base_dmg + smite_dmg} daño)."})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🛡️ {caster.name} falla el golpe y retiene su Maná."})
        return False
    return True

# ==========================================
# ERUDITOS ARCANOS
# ==========================================


@SkillRegistry.register(
    skill_id="bola_de_fuego", name="Bola de Fuego", skill_type="SESSION", req_level=5, allowed_classes=["WIZ", "SOR"]
)
def bola_de_fuego(context):
    caster = context['caster']

    # COSTO: 3 Maná
    if context.get('eval_mode'):
        if caster.class_resources.get('mana', 0) < 3:
            return 0
        return 85 if len(context['enemies']) > 1 else 20

    caster.class_resources['mana'] -= 3
    from posada.engine import calculate_save_dc, roll_d20

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔥 {caster.name} sacrifica 3 de Maná conjurando [bold red]BOLA DE FUEGO[/bold red]."})

    fire_dmg = sum(random.randint(1, 6) for _ in range(8))
    for target in context['enemies']:
        m_save = roll_d20() + target['stats']['dex']
        dmg_taken = fire_dmg if m_save < calculate_save_dc(
            caster) else fire_dmg // 2
        target['hp'] -= dmg_taken
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> [bold red]{target['name']}[/bold red] recibe {dmg_taken} daño."})
    return True


@SkillRegistry.register(
    skill_id="eldritch_blast", name="Descarga Sobrenatural", skill_type="COMBAT", req_level=1, allowed_classes=["WLK"]
)
def eldritch_blast(context):
    caster = context['caster']

    # COSTO: 0 (Es un Truco Mágico / Cantrip)
    if context.get('eval_mode'):
        return 55 if context['enemies'] else 0

    adv_mods = caster.get_stat_modifiers()
    beams = 2 if caster.level >= 5 else 1

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌌 {caster.name} dispara {beams} rayo(s) de [bold magenta]Eldritch Blast[/bold magenta]."})

    for i in range(beams):
        if not context['enemies']:
            break
        target = random.choice(context['enemies'])
        if (random.randint(1, 20) + adv_mods['cha']) >= (10 + target['stats']['dex']):
            dmg = random.randint(1, 10) + adv_mods['cha']
            target['hp'] -= dmg
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> ¡Impacto en [bold red]{target['name']}[/bold red]! ({dmg} daño)"})
    return True
