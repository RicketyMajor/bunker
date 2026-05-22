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
