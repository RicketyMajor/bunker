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


# Removido: curacion_menor antigua (reemplazada en la sección exclusiva del PAL)

@SkillRegistry.register(
    skill_id="golpe_brutal", name="Golpe Brutal", skill_type="COMBAT", req_level=1, allowed_classes=["BBN"]
)
def golpe_brutal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        if caster.class_resources.get('stamina', 0) < 1 and caster.class_resources.get('furia', 0) < 1:
            return 0
        return 60 if context['enemies'] else 0

    if 'stamina' in caster.class_resources and caster.class_resources['stamina'] > 0:
        caster.class_resources['stamina'] -= 1

    target = random.choice(context['enemies'])
    adv_mods = caster.get_stat_modifiers()

    m_evasion = 8 + max(target['stats']['dex'],
                        target['stats'].get('armor', 0))
    a_raw_roll = random.randint(1, 20)
    a_roll_total = a_raw_roll + adv_mods['str'] - 2

    if a_raw_roll == 20 or (a_raw_roll != 1 and a_roll_total >= m_evasion):
        sides = adv_mods.get('weapon_dice_sides', 4) or 4
        count = adv_mods.get('weapon_dice_count', 1) or 1
        dmg = sum(random.randint(1, sides) for _ in range(count + 1)
                  ) + adv_mods['damage'] + (adv_mods['str'] * 2)

        final_dmg = max(1, dmg - target['stats']['con'])
        target['hp'] -= final_dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"💥 {caster.name} ejecuta un [bold yellow]Golpe Brutal[/bold yellow] aplastando a [bold red]{target['name']}[/bold red] por {final_dmg} de daño."})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"💨 {caster.name} intenta un [bold yellow]Golpe Brutal[/bold yellow] pero falla."})
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


# Removido: accion_astuta antigua (reemplazada en la sección exclusiva del ROG)


# Removido: golpe_aturdidor antigua (reemplazada en la sección exclusiva del MNK)


# Removido: imposicion_manos y castigo_divino antiguas (reemplazadas en la sección exclusiva del PAL)

# ==========================================
# ERUDITOS ARCANOS
# ==========================================


# Removido: bola_de_fuego antigua (reemplazada en la sección exclusiva de WIZ)


# Removido: eldritch_blast antigua (reemplazada en la sección exclusiva del WLK)

# ==========================================
# ARTIFICER SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="chatarra_magica", name="Chatarra Mágica", skill_type="SESSION", req_level=1, allowed_classes=["ART"]
)
def chatarra_magica(context):
    caster = context['caster']
    if context.get('eval_mode'):
        # Solo usar si hay aliados heridos
        allies = [a for a in context['allies'] if a.current_hp < a.max_hp]
        return 45 if allies else 0

    adv_mods = caster.get_stat_modifiers()
    heal_amount = max(1, random.randint(1, 4) + adv_mods['int'])
    
    allies = [a for a in context['allies'] if a.current_hp < a.max_hp]
    if allies:
        target = min(allies, key=lambda a: a.current_hp / a.max_hp)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"🔧 {caster.name} ajusta la armadura abollada de {target.name}, restaurando {heal_amount} HP."})
    return True

@SkillRegistry.register(
    skill_id="infusiones_basicas", name="Infusiones Básicas", skill_type="SESSION", req_level=2, allowed_classes=["ART"]
)
def infusiones_basicas(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 40

    target = random.choice(context['allies'])
    # Se traduce como un ataque gratuito del aliado (un buff simulado)
    if not context['enemies']:
        return False
    
    enemy = random.choice(context['enemies'])
    dmg = random.randint(1, 6) + caster.get_stat_modifiers()['int']
    enemy['hp'] -= dmg
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✨ {caster.name} imbuye temporalmente el arma de {target.name}. ¡El impacto infundido inflige {dmg} de daño extra a [bold red]{enemy['name']}[/bold red]!"})
    return True

@SkillRegistry.register(
    skill_id="especializacion_temprana", name="Especialización Temprana", skill_type="COMBAT", req_level=3, allowed_classes=["ART"]
)
def especializacion_temprana(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 60 if context['enemies'] else 0

    adv_mods = caster.get_stat_modifiers()
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚙️ {caster.name} despliega su Cañón Elíxir en el campo de batalla."})
    
    if context['enemies']:
        target = random.choice(context['enemies'])
        dmg = random.randint(2, 16) + adv_mods['int'] # 2d8
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💥 El Cañón dispara a [bold red]{target['name']}[/bold red], infligiendo {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="ajuste_tuercas", name="Ajuste de Tuercas", skill_type="SESSION", req_level=4, allowed_classes=["ART"]
)
def ajuste_tuercas(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        # Solo evaluar alto si alguien tiene estados negativos
        for status_list in adv_status.values():
            if any(s in status_list for s in ['PSN', 'BRN', 'BLD']):
                return 70
        return 0

    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]
        if bad_status:
            cured = bad_status[0]
            adv_status[adv.id].remove(cured)
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"🧰 {caster.name} repara rápidamente el equipo de {adv.name}, anulando el efecto de {cured}."})
            return True
    return False

@SkillRegistry.register(
    skill_id="municion_arcana", name="Munición Arcana", skill_type="COMBAT", req_level=5, allowed_classes=["ART"]
)
def municion_arcana(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if len(context['enemies']) >= 1 else 0

    adv_mods = caster.get_stat_modifiers()
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔫 {caster.name} dispara Munición Arcana explosiva."})
    
    if not context['enemies']: return False
    
    target1 = random.choice(context['enemies'])
    dmg1 = random.randint(1, 8) + adv_mods['int']
    target1['hp'] -= dmg1
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"    -> Impacto directo en [bold red]{target1['name']}[/bold red] por {dmg1} daño."})
                           
    other_enemies = [e for e in context['enemies'] if e != target1]
    if other_enemies:
        target2 = random.choice(other_enemies)
        dmg2 = random.randint(1, 8)
        target2['hp'] -= dmg2
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> ☄️ La metralla alcanza a [bold red]{target2['name']}[/bold red] por {dmg2} daño."})
    return True

@SkillRegistry.register(
    skill_id="sintonia_avanzada", name="Sintonía Avanzada", skill_type="SESSION", req_level=6, allowed_classes=["ART"]
)
def sintonia_avanzada(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 50 if caster.current_hp < caster.max_hp else 0

    adv_mods = caster.get_stat_modifiers()
    heal_amount = max(1, random.randint(2, 8) + adv_mods['int'])
    
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"🔋 {caster.name} canaliza la energía estática de sus objetos mágicos, curándose {heal_amount} HP."})
    return True

@SkillRegistry.register(
    skill_id="genio_intermitente", name="Genio Intermitente", skill_type="SESSION", req_level=7, allowed_classes=["ART"]
)
def genio_intermitente(context):
    caster = context['caster']
    if context.get('eval_mode'):
        # Alto puntaje si un aliado está a menos del 25% de vida
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
        return 80 if critical_allies else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
    if critical_allies:
        target = random.choice(critical_allies)
        heal_amount = max(5, random.randint(3, 12) + caster.get_stat_modifiers()['int'] * 2)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"💡 {caster.name} tiene un chispazo de genialidad y desvía un golpe letal que iba hacia {target.name}, restaurando {heal_amount} HP equivalentes."})
        return True
    return False

@SkillRegistry.register(
    skill_id="blindaje_runico", name="Blindaje Rúnico", skill_type="SESSION", req_level=8, allowed_classes=["ART"]
)
def blindaje_runico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 55 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    dmg = random.randint(2, 12) + caster.get_stat_modifiers()['int']
    target['hp'] -= dmg
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ La armadura de {caster.name} libera una descarga rúnica. [bold red]{target['name']}[/bold red] recibe {dmg} daño eléctrico al acercarse."})
    return True

@SkillRegistry.register(
    skill_id="prototipo_explosivo", name="Prototipo Explosivo", skill_type="COMBAT", req_level=9, allowed_classes=["ART"]
)
def prototipo_explosivo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if len(context['enemies']) > 1 else 30

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💣 {caster.name} lanza un invento inestable al centro del grupo enemigo."})
    
    for target in context['enemies']:
        dmg = sum(random.randint(1, 6) for _ in range(3)) # 3d6
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💥 [bold red]{target['name']}[/bold red] recibe {dmg} daño por fuerza."})
    return True

