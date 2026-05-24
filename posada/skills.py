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
# GRIMORIO: HABILIDADES DE PRUEBA (FASE 26)
# ==========================================


@SkillRegistry.register(
    skill_id="curacion_menor",
    name="Curación Menor",
    skill_type="COMBAT",
    req_level=1,
    allowed_classes=["CLR", "PAL"]
)
def curacion_menor(context):
    """Cura a un aliado herido."""
    caster = context['caster']
    allies = context['allies']
    log = context['log']
    current_second = context['current_second']

    # 1. IA DE UTILIDAD: ¿Vale la pena usarlo?
    if context.get('eval_mode'):
        wounded_allies = [a for a in allies if a.current_hp < a.max_hp]
        if not wounded_allies:
            return 0  # Puntuación 0: Inútil si todos tienen la vida al máximo
        target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
        hp_missing = target.max_hp - target.current_hp
        # Mientras más herido esté el aliado, mayor puntuación (Base 40, Máx 100)
        return 40 + min(60, hp_missing * 5)

    # 2. EJECUCIÓN (Si la IA decide que esta es la mejor opción)
    wounded_allies = [a for a in allies if a.current_hp < a.max_hp]
    target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)

    heal_amount = random.randint(
        1, 8) + caster.get_stat_modifiers().get('wis', 0)
    target.current_hp = min(target.max_hp, target.current_hp + heal_amount)

    log.append({"second": current_second, "type": "flavor",
                "message": f"✨ {caster.name} alza su símbolo y lanza [bold yellow]Curación Menor[/bold yellow] sobre {target.name} (+{heal_amount} HP)."})
    return True


@SkillRegistry.register(
    skill_id="golpe_brutal",
    name="Golpe Brutal",
    skill_type="COMBAT",
    req_level=1,
    allowed_classes=["FTR", "BBN"]
)
def golpe_brutal(context):
    """Un ataque devastador pero impreciso."""
    caster = context['caster']
    enemies = context['enemies']
    log = context['log']
    current_second = context['current_second']

    # 1. IA DE UTILIDAD
    if context.get('eval_mode'):
        # Siempre es una opción decente si hay enemigos. Score: 60 (supera al ataque básico que vale 50)
        return 60

    # 2. EJECUCIÓN (Tirada D20 Modificada)
    target = random.choice(enemies)
    adv_mods = caster.get_stat_modifiers()

    # Penalización de -2 por ser un golpe pesado
    a_roll = random.randint(1, 20) + adv_mods['str'] - 2
    m_evasion = 10 + target['stats']['dex']

    if a_roll >= m_evasion:
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1
        # Daño extra: +1 dado y doble bonificador de Fuerza
        dmg = sum(random.randint(1, sides) for _ in range(count + 1)
                  ) + adv_mods['damage'] + (adv_mods['str'] * 2)
        target['hp'] -= dmg
        log.append({"second": current_second, "type": "flavor",
                    "message": f"💥 {caster.name} ejecuta un [bold yellow]Golpe Brutal[/bold yellow] aplastando a [bold red]{target['name']}[/bold red] por {dmg} de daño."})
    else:
        log.append({"second": current_second, "type": "flavor",
                    "message": f"💨 {caster.name} intenta un [bold yellow]Golpe Brutal[/bold yellow] pero pierde el equilibrio y falla contra [bold red]{target['name']}[/bold red]."})
    return True


@SkillRegistry.register(
    skill_id="furia_feroz", name="Furia Feroz", skill_type="SESSION", req_level=1, allowed_classes=["BBN"]
)
def furia_feroz(context):
    caster = context['caster']
    adv_status = context['adv_status']

    # IA: Solo usar si no está ya furioso
    if context.get('eval_mode'):
        return 90 if 'RAGING' not in adv_status[caster.id] else 0

    adv_status[caster.id].add('RAGING')
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💢 ¡{caster.name} entra en [bold red]Furia Feroz[/bold red]! Su piel resiste los impactos."})
    return True


@SkillRegistry.register(
    skill_id="accion_astuta", name="Acción Astuta", skill_type="COMBAT", req_level=2, allowed_classes=["ROG"]
)
def accion_astuta(context):
    caster = context['caster']
    adv_status = context['adv_status']

    # IA: Usar si la salud está por debajo del 60%
    if context.get('eval_mode'):
        if caster.current_hp < (caster.max_hp * 0.6) and 'DODGING' not in adv_status[caster.id]:
            return 80
        return 0

    adv_status[caster.id].add('DODGING')
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💨 {caster.name} usa [bold blue]Acción Astuta[/bold blue] volviéndose increíblemente escurridizo."})
    return True