@SkillRegistry.register(
    skill_id="replica_objeto", name="Réplica de Objeto", skill_type="SESSION", req_level=10, allowed_classes=["ART"]
)
def replica_objeto(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 # Siempre útil

    if random.random() < 0.50:
        from .models import Item, ItemRarity
        items_db = list(Item.objects.filter(rarity__in=['COM', 'UNC']))
        if items_db:
            drop_item = random.choice(items_db)
            context['log'].append({"second": context['current_second'], "type": "item_loot", "item_id": drop_item.id, "adventurer_id": caster.id,
                                   "message": f"🛠️ {caster.name} ha fabricado un prototipo rápido: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🛠️ {caster.name} intenta fabricar un objeto, pero el prototipo falla estrepitosamente."})
    return True

# ==========================================
# BARBARIAN SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="furia_feroz", name="Furia Feroz", skill_type="COMBAT", req_level=1, allowed_classes=["BBN"]
)
def furia_feroz(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 50 if context['enemies'] else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    dmg = random.randint(1, 12) + adv_mods['str'] * 2
    target['hp'] -= dmg
    
    # "Reduces physical damage taken" -> We heal the barbarian a bit.
    heal_amount = max(1, dmg // 3)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"😡 {caster.name} entra en Furia Feroz y ataca a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"🛡️ Su trance bélico le permite ignorar el dolor, recuperando {heal_amount} HP equivalentes."})
    return True

@SkillRegistry.register(
    skill_id="ataque_temerario", name="Ataque Temerario", skill_type="COMBAT", req_level=2, allowed_classes=["BBN"]
)
def ataque_temerario(context):
    caster = context['caster']
    if context.get('eval_mode'):
        # High value if he has plenty of HP to spare
        return 70 if context['enemies'] and caster.current_hp > (caster.max_hp * 0.5) else 20

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    # Ventaja = tira dos veces, elige el mejor (lo simulamos con daño alto)
    dmg1 = random.randint(1, 12) + adv_mods['str']
    dmg2 = random.randint(1, 12) + adv_mods['str']
    final_dmg = max(dmg1, dmg2) + 5
    
    target['hp'] -= final_dmg
    
    # Enemies have advantage against him = take recoil damage
    recoil = max(1, random.randint(1, 6))
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚔️ {caster.name} lanza un Ataque Temerario contra [bold red]{target['name']}[/bold red] infligiendo {final_dmg} daño masivo."})
    context['log'].append({"second": context['current_second'], "type": "damage", "adventurer_id": caster.id, "amount": recoil,
                           "message": f"🩸 Por exponerse tanto, {caster.name} recibe {recoil} daño de contragolpe."})
    return True

@SkillRegistry.register(
    skill_id="senda_furia", name="Senda de la Furia", skill_type="SESSION", req_level=3, allowed_classes=["BBN"]
)
def senda_furia(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if len(context['enemies']) >= 2 else 10

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🦅 {caster.name} ruge, canalizando el poder de su Senda de la Furia."})
    
    for target in context['enemies']:
        dmg = random.randint(1, 6) + caster.get_stat_modifiers()['str']
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> [bold red]{target['name']}[/bold red] tiembla de terror y recibe {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="piel_curtida", name="Piel Curtida", skill_type="SESSION", req_level=4, allowed_classes=["BBN"]
)
def piel_curtida(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 60 if caster.current_hp < caster.max_hp else 0

    adv_mods = caster.get_stat_modifiers()
    heal_amount = max(1, random.randint(2, 10) + adv_mods['con'] + adv_mods['str'])
    
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"💪 {caster.name} flexiona su Piel Curtida por las batallas, curándose {heal_amount} HP."})
    return True

@SkillRegistry.register(
    skill_id="ataque_extra_bbn", name="Ataque Extra (Bárbaro)", skill_type="COMBAT", req_level=5, allowed_classes=["BBN"]
)
def ataque_extra_bbn(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if len(context['enemies']) >= 1 else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    
    # Primer ataque
    target1 = random.choice(context['enemies'])
    dmg1 = random.randint(1, 12) + adv_mods['str']
    target1['hp'] -= dmg1
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🪓 {caster.name} asesta un primer golpe a [bold red]{target1['name']}[/bold red] ({dmg1} daño)."})
    
    # Segundo ataque
    living_enemies = [e for e in context['enemies'] if e['hp'] > 0]
    if living_enemies:
        target2 = random.choice(living_enemies)
        dmg2 = random.randint(1, 12) + adv_mods['str']
        target2['hp'] -= dmg2
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> Y un Ataque Extra brutal contra [bold red]{target2['name']}[/bold red] ({dmg2} daño)."})
    return True

@SkillRegistry.register(
    skill_id="instinto_manada", name="Instinto de Manada", skill_type="SESSION", req_level=6, allowed_classes=["BBN"]
)
def instinto_manada(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 70 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🐺 Usando su Instinto de Manada, {caster.name} guía al grupo lejos del peligro."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = max(2, random.randint(1, 6) + caster.get_stat_modifiers()['wis'])
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} descansa seguro ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="instinto_salvaje", name="Instinto Salvaje", skill_type="COMBAT", req_level=7, allowed_classes=["BBN"]
)
def instinto_salvaje(context):
    caster = context['caster']
    if context.get('eval_mode'):
        # Solo tiene sentido usar esto al inicio (enemigos con casi toda la vida)
        if not context['enemies']: return 0
        target = context['enemies'][0]
        # Simular si están intactos
        return 85 if target['hp'] >= target.get('max_hp', 10) * 0.9 else 10

    if not context['enemies']: return False
    
    target = random.choice(context['enemies'])
    dmg = sum(random.randint(1, 10) for _ in range(3)) + caster.get_stat_modifiers()['str']
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚡ Movido por su Instinto Salvaje, {caster.name} se abalanza primero y destroza a [bold red]{target['name']}[/bold red] con {dmg} de daño."})
    return True

@SkillRegistry.register(
    skill_id="zancada_poderosa", name="Zancada Poderosa", skill_type="SESSION", req_level=8, allowed_classes=["BBN"]
)
def zancada_poderosa(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 55 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    dmg = random.randint(2, 16) + caster.get_stat_modifiers()['str']
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌪️ {caster.name} atraviesa el terreno con su Zancada Poderosa, atropellando a [bold red]{target['name']}[/bold red] y causándole {dmg} de daño."})
    return True

@SkillRegistry.register(
    skill_id="critico_brutal", name="Crítico Brutal", skill_type="COMBAT", req_level=9, allowed_classes=["BBN"]
)
def critico_brutal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    # 3d12
    dmg = sum(random.randint(1, 12) for _ in range(3)) + caster.get_stat_modifiers()['str'] * 3
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🩸 ¡CRÍTICO BRUTAL! {caster.name} parte en dos a [bold red]{target['name']}[/bold red] infligiendo unos monstruosos {dmg} de daño."})
    return True

@SkillRegistry.register(
    skill_id="presencia_intimidante", name="Presencia Intimidante", skill_type="SESSION", req_level=10, allowed_classes=["BBN"]
)
def presencia_intimidante(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    # Si es SML o MED, y falla salvación (lo hacemos automático en el motor)
    if getattr(target.get('base'), 'category', 'SML') in ['SML', 'MED']:
        dmg = target['hp'] # Ejecución instakill
        target['hp'] = 0
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"👹 {caster.name} suelta un grito tan aterrador que [bold red]{target['name']}[/bold red] huye despavorido del combate."})
    else:
        dmg = sum(random.randint(1, 10) for _ in range(4))
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"👹 La Presencia Intimidante de {caster.name} paraliza a [bold red]{target['name']}[/bold red], causándole {dmg} de daño por pánico."})
    return True

# ==========================================
# BARD SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="inspiracion_bardica", name="Inspiración Bárdica", skill_type="COMBAT", req_level=1, allowed_classes=["BRD"]
)
def inspiracion_bardica(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 50 if context['enemies'] and context['allies'] else 0

    if not context['enemies'] or not context['allies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target_enemy = random.choice(context['enemies'])
    buffed_ally = random.choice([a for a in context['allies'] if a != caster] or [caster])
    
    dmg = random.randint(1, 6) + adv_mods['cha']
    target_enemy['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎵 {caster.name} toca una melodía motivadora. ¡Inspirado, {buffed_ally.name} asesta un golpe rápido a [bold red]{target_enemy['name']}[/bold red] por {dmg} de daño!"})
    return True

@SkillRegistry.register(
    skill_id="erudito_todo", name="Erudito de Todo", skill_type="SESSION", req_level=2, allowed_classes=["BRD"]
)
def erudito_todo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 45

    coins = random.randint(1, 5) * 5 # 5 a 25 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"📚 Gracias a su conocimiento como Erudito de Todo, {caster.name} identifica el valor de unos trastos que los demás ignoraron (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="cancion_descanso", name="Canción de Descanso", skill_type="SESSION", req_level=3, allowed_classes=["BRD"]
)
def cancion_descanso(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎶 {caster.name} interpreta una apacible Canción de Descanso para el grupo."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(1, 6) + caster.get_stat_modifiers()['cha']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} recobra fuerzas ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="oido_absoluto", name="Oído Absoluto", skill_type="SESSION", req_level=4, allowed_classes=["BRD"]
)
def oido_absoluto(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 55 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"👂 Usando su Oído Absoluto, {caster.name} detecta un crujido sutil y detiene al grupo antes de activar una trampa."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = max(1, caster.get_stat_modifiers()['wis'] + caster.get_stat_modifiers()['cha'])
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} respira aliviado por haber evitado el peligro ({heal_amount} HP equivalentes)."})
    return True

@SkillRegistry.register(
    skill_id="inspiracion_fontanal", name="Inspiración Fontanal", skill_type="SESSION", req_level=5, allowed_classes=["BRD"]
)
def inspiracion_fontanal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.4)]
        return 75 if critical_allies else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.4)]
    if critical_allies:
        target = random.choice(critical_allies)
        heal_amount = random.randint(4, 16) + caster.get_stat_modifiers()['cha'] * 2
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"⛲ {caster.name} recita un himno épico de Inspiración Fontanal. ¡{target.name} se llena de vitalidad inagotable y recupera {heal_amount} HP!"})
        return True
    return False

@SkillRegistry.register(
    skill_id="contrahechizo_musical", name="Contrahechizo Musical", skill_type="COMBAT", req_level=6, allowed_classes=["BRD"]
)
def contrahechizo_musical(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if any(s in status_list for s in ['PSN', 'BRN', 'BLD']):
                return 80
        return 0

    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]
        if bad_status:
            for s in bad_status:
                adv_status[adv.id].remove(s)
            
            heal_amount = random.randint(1, 8) + caster.get_stat_modifiers()['cha']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"🎸 {caster.name} toca un Contrahechizo Musical disonante que quiebra la magia enemiga, limpiando los estados de {adv.name} y curándole {heal_amount} HP."})
            return True
    return False

@SkillRegistry.register(
    skill_id="murmullo_perturbador", name="Murmullo Perturbador", skill_type="COMBAT", req_level=7, allowed_classes=["BRD"]
)
def murmullo_perturbador(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 60 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = max(5, caster.get_stat_modifiers()['cha'] * 3) + random.randint(1, 8)
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🗣️ {caster.name} le lanza un insulto psíquico con Murmullo Perturbador a [bold red]{target['name']}[/bold red], infligiéndole {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="presencia_escenica", name="Presencia Escénica", skill_type="SESSION", req_level=8, allowed_classes=["BRD"]
)
def presencia_escenica(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85

    coins = 100 # 1 Drabin
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🎭 Gracias a la Presencia Escénica de {caster.name}, el grupo impresiona a unos mercaderes y consiguen un botín garantizado (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="improvisacion_magica", name="Improvisación Mágica", skill_type="COMBAT", req_level=9, allowed_classes=["BRD"]
)
def improvisacion_magica(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if len(context['enemies']) >= 2 else 40

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎭 {caster.name} recurre a su Improvisación Mágica, imitando un hechizo elemental destructivo a la perfección."})
    
    for target in context['enemies']:
        dmg = sum(random.randint(1, 8) for _ in range(4)) + caster.get_stat_modifiers()['cha'] # 4d8
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💥 El hechizo improvisado devasta a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="secretos_magicos", name="Secretos Mágicos", skill_type="COMBAT", req_level=10, allowed_classes=["BRD"]
)
def secretos_magicos(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 if context['enemies'] and context['allies'] else 0

    if not context['enemies'] or not context['allies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target_enemy = random.choice(context['enemies'])
    buffed_ally = min(context['allies'], key=lambda a: a.current_hp / a.max_hp)
    
    dmg = random.randint(2, 20) + adv_mods['cha'] * 2
    heal_amount = random.randint(2, 20) + adv_mods['cha'] * 2
    
    target_enemy['hp'] -= dmg
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌟 Usando Secretos Mágicos, {caster.name} fusiona roles: asesta {dmg} daño mágico a [bold red]{target_enemy['name']}[/bold red]..."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": buffed_ally.id, "amount": heal_amount,
                           "message": f"🌟 ...y simultáneamente canaliza un milagro que cura a {buffed_ally.name} por {heal_amount} HP."})
    return True

# ==========================================
# CLERIC SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="dominio_divino", name="Dominio Divino", skill_type="SESSION", req_level=1, allowed_classes=["CLR"]
)
def dominio_divino(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 50 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🕊️ Guiado por su Dominio Divino, {caster.name} proyecta un santuario de paz."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(1, 4) + caster.get_stat_modifiers()['wis']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} se baña en luz sagrada ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="canalizar_divinidad", name="Canalizar Divinidad", skill_type="COMBAT", req_level=2, allowed_classes=["CLR"]
)
def canalizar_divinidad(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 55 if context['enemies'] else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    dmg = random.randint(2, 16) + adv_mods['wis'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"☀️ {caster.name} logra Canalizar Divinidad, disparando un haz radiante que calcina a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="aura_devocion", name="Aura de Devoción", skill_type="SESSION", req_level=3, allowed_classes=["CLR"]
)
def aura_devocion(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if any(s in status_list for s in ['PSN', 'BRN', 'BLD']):
                return 75
        return 0

    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]
        if bad_status:
            for s in bad_status:
                adv_status[adv.id].remove(s)
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"✨ El Aura de Devoción constante de {caster.name} purifica instantáneamente las aflicciones de {adv.name}."})
            return True
    return False

@SkillRegistry.register(
    skill_id="bendicion_matutina", name="Bendición Matutina", skill_type="SESSION", req_level=4, allowed_classes=["CLR"]
)
def bendicion_matutina(context):
    caster = context['caster']
    if context.get('eval_mode'):
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.5)]
        return 65 if critical_allies else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.5)]
    if critical_allies:
        target = random.choice(critical_allies)
        heal_amount = max(5, random.randint(2, 12) + caster.get_stat_modifiers()['wis'] * 3)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"🙏 Una trampa mortal falla por centímetros gracias a la Bendición Matutina de {caster.name}. {target.name} se salva ileso ({heal_amount} HP equivalentes)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="destruir_muertos", name="Destruir Muertos Vivientes", skill_type="COMBAT", req_level=5, allowed_classes=["CLR"]
)
def destruir_muertos(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💀 {caster.name} levanta su símbolo sagrado para Destruir Muertos Vivientes."})
    
    for target in context['enemies']:
        # Instakill para pequeños y medianos, daño para los grandes
        if getattr(target.get('base'), 'category', 'SML') in ['SML', 'MED']:
            target['hp'] = 0
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> 💨 [bold red]{target['name']}[/bold red] es desintegrado en polvo de estrellas."})
        else:
            dmg = random.randint(1, 8) + caster.get_stat_modifiers()['wis']
            target['hp'] -= dmg
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> 🔥 [bold red]{target['name']}[/bold red] arde con fuego celestial ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="intercesion_protectora", name="Intercesión Protectora", skill_type="COMBAT", req_level=6, allowed_classes=["CLR"]
)
def intercesion_protectora(context):
    caster = context['caster']
    if context.get('eval_mode'):
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
        return 90 if critical_allies else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
    if critical_allies:
        target = random.choice(critical_allies)
        heal_amount = max(10, random.randint(5, 20) + caster.get_stat_modifiers()['wis'] * 3)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"🛡️ ¡Intercesión Protectora! {caster.name} salta frente a un golpe letal dirigido a {target.name}, curándole {heal_amount} HP y salvándole la vida."})
        return True
    return False

@SkillRegistry.register(
    skill_id="escudo_fe", name="Escudo de Fe", skill_type="SESSION", req_level=7, allowed_classes=["CLR"]
)
def escudo_fe(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 55 if caster.current_hp < caster.max_hp else 0

    heal_amount = random.randint(2, 12) + caster.get_stat_modifiers()['wis'] * 2
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"🛡️ El Escudo de Fe pasivo de {caster.name} amortigua los golpes ambientales constantes ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="golpe_divino", name="Golpe Divino", skill_type="COMBAT", req_level=8, allowed_classes=["CLR"]
)
def golpe_divino(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 8) for _ in range(3)) + caster.get_stat_modifiers()['wis'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚔️ {caster.name} ejecuta un Golpe Divino espectacular que parte a [bold red]{target['name']}[/bold red] infligiendo {dmg} de daño radiante."})
    return True

@SkillRegistry.register(
    skill_id="comunion_diaria", name="Comunión Diaria", skill_type="SESSION", req_level=9, allowed_classes=["CLR"]
)
def comunion_diaria(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 # Siempre útil buscar botín

    from .models import Item, ItemRarity
    items_db = list(Item.objects.filter(rarity__in=['COM', 'UNC']))
    if items_db:
        drop_item = random.choice(items_db)
        context['log'].append({"second": context['current_second'], "type": "item_loot", "item_id": drop_item.id, "adventurer_id": caster.id,
                               "message": f"📿 Tras una Comunión Diaria, los dioses guían a {caster.name} hacia un tesoro oculto: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"📿 {caster.name} reza, pero los dioses guardan silencio hoy."})
    return True

@SkillRegistry.register(
    skill_id="intervencion_divina", name="Intervención Divina", skill_type="COMBAT", req_level=10, allowed_classes=["CLR"]
)
def intervencion_divina(context):
    caster = context['caster']
    if context.get('eval_mode'):
        # Solo usar si hay al menos 2 monstruos o es jefe, muy raro de evaluar pero muy potente
        return 95 if len(context['enemies']) >= 2 else 50

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌟 {caster.name} cae de rodillas e implora una Intervención Divina a los cielos..."})
    
    d100 = random.randint(1, 100)
    # Probabilidad = Nivel de Clérigo (10%)
    if d100 <= caster.level:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 🌩️ ¡UN MILAGRO! ¡El cielo se abre y un cataclismo sagrado cae sobre los monstruos!"})
        for target in context['enemies']:
            target['hp'] = 0
            context['log'].append({"second": context['current_second'], "type": "flavor",
                                   "message": f"    -> [bold red]{target['name']}[/bold red] es borrado de la existencia."})
    else:
        dmg = random.randint(2, 20) + caster.get_stat_modifiers()['wis']
        target = random.choice(context['enemies'])
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> ⚡ Los dioses no bajan, pero otorgan fuerza. [bold red]{target['name']}[/bold red] sufre {dmg} de daño celestial."})
    return True

# ==========================================
# DRUID SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="druidico", name="Druídico", skill_type="SESSION", req_level=1, allowed_classes=["DRD"]
)
def druidico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 45

    coins = random.randint(2, 6) * 5 # 10 a 30 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🌿 Leyendo las marcas en Druídico dejadas en un árbol subterráneo, {caster.name} descubre un alijo escondido (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="forma_salvaje", name="Forma Salvaje", skill_type="COMBAT", req_level=2, allowed_classes=["DRD"]
)
def forma_salvaje(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if context['enemies'] else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    # Curación temporal por convertirse en bestia
    heal_amount = random.randint(2, 8) + adv_mods['wis']
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    # Ataque de la bestia
    dmg = random.randint(1, 10) + max(adv_mods['str'], adv_mods['wis'])
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🐻 {caster.name} usa Forma Salvaje, recuperando vigor ({heal_amount} HP) y desgarrando a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="circulo_druidico", name="Círculo Druídico", skill_type="SESSION", req_level=3, allowed_classes=["DRD"]
)
def circulo_druidico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 60 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌱 {caster.name} recurre al conocimiento milenario de su Círculo Druídico para revitalizar al grupo."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(1, 6) + caster.get_stat_modifiers()['wis']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} absorbe la magia natural ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="paso_forestal", name="Paso Forestal", skill_type="SESSION", req_level=4, allowed_classes=["DRD"]
)
def paso_forestal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 50 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🍃 Con su Paso Forestal, {caster.name} guía al grupo con seguridad a través de un denso matorral de espinas ponzoñosas."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(2, 6) + caster.get_stat_modifiers()['wis']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} llega ileso ({heal_amount} HP de daño evitado)."})
    return True