@SkillRegistry.register(
    skill_id="golpe_aturdidor", name="Golpe Aturdidor", skill_type="COMBAT", req_level=5, allowed_classes=["MNK"]
)
def golpe_aturdidor(context):
    caster = context['caster']
    enemies = [m for m in context['enemies'] if 'STUNNED' not in m['status']]

    # IA: Gran prioridad si hay enemigos que no estén aturdidos
    if context.get('eval_mode'):
        return 75 if enemies else 0

    target = random.choice(enemies)
    # Tirada de Salvación: Dificultad basada en el Monje vs Constitución del Monstruo
    from posada.engine import calculate_save_dc, roll_d20
    save_dc = calculate_save_dc(caster)
    m_save = roll_d20() + target['stats']['con']

    if m_save < save_dc:
        target['status'].add('STUNNED')
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"⚡ {caster.name} golpea puntos nerviosos. ¡[bold red]{target['name']}[/bold red] queda [bold yellow]ATURDIDO[/bold yellow]!"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🛡️ {caster.name} intenta un Golpe Aturdidor, pero [bold red]{target['name']}[/bold red] resiste el impacto."})
    return True


@SkillRegistry.register(
    skill_id="fuerzas_flaqueza", name="Fuerzas de Flaqueza", skill_type="SESSION", req_level=1, allowed_classes=["FTR"]
)
def fuerzas_flaqueza(context):
    caster = context['caster']

    if context.get('eval_mode'):
        # Solo usar si ha perdido más de 10 HP
        return 85 if (caster.max_hp - caster.current_hp) >= 10 else 0

    heal = random.randint(1, 10) + caster.level
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal)
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"❤️‍🩹 {caster.name} recupera el aliento con [bold green]Fuerzas de Flaqueza[/bold green] (+{heal} HP)."})
    return True

# ==========================================
# CUSTODIOS DIVINOS Y PRIMALES
# ==========================================


@SkillRegistry.register(
    skill_id="imposicion_manos", name="Imposición de Manos", skill_type="SESSION", req_level=1, allowed_classes=["PAL"]
)
def imposicion_manos(context):
    caster = context['caster']
    allies = context['allies']

    # IA: Evalúa al aliado más herido
    wounded_allies = [a for a in allies if a.current_hp < a.max_hp]
    if context.get('eval_mode'):
        if not wounded_allies:
            return 0
        target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
        hp_missing = target.max_hp - target.current_hp
        # Alta prioridad si alguien está muriendo
        return 50 + min(40, hp_missing * 4)

    target = min(wounded_allies, key=lambda a: a.current_hp / a.max_hp)
    heal = caster.level * 5  # Curación masiva
    target.current_hp = min(target.max_hp, target.current_hp + heal)
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✋ {caster.name} toca a {target.name} usando [bold yellow]Imposición de Manos[/bold yellow] (+{heal} HP)."})
    return True


@SkillRegistry.register(
    skill_id="castigo_divino", name="Castigo Divino", skill_type="COMBAT", req_level=2, allowed_classes=["PAL"]
)
def castigo_divino(context):
    caster = context['caster']
    enemies = context['enemies']

    # IA: Gran golpe para acabar combates rápido. Score base 70.
    if context.get('eval_mode'):
        return 70 if enemies else 0

    target = random.choice(enemies)
    adv_mods = caster.get_stat_modifiers()

    # Tirada de ataque normal
    a_roll = random.randint(1, 20) + max(adv_mods['str'], adv_mods['dex'])
    m_evasion = 10 + target['stats']['dex']

    if a_roll >= m_evasion:
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1
        base_dmg = sum(random.randint(1, sides) for _ in range(
            count)) + adv_mods['damage'] + adv_mods['str']

        # Daño extra de Castigo Divino (Radiante)
        smite_dmg = sum(random.randint(1, 8) for _ in range(2))  # 2d8 base
        total_dmg = base_dmg + smite_dmg

        target['hp'] -= total_dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"☀️ ¡El arma de {caster.name} brilla! [bold yellow]Castigo Divino[/bold yellow] arrasa a [bold red]{target['name']}[/bold red] ({total_dmg} daño)."})
    else:
        # El paladín no gasta el uso si falla el golpe (regla oficial de D&D)
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🛡️ {caster.name} falla el golpe e interrumpe su [bold yellow]Castigo Divino[/bold yellow] para no desperdiciarlo."})
        return False  # Devolver False evita que el motor marque la habilidad como "usada"
    return True