@SkillRegistry.register(
    skill_id="comunion_tierra", name="Comunión con la Tierra", skill_type="SESSION", req_level=5, allowed_classes=["DRD"]
)
def comunion_tierra(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if caster.current_hp <= (caster.max_hp * 0.5) else 0

    if caster.current_hp < caster.max_hp:
        heal_amount = random.randint(5, 20) + caster.get_stat_modifiers()['wis'] * 3
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🌍 {caster.name} entra en Comunión con la Tierra descansando descalzo sobre el suelo, regenerando velozmente {heal_amount} HP."})
        return True
    return False

@SkillRegistry.register(
    skill_id="formas_legendarias", name="Formas Legendarias", skill_type="COMBAT", req_level=6, allowed_classes=["DRD"]
)
def formas_legendarias(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 10) for _ in range(3)) + caster.get_stat_modifiers()['wis'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🐅 Gracias a sus Formas Legendarias, el ataque de {caster.name} ignora por completo la armadura de [bold red]{target['name']}[/bold red] ({dmg} daño mágico)."})
    return True

@SkillRegistry.register(
    skill_id="piel_roble", name="Piel de Roble Natural", skill_type="SESSION", req_level=7, allowed_classes=["DRD"]
)
def piel_roble(context):
    caster = context['caster']
    if context.get('eval_mode'):
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.4)]
        return 65 if critical_allies else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.4)]
    if critical_allies:
        target = random.choice(critical_allies)
        heal_amount = random.randint(4, 12) + caster.get_stat_modifiers()['wis'] * 2
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target.id, "amount": heal_amount,
                               "message": f"🛡️ {caster.name} extiende su Piel de Roble Natural para proteger a {target.name} de las inclemencias del camino (amortigua {heal_amount} HP de desgaste)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="vuelo_halcon", name="Vuelo de Halcón", skill_type="COMBAT", req_level=8, allowed_classes=["DRD"]
)
def vuelo_halcon(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 12) for _ in range(3)) + caster.get_stat_modifiers()['wis']
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🦅 {caster.name} usa Forma Salvaje: Vuelo de Halcón, cayendo en picado sobre [bold red]{target['name']}[/bold red] y destrozándolo con sus garras ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="transmutacion_ambiental", name="Transmutación Ambiental", skill_type="COMBAT", req_level=9, allowed_classes=["DRD"]
)
def transmutacion_ambiental(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if len(context['enemies']) >= 2 else 45

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌪️ {caster.name} realiza una Transmutación Ambiental violenta. ¡La sala se llena de ráfagas heladas y relámpagos!"})
    
    for target in context['enemies']:
        dmg = sum(random.randint(1, 6) for _ in range(3)) + caster.get_stat_modifiers()['wis'] # 3d6
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 🌩️ [bold red]{target['name']}[/bold red] es electrocutado por {dmg} de daño elemental."})
    return True

@SkillRegistry.register(
    skill_id="inmunidad_naturaleza", name="Inmunidad de la Naturaleza", skill_type="SESSION", req_level=10, allowed_classes=["DRD"]
)
def inmunidad_naturaleza(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if any(s in status_list for s in ['PSN', 'BRN', 'BLD']):
                return 100
        return 0

    cleansed = False
    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]
        if bad_status:
            cleansed = True
            for s in bad_status:
                adv_status[adv.id].remove(s)
            
            heal_amount = random.randint(5, 15) + caster.get_stat_modifiers()['wis'] * 3
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"🌿 Su Inmunidad de la Naturaleza exuda una fragancia purificadora, erradicando todas las toxinas de {adv.name} y restaurando {heal_amount} HP."})
    return cleansed

# ==========================================
# RANGER SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="enemigo_favorecido", name="Enemigo Favorecido", skill_type="SESSION", req_level=1, allowed_classes=["RGR"]
)
def enemigo_favorecido(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 45

    coins = random.randint(3, 8) * 5 # 15 a 40 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🐾 Al rastrear los restos de su Enemigo Favorecido, {caster.name} extrae trofeos invaluables (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="estilo_combate", name="Estilo de Combate", skill_type="COMBAT", req_level=2, allowed_classes=["RGR"]
)
def estilo_combate(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if context['enemies'] else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    dmg = random.randint(2, 12) + max(adv_mods['dex'], adv_mods['str']) * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🏹 {caster.name} aplica su Estilo de Combate, asestando un golpe preciso y letal a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="conciencia_primal", name="Conciencia Primal", skill_type="SESSION", req_level=3, allowed_classes=["RGR"]
)
def conciencia_primal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 60 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"👁️ La Conciencia Primal de {caster.name} le alerta de aberraciones cercanas, permitiendo al grupo rodear el peligro."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(1, 6) + caster.get_stat_modifiers()['wis']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} evita un desgaste innecesario ({heal_amount} HP preservados)."})
    return True

@SkillRegistry.register(
    skill_id="superviviente_frontera", name="Superviviente de la Frontera", skill_type="SESSION", req_level=4, allowed_classes=["RGR"]
)
def superviviente_frontera(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🏕️ Como Superviviente de la Frontera, {caster.name} encuentra el único sendero seguro en el pantano."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(2, 8) + caster.get_stat_modifiers()['wis'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} avanza sin agotarse ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="ataque_extra_rgr", name="Ataque Extra (Cazador)", skill_type="COMBAT", req_level=5, allowed_classes=["RGR"]
)
def ataque_extra_rgr(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 8) for _ in range(4)) + max(caster.get_stat_modifiers()['dex'], caster.get_stat_modifiers()['str']) * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚔️ {caster.name} se mueve como una sombra y realiza un Ataque Extra. Dos impactos letales conectan contra [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="explorador_tierras", name="Explorador de Tierras", skill_type="SESSION", req_level=6, allowed_classes=["RGR"]
)
def explorador_tierras(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if any(s in status_list for s in ['PSN', 'BRN', 'BLD']):
                return 80
        return 0

    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        bad_status = [s for s in status_list if s in ['PSN', 'BRN', 'BLD']]
        if bad_status:
            for s in bad_status:
                adv_status[adv.id].remove(s)
            
            heal_amount = random.randint(1, 10) + caster.get_stat_modifiers()['wis']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"🌿 Como Explorador de Tierras, {caster.name} aplica antídotos naturales, limpiando los estados de {adv.name} y curándole {heal_amount} HP."})
            return True
    return False

@SkillRegistry.register(
    skill_id="tactica_defensiva", name="Táctica Defensiva", skill_type="COMBAT", req_level=7, allowed_classes=["RGR"]
)
def tactica_defensiva(context):
    caster = context['caster']
    if context.get('eval_mode'):
        critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
        return 85 if critical_allies and context['enemies'] else 0

    critical_allies = [a for a in context['allies'] if a.current_hp <= (a.max_hp * 0.25)]
    if critical_allies and context['enemies']:
        target_ally = random.choice(critical_allies)
        target_enemy = random.choice(context['enemies'])
        
        heal_amount = max(5, random.randint(5, 15) + caster.get_stat_modifiers()['dex'] * 2)
        dmg = random.randint(1, 12) + caster.get_stat_modifiers()['dex']
        
        target_enemy['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": target_ally.id, "amount": heal_amount,
                               "message": f"🛡️ ¡Táctica Defensiva! {caster.name} distrae a los enemigos, permitiendo que {target_ally.name} respire ({heal_amount} HP recuperados)..."})
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 🏹 ...y en el proceso, dispara de vuelta a [bold red]{target_enemy['name']}[/bold red] por {dmg} daño."})
        return True
    return False

@SkillRegistry.register(
    skill_id="camuflaje_campo", name="Camuflaje de Campo", skill_type="SESSION", req_level=8, allowed_classes=["RGR"]
)
def camuflaje_campo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 # Drop de ítem garantizado, siempre prioridad máxima.

    from .models import Item, ItemRarity
    items_db = list(Item.objects.filter(rarity__in=['COM', 'UNC']))
    if items_db:
        drop_item = random.choice(items_db)
        context['log'].append({"second": context['current_second'], "type": "item_loot", "item_id": drop_item.id, "adventurer_id": caster.id,
                               "message": f"🥷 Usando Camuflaje de Campo, {caster.name} saquea el campamento de unos monstruos dormidos: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🥷 {caster.name} se camufla y acecha, pero el terreno está vacío."})
    return True

@SkillRegistry.register(
    skill_id="flecha_rastreo", name="Flecha de Rastreo", skill_type="COMBAT", req_level=9, allowed_classes=["RGR"]
)
def flecha_rastreo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 10) for _ in range(5)) + max(caster.get_stat_modifiers()['dex'], caster.get_stat_modifiers()['wis']) * 3
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎯 {caster.name} marca el punto débil con una Flecha de Rastreo. ¡Un impacto ineludible desgarra a [bold red]{target['name']}[/bold red] ({dmg} daño)!"})
    return True

@SkillRegistry.register(
    skill_id="desvanecerse", name="Desvanecerse", skill_type="COMBAT", req_level=10, allowed_classes=["RGR"]
)
def desvanecerse(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if context['enemies'] else 0

    if not context['enemies']: return False
    
    adv_mods = caster.get_stat_modifiers()
    target = random.choice(context['enemies'])
    
    dmg = random.randint(10, 50) + adv_mods['dex'] * 4
    heal_amount = random.randint(10, 30) + adv_mods['wis'] * 2
    
    target['hp'] -= dmg
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌫️ {caster.name} utiliza Desvanecerse para volverse indetectable en las sombras."})
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"    -> 🗡️ Asesta un golpe catastrófico desde el sigilo a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> 🛡️ Estando oculto, recupera la calma y sana sus heridas ({heal_amount} HP recuperados)."})
    return True

# ==========================================
# FIGHTER SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="fuerzas_flaqueza", name="Fuerzas de Flaqueza", skill_type="COMBAT", req_level=1, allowed_classes=["FTR"]
)
def fuerzas_flaqueza(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if caster.current_hp <= (caster.max_hp * 0.4) else 0

    if caster.current_hp <= (caster.max_hp * 0.4):
        heal_amount = random.randint(1, 10) + caster.level
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🩸 {caster.name} saca Fuerzas de Flaqueza en pleno combate, regenerando velozmente {heal_amount} HP."})
        return True
    return False

@SkillRegistry.register(
    skill_id="oleada_accion", name="Oleada de Acción", skill_type="COMBAT", req_level=2, allowed_classes=["FTR"]
)
def oleada_accion(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if context['enemies'] else 0

    if not context['enemies']: return False
    
    target = random.choice(context['enemies'])
    adv_mods = caster.get_stat_modifiers()
    
    dmg = sum(random.randint(1, 10) for _ in range(2)) + adv_mods['str'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚔️ {caster.name} rompe sus límites con una Oleada de Acción, asestando dos golpes devastadores a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="arquetipo_marcial", name="Arquetipo Marcial", skill_type="SESSION", req_level=3, allowed_classes=["FTR"]
)
def arquetipo_marcial(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 60 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⛺ Usando su Arquetipo Marcial, {caster.name} fortifica el campamento, previniendo emboscadas tácticas."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(1, 8) + caster.get_stat_modifiers()['con']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} descansa seguro ({heal_amount} HP preservados)."})
    return True

@SkillRegistry.register(
    skill_id="postura_firme", name="Postura Firme", skill_type="SESSION", req_level=4, allowed_classes=["FTR"]
)
def postura_firme(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 50 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ {caster.name} adopta una Postura Firme, anclándose para proteger al grupo de un derrumbe inesperado."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(2, 6) + caster.get_stat_modifiers()['str']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} esquiva las rocas ({heal_amount} HP de daño ambiental evitado)."})
    return True

@SkillRegistry.register(
    skill_id="ataque_extra_ftr", name="Ataque Extra (Guerrero)", skill_type="COMBAT", req_level=5, allowed_classes=["FTR"]
)
def ataque_extra_ftr(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 10) for _ in range(3)) + caster.get_stat_modifiers()['str'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🗡️ {caster.name} encadena ataques con maestría pura, destrozando a [bold red]{target['name']}[/bold red] ({dmg} daño físico)."})
    return True

@SkillRegistry.register(
    skill_id="entrenamiento_fisico", name="Entrenamiento Físico Absoluto", skill_type="SESSION", req_level=6, allowed_classes=["FTR"]
)
def entrenamiento_fisico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 45

    coins = random.randint(5, 12) * 5 # 25 a 60 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🧗‍♂️ Con su Entrenamiento Físico Absoluto, {caster.name} escala un foso imposible y recupera un botín atrapado (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="guardia_agresiva", name="Guardia Agresiva", skill_type="COMBAT", req_level=7, allowed_classes=["FTR"]
)
def guardia_agresiva(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    adv_mods = caster.get_stat_modifiers()
    heal_amount = max(5, random.randint(5, 15) + adv_mods['con'])
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    dmg = random.randint(5, 15) + adv_mods['str'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ ¡Guardia Agresiva! {caster.name} bloquea el embate y contraataca con su escudo a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> 🩹 El desvío perfecto evita desgaste futuro ({heal_amount} HP amortiguados)."})
    return True

@SkillRegistry.register(
    skill_id="recarga_marcial", name="Recarga Marcial", skill_type="SESSION", req_level=8, allowed_classes=["FTR"]
)
def recarga_marcial(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if caster.current_hp <= (caster.max_hp * 0.5) else 0

    if caster.current_hp < caster.max_hp:
        heal_amount = random.randint(10, 30) + caster.get_stat_modifiers()['con'] * 3
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"⚔️ {caster.name} realiza una Recarga Marcial. Afila sus armas, estira sus músculos y recupera {heal_amount} HP, listo para la guerra."})
        return True
    return False

@SkillRegistry.register(
    skill_id="indomable", name="Indomable", skill_type="COMBAT", req_level=9, allowed_classes=["FTR"]
)
def indomable(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 if caster.current_hp <= (caster.max_hp * 0.2) else 0

    if caster.current_hp <= (caster.max_hp * 0.2):
        heal_amount = random.randint(20, 50) + caster.get_stat_modifiers()['con'] * 4
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🔥 ¡Indomable! A un paso de la muerte, la voluntad de {caster.name} rechaza el fracaso. (Curación in extremis: {heal_amount} HP)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="estilo_critico", name="Estilo Crítico", skill_type="COMBAT", req_level=10, allowed_classes=["FTR"]
)
def estilo_critico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = (sum(random.randint(1, 12) for _ in range(4)) + caster.get_stat_modifiers()['str'] * 4) * 2 # Daño masivo crítico
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💥 ¡Estilo Crítico! {caster.name} encuentra el punto ciego absoluto de [bold red]{target['name']}[/bold red] y desata un golpe letal ({dmg} DAÑO CRÍTICO)."})
    return True

# ==========================================
# SORCERER SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="origen_arcano", name="Origen Arcano", skill_type="SESSION", req_level=1, allowed_classes=["SOR"]
)
def origen_arcano(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 60 if caster.current_hp < caster.max_hp else 0

    if caster.current_hp < caster.max_hp:
        heal_amount = random.randint(2, 6) + caster.get_stat_modifiers()['cha']
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🐉 Las escamas místicas del Origen Arcano de {caster.name} endurecen su piel, curando su desgaste ({heal_amount} HP)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="fuente_magia", name="Fuente de Magia", skill_type="COMBAT", req_level=2, allowed_classes=["SOR"]
)
def fuente_magia(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(2, 12) + caster.get_stat_modifiers()['cha'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✨ {caster.name} convierte su propia esencia en una Fuente de Magia, calcinando a [bold red]{target['name']}[/bold red] por {dmg} daño."})
    return True

@SkillRegistry.register(
    skill_id="metamagia_basica", name="Metamagia (Conjuro Gemelo)", skill_type="COMBAT", req_level=3, allowed_classes=["SOR"]
)
def metamagia_basica(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if len(context['enemies']) >= 2 else 50

    if not context['enemies']: return False
    
    # Intenta seleccionar dos objetivos distintos si hay más de 1
    targets = random.sample(context['enemies'], min(2, len(context['enemies'])))
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔮 {caster.name} retuerce la magia usando Conjuro Gemelo:"})
                           
    for target in targets:
        dmg = random.randint(2, 10) + caster.get_stat_modifiers()['cha']
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> ⚡ Un rayo arcano impacta a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="flujo_estable", name="Flujo Estable", skill_type="SESSION", req_level=4, allowed_classes=["SOR"]
)
def flujo_estable(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 45

    coins = random.randint(4, 10) * 5 # 20 a 50 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🌌 Su Flujo Estable estabiliza la magia volátil de la sala, revelando un tesoro de plata pura (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="sobrecarga_arcana", name="Sobrecarga Arcana", skill_type="COMBAT", req_level=5, allowed_classes=["SOR"]
)
def sobrecarga_arcana(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 8) for _ in range(4)) + caster.get_stat_modifiers()['cha'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💥 {caster.name} impone una Sobrecarga Arcana, forzando a [bold red]{target['name']}[/bold red] a recibir el impacto pleno y crítico de su conjuro ({dmg} daño mágico)."})
    return True

@SkillRegistry.register(
    skill_id="corazon_origen", name="Corazón del Origen", skill_type="SESSION", req_level=6, allowed_classes=["SOR"]
)
def corazon_origen(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if 'BRN' in status_list:
                return 80
        return 0

    cleansed = False
    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        if 'BRN' in status_list:
            cleansed = True
            adv_status[adv.id].remove('BRN')
            
            heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['cha'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"🔥 El Corazón del Origen de {caster.name} absorbe las llamas que consumían a {adv.name}, sanándole {heal_amount} HP."})
    return cleansed

@SkillRegistry.register(
    skill_id="escudo_espejismo", name="Escudo de Espejismo", skill_type="COMBAT", req_level=7, allowed_classes=["SOR"]
)
def escudo_espejismo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if caster.current_hp <= (caster.max_hp * 0.5) else 0

    if caster.current_hp <= (caster.max_hp * 0.5):
        heal_amount = random.randint(15, 30) + caster.get_stat_modifiers()['cha'] * 3
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🪞 ¡Escudo de Espejismo! {caster.name} se fragmenta en ilusiones, evadiendo ataques mortales (Mitiga/Cura {heal_amount} HP)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="intuicion_conjuro", name="Intuición de Conjuro", skill_type="SESSION", req_level=8, allowed_classes=["SOR"]
)
def intuicion_conjuro(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 100 # Item Drop garantizado

    from .models import Item, ItemRarity
    items_db = list(Item.objects.filter(rarity__in=['COM', 'UNC']))
    if items_db:
        drop_item = random.choice(items_db)
        context['log'].append({"second": context['current_second'], "type": "item_loot", "item_id": drop_item.id, "adventurer_id": caster.id,
                               "message": f"🔮 Su Intuición de Conjuro le permite identificar mágicamente los remanentes de un artefacto enterrado: [[{ItemRarity.get_color(drop_item.rarity)}]{drop_item.name}[/]]"})
    else:
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"🔮 {caster.name} intenta identificar un objeto mágico, pero no encuentra nada estable en esta zona."})
    return True

@SkillRegistry.register(
    skill_id="transfusion_sangre", name="Transfusión de Sangre", skill_type="COMBAT", req_level=9, allowed_classes=["SOR"]
)
def transfusion_sangre(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if context['enemies'] and caster.current_hp > (caster.max_hp * 0.3) else 0

    if not context['enemies'] or caster.current_hp <= (caster.max_hp * 0.3): return False
    
    # Pierde HP para infligir daño colosal a todos
    hp_cost = max(1, int(caster.current_hp * 0.15))
    caster.current_hp -= hp_cost
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🩸 {caster.name} sacrifica su propia vitalidad ({hp_cost} HP) en una Transfusión de Sangre para potenciar su poder destructivo."})
    
    for target in context['enemies']:
        dmg = sum(random.randint(1, 12) for _ in range(4)) + caster.get_stat_modifiers()['cha'] * 3
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💀 [bold red]{target['name']}[/bold red] es bombardeado por magia de sangre ({dmg} daño oscuro)."})
    return True

@SkillRegistry.register(
    skill_id="metamagia_avanzada", name="Metamagia Avanzada", skill_type="COMBAT", req_level=10, allowed_classes=["SOR"]
)
def metamagia_avanzada(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if context['enemies'] else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌠 {caster.name} desata la Metamagia Avanzada: Conjuro Potenciado + Conjuro Cuidadoso."})
    
    # Daño a todos los enemigos
    for target in context['enemies']:
        dmg = sum(random.randint(1, 10) for _ in range(5)) + caster.get_stat_modifiers()['cha'] * 4
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> ☄️ [bold red]{target['name']}[/bold red] recibe el infierno metamágico ({dmg} daño devastador)."})
    
    # Curación pasiva a los aliados por la energía residual curativa ("Cuidadoso")
    for adv in context['allies']:
        heal_amount = random.randint(5, 15) + caster.get_stat_modifiers()['cha']
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                               "message": f"    -> 🛡️ La magia cuidadosamente esquiva a {adv.name}, dándole energía ({heal_amount} HP recuperados)."})
    return True