@SkillRegistry.register(
    skill_id="expulsar_muertos", name="Expulsar Impíos", skill_type="COMBAT", req_level=2, allowed_classes=["CLR"]
)
def expulsar_muertos(context):
    caster = context['caster']
    enemies = context['enemies']

    # IA: Excelente si hay muchos enemigos (Daño en Área / Control)
    if context.get('eval_mode'):
        # Más enemigos = mayor utilidad (hasta 100)
        return 40 + (len(enemies) * 15)

    from posada.engine import calculate_save_dc, roll_d20
    save_dc = calculate_save_dc(caster)

    affected = 0
    for m in enemies:
        m_save = roll_d20() + m['stats']['wis']
        if m_save < save_dc:
            # En el motor simulamos el "miedo" como aturdimiento para que pierdan turnos
            m['status'].add('STUNNED')
            affected += 1

    if affected > 0:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"✨ {caster.name} alza su símbolo sagrado. ¡{affected} enemigo(s) se acobardan por el fulgor divino!"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🌑 {caster.name} usa Expulsar Impíos, pero los monstruos resisten la luz."})
    return True


@SkillRegistry.register(
    skill_id="forma_salvaje", name="Forma Salvaje", skill_type="SESSION", req_level=2, allowed_classes=["DRD"]
)
def forma_salvaje(context):
    caster = context['caster']
    adv_status = context['adv_status']

    # IA: Usar si la salud de su forma normal baja demasiado (funciona como escudo de HP)
    if context.get('eval_mode'):
        if 'WILD_SHAPE' in adv_status[caster.id]:
            return 0
        return 85 if caster.current_hp < (caster.max_hp * 0.5) else 30

    adv_status[caster.id].add('WILD_SHAPE')

    # En D&D, Forma Salvaje te da un pool de HP temporal. Para simularlo de forma limpia,
    # el druida se cura masivamente al transformarse.
    heal = caster.level * 4
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal)

    animal = random.choice(
        ["Lobo Terrible", "Oso Pardo", "Tigre Gigante", "Araña de Fase"])
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🐺 {caster.name} se transforma en un [bold green]{animal}[/bold green] revitalizando su cuerpo (+{heal} HP)."})
    return True


@SkillRegistry.register(
    skill_id="marca_cazador", name="Marca del Cazador", skill_type="COMBAT", req_level=2, allowed_classes=["RGR"]
)
def marca_cazador(context):
    caster = context['caster']
    enemies = context['enemies']
    adv_status = context['adv_status']

    # IA: Usarlo siempre que sea posible para buffear el daño a largo plazo
    if context.get('eval_mode'):
        return 85 if enemies else 0

    target = random.choice(enemies)
    # Aplicamos un estado único al monstruo que podemos revisar luego
    target['status'].add('HUNTERS_MARK')

    # Hacemos que el Ranger ataque inmediatamente con el bonus (simulando que Marca es Acción Adicional)
    adv_mods = caster.get_stat_modifiers()
    attack_stat = max(adv_mods['str'], adv_mods['dex'])
    a_roll = random.randint(1, 20) + attack_stat
    m_evasion = 10 + target['stats']['dex']

    context['log'].append({"second": context['current_second'] - 1, "type": "flavor",
                           "message": f"👁️ {caster.name} fija su [bold green]Marca del Cazador[/bold green] sobre [bold red]{target['name']}[/bold red]."})

    if a_roll >= m_evasion:
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1

        # Daño del arma + Daño extra de la Marca (1d6)
        base_dmg = sum(random.randint(1, sides) for _ in range(
            count)) + adv_mods['damage'] + adv_mods['str']
        mark_dmg = random.randint(1, 6)
        total_dmg = base_dmg + mark_dmg

        target['hp'] -= total_dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🏹 El golpe certero de {caster.name} inflige {total_dmg} daño al objetivo marcado."})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"💨 {caster.name} marca al objetivo, pero su ataque posterior falla."})
    return True

# ==========================================
# ERUDITOS ARCANOS
# ==========================================