# ==========================================
# WIZARD SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="proyectil_magico", name="Proyectil Mágico", skill_type="COMBAT", req_level=1, allowed_classes=["WIZ"]
)
def proyectil_magico(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if context['enemies'] else 0

    if not context['enemies']: return False
    
    # 3 dardos mágicos. Puede impactar al mismo o distintos.
    targets = [random.choice(context['enemies']) for _ in range(3)]
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🪄 {caster.name} conjura Proyectil Mágico, lanzando 3 dardos de fuerza ineludibles:"})
                           
    for i, target in enumerate(targets):
        dmg = random.randint(2, 5) + caster.get_stat_modifiers()['int']
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💫 El dardo {i+1} impacta a [bold red]{target['name']}[/bold red] de lleno ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="tradicion_arcana", name="Tradición Arcana", skill_type="SESSION", req_level=2, allowed_classes=["WIZ"]
)
def tradicion_arcana(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 50

    coins = random.randint(3, 8) * 10 # 30 a 80 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"📚 Gracias a su Tradición Arcana, {caster.name} optimiza los recursos de escriba del grupo, recuperando y ahorrando materiales por valor de {coins} cobres."})
    return True

@SkillRegistry.register(
    skill_id="memorizacion_rapida", name="Memorización Rápida", skill_type="SESSION", req_level=3, allowed_classes=["WIZ"]
)
def memorizacion_rapida(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"📖 Usando su Memorización Rápida, {caster.name} traza velozmente runas de protección sobre el grupo."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(2, 8) + caster.get_stat_modifiers()['int']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> La magia escuda a {adv.name} de las inclemencias ({heal_amount} HP prevenidos/curados)."})
    return True

@SkillRegistry.register(
    skill_id="bola_de_fuego_wiz", name="Bola de Fuego", skill_type="COMBAT", req_level=4, allowed_classes=["WIZ"]
)
def bola_de_fuego_wiz(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if context['enemies'] else 0

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔥 ¡BOLA DE FUEGO! {caster.name} desata una explosión térmica devastadora en toda la sala:"})
                           
    for target in context['enemies']:
        dmg = sum(random.randint(1, 6) for _ in range(8)) + caster.get_stat_modifiers()['int'] * 2
        target['hp'] -= dmg
        
        # Posibilidad de aplicar BRN (Burn) simulado
        burn_msg = ""
        if random.random() < 0.3:
            adv_status = context.get('adv_status', {}) # en este caso no aplica a monstruos permanentemente, solo flavor
            burn_msg = " [red](Quemado)[/red]"
            
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 💥 [bold red]{target['name']}[/bold red] es engullido por las llamas ({dmg} daño){burn_msg}."})
    return True

@SkillRegistry.register(
    skill_id="enfoque_inquebrantable", name="Enfoque Inquebrantable", skill_type="COMBAT", req_level=5, allowed_classes=["WIZ"]
)
def enfoque_inquebrantable(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if caster.current_hp <= (caster.max_hp * 0.4) else 0

    if caster.current_hp <= (caster.max_hp * 0.4):
        heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['con'] * 2
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🧠 {caster.name} mantiene un Enfoque Inquebrantable frente al dolor. La magia residual fortifica su cuerpo ({heal_amount} HP recuperados)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="rasgo_escuela", name="Rasgo de Escuela Especializado", skill_type="COMBAT", req_level=6, allowed_classes=["WIZ"]
)
def rasgo_escuela(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(15, 30) + caster.get_stat_modifiers()['int'] * 3
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎓 {caster.name} demuestra el pináculo de su Escuela de Magia, desintegrando las defensas de [bold red]{target['name']}[/bold red] ({dmg} daño mágico absoluto)."})
    return True

@SkillRegistry.register(
    skill_id="barrera_intelectual", name="Barrera Intelectual", skill_type="SESSION", req_level=7, allowed_classes=["WIZ"]
)
def barrera_intelectual(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 60 if allies_hurt >= 2 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ La Barrera Intelectual de {caster.name} se expande, disipando toxinas mentales y fatiga de la party."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 12) + caster.get_stat_modifiers()['int']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> La mente de {adv.name} se aclara ({heal_amount} HP sanados)."})
    return True

@SkillRegistry.register(
    skill_id="biblioteca_mental", name="Biblioteca Mental", skill_type="SESSION", req_level=8, allowed_classes=["WIZ"]
)
def biblioteca_mental(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 80 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🗺️ Accediendo a su Biblioteca Mental, {caster.name} descifra la arquitectura del calabozo y guía al grupo por rutas seguras."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['int'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} evita trampas mortales gracias al mapa ({heal_amount} HP de daño evitado)."})
    return True

@SkillRegistry.register(
    skill_id="contrahechizo_calculado", name="Contrahechizo Calculado", skill_type="COMBAT", req_level=9, allowed_classes=["WIZ"]
)
def contrahechizo_calculado(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if caster.current_hp <= (caster.max_hp * 0.3) and context['enemies'] else 0

    if not context['enemies'] or caster.current_hp > (caster.max_hp * 0.3): return False
    target = random.choice(context['enemies'])
    
    heal_amount = random.randint(20, 40) + caster.get_stat_modifiers()['int'] * 3
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    dmg = heal_amount // 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛑 ¡Contrahechizo Calculado! {caster.name} anula un ataque letal, absorbiendo su energía (Mitiga {heal_amount} HP) y redirigiéndola como un latigazo a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="impulso_grimorio", name="Impulso de Grimorio", skill_type="COMBAT", req_level=10, allowed_classes=["WIZ"]
)
def impulso_grimorio(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if context['enemies'] else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"📜 {caster.name} desata el Impulso de Grimorio. Rompiendo las leyes de la magia, lanza una ráfaga incesante de conjuros:"})
                           
    for target in context['enemies']:
        dmg = sum(random.randint(1, 10) for _ in range(6)) + caster.get_stat_modifiers()['int'] * 4
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 🌠 Tormenta arcana impacta a [bold red]{target['name']}[/bold red] sin piedad ({dmg} daño masivo)."})
    return True

# ==========================================
# MONK SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="defensa_sin_armadura", name="Defensa sin Armadura", skill_type="SESSION", req_level=1, allowed_classes=["MNK"]
)
def defensa_sin_armadura(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 65 if caster.current_hp < caster.max_hp else 0

    if caster.current_hp < caster.max_hp:
        heal_amount = random.randint(2, 6) + caster.get_stat_modifiers()['dex']
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🥋 Su Defensa sin Armadura y agilidad zen previenen un gran desgaste físico ({heal_amount} HP preservados)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="flujo_de_ki", name="Flujo de Ki", skill_type="COMBAT", req_level=2, allowed_classes=["MNK"]
)
def flujo_de_ki(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(2, 10) + caster.get_stat_modifiers()['dex'] * 2
    target['hp'] -= dmg
    
    heal_amount = max(1, caster.get_stat_modifiers()['wis']) * 2
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💨 {caster.name} fluye con el Ki, asestando golpes ultrarrápidos a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> Inmediatamente adopta una postura esquiva y se retira sin ser golpeado ({heal_amount} HP mitigados/sanados)."})
    return True

@SkillRegistry.register(
    skill_id="deflectar_proyectiles", name="Deflectar Proyectiles", skill_type="COMBAT", req_level=3, allowed_classes=["MNK"]
)
def deflectar_proyectiles(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    heal_amount = random.randint(5, 15) + caster.get_stat_modifiers()['dex']
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    dmg = heal_amount # Devuelve el daño que mitigó
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✋ ¡Reflejo zen! {caster.name} atrapa un proyectil en el aire (Mitiga {heal_amount} HP) y lo devuelve velozmente a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="caida_lenta", name="Caída Lenta", skill_type="SESSION", req_level=4, allowed_classes=["MNK"]
)
def caida_lenta(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🪶 El grupo resbala en un acantilado profundo. {caster.name} usa Caída Lenta, rebotando en las paredes para atrapar y salvar a sus aliados."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 12) + caster.get_stat_modifiers()['dex']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} aterriza de pie suavemente ({heal_amount} HP salvados)."})
    return True

@SkillRegistry.register(
    skill_id="golpe_aturdidor_mnk", name="Golpe Aturdidor", skill_type="COMBAT", req_level=5, allowed_classes=["MNK"]
)
def golpe_aturdidor_mnk(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(5, 15) + caster.get_stat_modifiers()['dex'] * 2
    target['hp'] -= dmg
    
    heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['wis'] * 2
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚡ {caster.name} asesta un Golpe Aturdidor certero. [bold red]{target['name']}[/bold red] recibe ({dmg} daño) y queda completamente paralizado."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> 🛡️ La parálisis enemiga previene letalidad inminente al grupo ({heal_amount} HP mitigados pasivamente)."})
    return True

@SkillRegistry.register(
    skill_id="ataques_ki", name="Ataques de Ki Mágicos", skill_type="COMBAT", req_level=6, allowed_classes=["MNK"]
)
def ataques_ki(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = sum(random.randint(1, 10) for _ in range(3)) + caster.get_stat_modifiers()['wis'] * 3
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"👊 Sus puños brillan con pura energía espiritual. {caster.name} desata Ataques de Ki Mágicos, ignorando resistencias de [bold red]{target['name']}[/bold red] ({dmg} daño absoluto)."})
    return True

@SkillRegistry.register(
    skill_id="evasion_absoluta", name="Evasión Absoluta", skill_type="COMBAT", req_level=7, allowed_classes=["MNK"]
)
def evasion_absoluta(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if caster.current_hp <= (caster.max_hp * 0.3) else 0

    if caster.current_hp <= (caster.max_hp * 0.3):
        heal_amount = random.randint(30, 50) + caster.get_stat_modifiers()['dex'] * 4
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🌫️ ¡Evasión Absoluta! El ataque de área iba a ser mortal, pero {caster.name} se mueve más rápido que la luz (Esquiva impecable: {heal_amount} HP curados/evitados)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="mente_serena", name="Mente Serena", skill_type="SESSION", req_level=8, allowed_classes=["MNK"]
)
def mente_serena(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 75 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🧘 Mediante su Mente Serena, {caster.name} disipa los terrores invisibles y la fatiga del equipo en absoluto silencio."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['wis'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} halla la paz mental ({heal_amount} HP restaurados)."})
    return True

@SkillRegistry.register(
    skill_id="movimiento_sin_limites", name="Movimiento sin Límites", skill_type="SESSION", req_level=9, allowed_classes=["MNK"]
)
def movimiento_sin_limites(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80

    coins = random.randint(8, 15) * 10 # 80 a 150 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🏃‍♂️ Desafiando la gravedad con su Movimiento sin Límites, {caster.name} corre por una cascada vertical y hurta un tesoro intocable (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="pureza_cuerpo", name="Pureza de Cuerpo", skill_type="SESSION", req_level=10, allowed_classes=["MNK"]
)
def pureza_cuerpo(context):
    caster = context['caster']
    adv_status = context.get('adv_status', {})
    
    if context.get('eval_mode'):
        for status_list in adv_status.values():
            if 'PSN' in status_list:
                return 95
        return 40 if caster.current_hp < caster.max_hp else 0

    cleansed = False
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🧬 El metabolismo inmaculado de {caster.name} exuda una Pureza de Cuerpo sobrehumana."})

    for adv in context['allies']:
        status_list = adv_status.get(adv.id, [])
        if 'PSN' in status_list:
            cleansed = True
            adv_status[adv.id].remove('PSN')
            heal_amount = random.randint(15, 30) + caster.get_stat_modifiers()['con'] * 3
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> 🧪 Su tacto expulsa el veneno letal de {adv.name} y purifica la sangre ({heal_amount} HP curados)."})
                                   
    if caster.current_hp < caster.max_hp and not cleansed:
         heal_amount = random.randint(20, 50) + caster.get_stat_modifiers()['con'] * 4
         caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
         context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                                "message": f"    -> 🌱 Su propio cuerpo rechaza toda enfermedad pasivamente, regenerándose ({heal_amount} HP sanados)."})
         cleansed = True

    return cleansed

# ==========================================
# PALADIN SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="imposicion_manos_pal", name="Imposición de Manos", skill_type="SESSION", req_level=1, allowed_classes=["PAL"]
)
def imposicion_manos_pal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 75 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"✨ {caster.name} extiende su mano y canaliza una curación sagrada hacia los heridos."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 10) + caster.level * 5
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} se baña en luz divina ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="castigo_divino_pal", name="Castigo Divino", skill_type="COMBAT", req_level=2, allowed_classes=["PAL"]
)
def castigo_divino_pal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(15, 30) + caster.get_stat_modifiers()['str'] * 2 + caster.get_stat_modifiers()['cha'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"☀️ ¡CASTIGO DIVINO! {caster.name} golpea con su arma imbuida en luz sagrada, destrozando a [bold red]{target['name']}[/bold red] ({dmg} daño radiante)."})
    return True

@SkillRegistry.register(
    skill_id="juramento_sagrado", name="Juramento Sagrado", skill_type="SESSION", req_level=3, allowed_classes=["PAL"]
)
def juramento_sagrado(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ Guiado por su Juramento Sagrado, {caster.name} protege a sus compañeros de los peligros del entorno."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(4, 12) + caster.get_stat_modifiers()['cha']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> Su devoción salvaguarda a {adv.name} ({heal_amount} HP preservados)."})
    return True

@SkillRegistry.register(
    skill_id="sentido_divino", name="Sentido Divino", skill_type="SESSION", req_level=4, allowed_classes=["PAL"]
)
def sentido_divino(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85

    coins = random.randint(5, 10) * 10 # 50 a 100 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"👁️ Con su Sentido Divino, {caster.name} detecta la magia oscura oculta, evadiendo una emboscada y reclamando un alijo macabro (+{coins} cobres)."})
    
    # Curación pasiva por la fatiga evitada
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 15)
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} se libra del horror oculto ({heal_amount} HP de daño prevenido)."})
    return True

@SkillRegistry.register(
    skill_id="ataque_extra_pal", name="Ataque Extra", skill_type="COMBAT", req_level=5, allowed_classes=["PAL"]
)
def ataque_extra_pal(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if context['enemies'] else 0

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"⚔️ El celo sagrado de {caster.name} le permite realizar un Ataque Extra implacable:"})
                           
    for i in range(2):
        if not context['enemies']: break
        target = random.choice(context['enemies'])
        dmg = random.randint(8, 20) + caster.get_stat_modifiers()['str'] * 2
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> 🗡️ Golpe {i+1}: Impacta a [bold red]{target['name']}[/bold red] ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="aura_proteccion", name="Aura de Protección", skill_type="COMBAT", req_level=6, allowed_classes=["PAL"]
)
def aura_proteccion(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if any(a.current_hp < a.max_hp * 0.4 for a in context['allies']) else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🛡️ El Aura de Protección de {caster.name} brilla intensamente, mitigando los golpes enemigos."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp * 0.4:
            heal_amount = random.randint(15, 30) + caster.get_stat_modifiers()['cha'] * 2
            adv.current_hp = min(adv.max_hp, adv.current_hp + heal_amount)
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> La luz rechaza la letalidad sobre {adv.name} ({heal_amount} HP curados/prevenidos)."})
    return True

@SkillRegistry.register(
    skill_id="aura_subclase", name="Aura de Subclase", skill_type="COMBAT", req_level=7, allowed_classes=["PAL"]
)
def aura_subclase(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔥 El Aura de Subclase de {caster.name} emana llamas de conquista, purificando a los monstruos cercanos."})
                           
    for target in context['enemies']:
        dmg = random.randint(5, 15) + caster.get_stat_modifiers()['cha'] * 2
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> [bold red]{target['name']}[/bold red] sufre en presencia del Paladín ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="castigo_firme", name="Castigo Firme", skill_type="COMBAT", req_level=8, allowed_classes=["PAL"]
)
def castigo_firme(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if caster.current_hp < caster.max_hp * 0.5 else 0

    if caster.current_hp < caster.max_hp * 0.5:
        heal_amount = random.randint(20, 40) + caster.get_stat_modifiers()['cha'] * 3
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🛐 Castigo Firme: {caster.name} retiene su fervor y lo canaliza en autosanación absoluta ({heal_amount} HP restaurados)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="voluntad_hierro", name="Voluntad de Hierro", skill_type="SESSION", req_level=9, allowed_classes=["PAL"]
)
def voluntad_hierro(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 80 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🧠 La Voluntad de Hierro de {caster.name} purga cualquier manipulación mental o estrés acumulado en la party."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(15, 30) + caster.get_stat_modifiers()['cha'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> La psique de {adv.name} se vuelve irrompible ({heal_amount} HP sanados)."})
    return True

@SkillRegistry.register(
    skill_id="aura_coraje", name="Aura de Coraje", skill_type="SESSION", req_level=10, allowed_classes=["PAL"]
)
def aura_coraje(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 95 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🦁 ¡AURA DE CORAJE! La simple presencia de {caster.name} disipa el terror de las sombras, inspirando un valor absoluto."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(30, 60) + caster.get_stat_modifiers()['cha'] * 4
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} siente cómo el miedo abandona su cuerpo y sus heridas cierran milagrosamente ({heal_amount} HP curados)."})
    return True

# ==========================================
# ROGUE SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="ataque_furtivo", name="Ataque Furtivo", skill_type="COMBAT", req_level=1, allowed_classes=["ROG"]
)
def ataque_furtivo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 75 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(10, 20) + caster.get_stat_modifiers()['dex'] * 3
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🗡️ ¡ATAQUE FURTIVO! Aprovechando un punto ciego, {caster.name} apuñala brutalmente a [bold red]{target['name']}[/bold red] ({dmg} daño crítico)."})
    return True

@SkillRegistry.register(
    skill_id="accion_astuta_rog", name="Acción Astuta", skill_type="COMBAT", req_level=2, allowed_classes=["ROG"]
)
def accion_astuta_rog(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 70 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(5, 12) + caster.get_stat_modifiers()['dex']
    target['hp'] -= dmg
    
    heal_amount = random.randint(5, 15) + caster.get_stat_modifiers()['dex'] * 2
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💨 {caster.name} golpea rápido a [bold red]{target['name']}[/bold red] ({dmg} daño) y usa su Acción Astuta para retirarse de la línea enemiga."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> 🛡️ La maniobra esquiva confunde a los enemigos, previniendo sus contraataques ({heal_amount} HP mitigados pasivamente)."})
    return True

@SkillRegistry.register(
    skill_id="arquetipo_picaro", name="Arquetipo de Pícaro", skill_type="SESSION", req_level=3, allowed_classes=["ROG"]
)
def arquetipo_picaro(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80

    coins = random.randint(5, 15) * 10 # 50 a 150 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🎭 Usando las artes de su Arquetipo de Pícaro, {caster.name} saquea cofres ocultos que la party había ignorado (+{coins} cobres)."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(3, 8) + caster.get_stat_modifiers()['dex']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> Consigue suministros médicos extra ({heal_amount} HP sanados para {adv.name})."})
    return True

@SkillRegistry.register(
    skill_id="pies_ligeros", name="Pies Ligeros", skill_type="SESSION", req_level=4, allowed_classes=["ROG"]
)
def pies_ligeros(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 75 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🐾 Con Pies Ligeros, {caster.name} guía a la party por un pasillo plagado de trampas invisibles y terreno peligroso."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 15) + caster.get_stat_modifiers()['dex'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} sortea una trampa mortal ({heal_amount} HP de letalidad evitada)."})
    return True