@SkillRegistry.register(
    skill_id="bola_de_fuego", name="Bola de Fuego", skill_type="SESSION", req_level=5, allowed_classes=["WIZ", "SOR"]
)
def bola_de_fuego(context):
    caster = context['caster']
    enemies = context['enemies']

    # IA: Solo usar si hay múltiples enemigos vivos. Score base 85.
    if context.get('eval_mode'):
        return 85 if len(enemies) > 1 else 20

    from posada.engine import calculate_save_dc, roll_d20
    save_dc = calculate_save_dc(caster)

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔥 {caster.name} conjura una [bold red]Bola de Fuego[/bold red] que envuelve el campo de batalla."})

    fire_dmg = sum(random.randint(1, 6)
                   for _ in range(8))  # 8d6 de daño de fuego

    # Daño en área a TODOS los enemigos
    for target in enemies:
        m_save = roll_d20() + target['stats']['dex']
        dmg_taken = fire_dmg if m_save < save_dc else fire_dmg // 2
        target['hp'] -= dmg_taken
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> [bold red]{target['name']}[/bold red] recibe {dmg_taken} daño por quemaduras."})

    return True


@SkillRegistry.register(
    skill_id="inspiracion_bardica", name="Inspiración Bárdica", skill_type="COMBAT", req_level=1, allowed_classes=["BRD"]
)
def inspiracion_bardica(context):
    caster = context['caster']
    allies = context['allies']
    adv_status = context['adv_status']

    # IA: Priorizar si un aliado no tiene inspiración
    uninspired_allies = [
        a for a in allies if 'INSPIRED' not in adv_status[a.id]]
    if context.get('eval_mode'):
        return 65 if uninspired_allies else 0

    target = random.choice(uninspired_allies)
    adv_status[target.id].add('INSPIRED')

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎵 {caster.name} toca una melodía heroica. ¡{target.name} gana [bold yellow]Inspiración Bárdica[/bold yellow]!"})
    return True


@SkillRegistry.register(
    skill_id="eldritch_blast", name="Descarga Sobrenatural", skill_type="COMBAT", req_level=1, allowed_classes=["WLK"]
)
def eldritch_blast(context):
    caster = context['caster']
    enemies = context['enemies']

    # IA: Como es el ataque principal del Warlock, siempre es buena idea.
    if context.get('eval_mode'):
        return 55 if enemies else 0

    adv_mods = caster.get_stat_modifiers()
    attack_stat = adv_mods['cha']

    # Escala con el nivel: 1 rayo a Nv 1, 2 rayos a Nv 5
    beams = 2 if caster.level >= 5 else 1

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌌 {caster.name} dispara {beams} rayo(s) de [bold magenta]Descarga Sobrenatural[/bold magenta]."})

    for i in range(beams):
        if not enemies:
            break
        target = random.choice(enemies)

        a_roll = random.randint(1, 20) + attack_stat
        m_evasion = 10 + target['stats']['dex']

        if a_roll >= m_evasion:
            # Daño: 1d10 + modificador de Carisma (gracias a Agonizing Blast)
            dmg = random.randint(1, 10) + adv_mods['cha']
            target['hp'] -= dmg
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> ¡El rayo impacta a [bold red]{target['name']}[/bold red] por {dmg} daño de fuerza!"})
        else:
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> El rayo pasa rozando a [bold red]{target['name']}[/bold red]."})

    return True


@SkillRegistry.register(
    skill_id="infusion_basica", name="Infusión de Artífice", skill_type="SESSION", req_level=2, allowed_classes=["ART"]
)
def infusion_basica(context):
    caster = context['caster']
    allies = context['allies']
    adv_status = context['adv_status']

    # IA: Priorizar dar +1 a las armas de un aliado fuerte
    if context.get('eval_mode'):
        # Busca aliados físicos sin el buff
        targets = [a for a in allies if a.adv_class in [
            'FTR', 'BBN', 'RGR'] and 'INFUSED_WEAPON' not in adv_status[a.id]]
        return 75 if targets else 40

    # Si hay aliados marciales, buffearlos. Si no, buffearse a sí mismo.
    targets = [a for a in allies if a.adv_class in [
        'FTR', 'BBN', 'RGR'] and 'INFUSED_WEAPON' not in adv_status[a.id]]
    target = random.choice(targets) if targets else caster

    adv_status[target.id].add('INFUSED_WEAPON')

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚙️ {caster.name} ajusta las tuercas del equipo de {target.name}. Gana [bold blue]Arma Infundida[/bold blue] (+1 Daño)."})
    return True