@SkillRegistry.register(
    skill_id="esquiva_asombrosa", name="Esquiva Asombrosa", skill_type="COMBAT", req_level=5, allowed_classes=["ROG"]
)
def esquiva_asombrosa(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if caster.current_hp < caster.max_hp * 0.5 else 0

    if caster.current_hp < caster.max_hp * 0.5:
        heal_amount = random.randint(20, 35) + caster.get_stat_modifiers()['dex'] * 3
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🛡️ ¡Esquiva Asombrosa! {caster.name} fue golpeado salvajemente, pero dobla su cuerpo a último segundo para dividir el impacto a la mitad ({heal_amount} HP recuperados)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="pericia_duplicada", name="Pericia Duplicada", skill_type="SESSION", req_level=6, allowed_classes=["ROG"]
)
def pericia_duplicada(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90

    coins = random.randint(15, 30) * 10 # 150 a 300 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🔎 Aplicando su Pericia Duplicada en Juego de Manos, {caster.name} desmonta una caja fuerte inexpugnable y se hace de oro masivo (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="evasion_rogue", name="Evasión", skill_type="COMBAT", req_level=7, allowed_classes=["ROG"]
)
def evasion_rogue(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if caster.current_hp < caster.max_hp * 0.4 else 0

    if caster.current_hp < caster.max_hp * 0.4:
        heal_amount = random.randint(30, 50) + caster.get_stat_modifiers()['dex'] * 4
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🌫️ ¡EVASIÓN PERFECTA! El aliento destructivo del enemigo iba a incinerarlo, pero {caster.name} no sufre ni un rasguño ({heal_amount} HP de letalidad evadida in-extremis)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="golpe_sucio", name="Golpe Sucio", skill_type="COMBAT", req_level=8, allowed_classes=["ROG"]
)
def golpe_sucio(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(15, 30) + caster.get_stat_modifiers()['dex'] * 2
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🩸 ¡Golpe Sucio! {caster.name} le arroja ácido a los ojos a [bold red]{target['name']}[/bold red] y lo apuñala ({dmg} daño). El monstruo queda CEGADO."})
                           
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(10, 20) + caster.get_stat_modifiers()['dex'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> El enemigo falla desesperadamente contra {adv.name} por la ceguera ({heal_amount} HP de daño enemigo prevenido)."})
    return True

@SkillRegistry.register(
    skill_id="infiltrado_supremo", name="Infiltrado Supremo", skill_type="SESSION", req_level=9, allowed_classes=["ROG"]
)
def infiltrado_supremo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 85 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🎭 Como un Infiltrado Supremo, {caster.name} provee a todo el gremio de uniformes enemigos y salvoconductos falsificados, evadiendo ejércitos enteros."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(25, 40) + caster.get_stat_modifiers()['int'] * 3
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> {adv.name} se ahorra colosales niveles de daño y fatiga al caminar tranquilamente ({heal_amount} HP prevenidos)."})
    return True

@SkillRegistry.register(
    skill_id="mente_escurridiza", name="Mente Escurridiza", skill_type="SESSION", req_level=10, allowed_classes=["ROG"]
)
def mente_escurridiza(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 95 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🧠 La Mente Escurridiza de {caster.name} es impermeable al control mental. Disipa los terrores invisibles de la sala como si no fueran nada."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(30, 50) + caster.get_stat_modifiers()['wis'] * 3
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> La cordura de {adv.name} es restaurada a través de trucos psicológicos ({heal_amount} HP curados)."})
    return True

# ==========================================
# WARLOCK SKILLS
# ==========================================

@SkillRegistry.register(
    skill_id="patron_pacto", name="Patrón del Pacto", skill_type="SESSION", req_level=1, allowed_classes=["WLK"]
)
def patron_pacto(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 75 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"👁️‍🗨️ {caster.name} susurra al vacío. Su Patrón del Pacto responde, otorgando favores oscuros a la party a cambio de su cordura."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(5, 12) + caster.get_stat_modifiers()['cha']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> Sombras envuelven a {adv.name}, cerrando sus heridas sobrenaturalmente ({heal_amount} HP recuperados)."})
    return True

@SkillRegistry.register(
    skill_id="invocaciones_eldritch", name="Invocaciones Eldritch", skill_type="COMBAT", req_level=2, allowed_classes=["WLK"]
)
def invocaciones_eldritch(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] else 0

    if not context['enemies']: return False
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌌 ¡ELDRITCH BLAST! {caster.name} canaliza sus Invocaciones Eldritch, desatando múltiples rayos de fuerza abisal:"})
                           
    for i in range(2):
        if not context['enemies']: break
        target = random.choice(context['enemies'])
        dmg = random.randint(8, 15) + caster.get_stat_modifiers()['cha'] * 2
        target['hp'] -= dmg
        context['log'].append({"second": context['current_second'], "type": "flavor",
                               "message": f"    -> ☄️ Rayo {i+1} impacta a [bold red]{target['name']}[/bold red] de lleno ({dmg} daño)."})
    return True

@SkillRegistry.register(
    skill_id="regalo_pacto", name="Regalo del Pacto", skill_type="SESSION", req_level=3, allowed_classes=["WLK"]
)
def regalo_pacto(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 65 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"📖 El Regalo del Pacto de {caster.name} revela un camino seguro mediante presagios demoníacos, guiando al grupo por el abismo."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(4, 10) + caster.get_stat_modifiers()['cha']
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> Evita el letal peligro inminente para {adv.name} ({heal_amount} HP preservados)."})
    return True

@SkillRegistry.register(
    skill_id="mirada_penetrante", name="Mirada Penetrante", skill_type="SESSION", req_level=4, allowed_classes=["WLK"]
)
def mirada_penetrante(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85

    coins = random.randint(8, 20) * 10 # 80 a 200 cobres
    context['log'].append({"second": context['current_second'], "type": "loot", "amount": coins,
                           "message": f"🧿 Los ojos de {caster.name} arden con la Mirada Penetrante, destrozando ilusiones mágicas y hallando un enorme tesoro oscuro (+{coins} cobres)."})
    return True

@SkillRegistry.register(
    skill_id="magia_pacto_aumentada", name="Magia de Pacto Aumentada", skill_type="COMBAT", req_level=5, allowed_classes=["WLK"]
)
def magia_pacto_aumentada(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if context['enemies'] else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(20, 40) + caster.get_stat_modifiers()['cha'] * 4
    target['hp'] -= dmg
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🔥 ¡Magia de Pacto Aumentada a Nivel 3! {caster.name} desgarra la realidad y engulle a [bold red]{target['name']}[/bold red] en fuego infernal ({dmg} daño absoluto ignorando defensas)."})
    return True

@SkillRegistry.register(
    skill_id="escape_defensivo", name="Escape Defensivo", skill_type="COMBAT", req_level=6, allowed_classes=["WLK"]
)
def escape_defensivo(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 90 if caster.current_hp < caster.max_hp * 0.4 else 0

    if caster.current_hp < caster.max_hp * 0.4:
        heal_amount = random.randint(25, 40) + caster.get_stat_modifiers()['cha'] * 3
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"💨 ¡Escape Defensivo! Acorralado, {caster.name} se vuelve invisible de repente y se teletransporta, salvando su vida milagrosamente ({heal_amount} HP recuperados de un golpe mortal)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="velo_sombras", name="Velo de Sombras", skill_type="COMBAT", req_level=7, allowed_classes=["WLK"]
)
def velo_sombras(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 85 if caster.current_hp < caster.max_hp * 0.3 else 0

    if caster.current_hp < caster.max_hp * 0.3:
        heal_amount = random.randint(30, 50) + caster.get_stat_modifiers()['cha'] * 4
        caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
        context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                               "message": f"🌫️ Sumergiéndose en el Velo de Sombras, {caster.name} se vuelve inalcanzable. El ataque enemigo lo atraviesa como si fuera neblina ({heal_amount} HP de daño prevenido al máximo)."})
        return True
    return False

@SkillRegistry.register(
    skill_id="absorcion_almas", name="Absorción de Almas", skill_type="COMBAT", req_level=8, allowed_classes=["WLK"]
)
def absorcion_almas(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 80 if context['enemies'] and caster.current_hp < caster.max_hp else 0

    if not context['enemies']: return False
    target = random.choice(context['enemies'])
    
    dmg = random.randint(15, 30) + caster.get_stat_modifiers()['cha'] * 2
    target['hp'] -= dmg
    
    heal_amount = caster.level * 2 + caster.get_stat_modifiers()['cha'] * 3
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"💀 {caster.name} masacra a [bold red]{target['name']}[/bold red] ({dmg} daño) y ejerce su Absorción de Almas arrancándole su fuerza vital."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> 🩸 El Brujo consume la esencia, ganando vitalidad oscura ({heal_amount} HP restaurados como vida temporal)."})
    return True

@SkillRegistry.register(
    skill_id="trance_vacio", name="Trance del Vacío", skill_type="SESSION", req_level=9, allowed_classes=["WLK"]
)
def trance_vacio(context):
    caster = context['caster']
    if context.get('eval_mode'):
        allies_hurt = sum(1 for a in context['allies'] if a.current_hp < a.max_hp)
        return 85 if allies_hurt >= 1 else 0

    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🌌 Entrando en el Trance del Vacío, {caster.name} se comunica con entidades superiores (El DM) obteniendo secretos prohibidos sobre la mazmorra."})
    
    for adv in context['allies']:
        if adv.current_hp < adv.max_hp:
            heal_amount = random.randint(25, 45) + caster.get_stat_modifiers()['int'] * 2 + caster.get_stat_modifiers()['wis'] * 2
            context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": adv.id, "amount": heal_amount,
                                   "message": f"    -> El atajo revelado evita toda una legión de monstruos ({heal_amount} HP de letalidad masiva evitada por {adv.name})."})
    return True

@SkillRegistry.register(
    skill_id="resiliencia_entidad", name="Resiliencia de la Entidad", skill_type="SESSION", req_level=10, allowed_classes=["WLK"]
)
def resiliencia_entidad(context):
    caster = context['caster']
    if context.get('eval_mode'):
        return 95 if caster.current_hp < caster.max_hp else 0

    heal_amount = random.randint(40, 80) + caster.get_stat_modifiers()['cha'] * 5
    caster.current_hp = min(caster.max_hp, caster.current_hp + heal_amount)
    
    context['log'].append({"second": context['current_second'], "type": "flavor",
                           "message": f"🧟 Su cuerpo es apenas humano. Mediante la Resiliencia de la Entidad, {caster.name} muta pasivamente para ignorar el daño ambiental extremo."})
    context['log'].append({"second": context['current_second'], "type": "heal", "adventurer_id": caster.id, "amount": heal_amount,
                           "message": f"    -> Las células oscuras suturan por completo cualquier mutilación letal ({heal_amount} HP recuperados)."})
    return True
