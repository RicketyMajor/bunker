from django.db import models
from django.utils import timezone


class AdventurerClass(models.TextChoices):
    # Clases de Dungeons & Dragons
    ARTIFICER = 'ART', 'Artificer'
    BARBARIAN = 'BBN', 'Barbarian'
    BARD = 'BRD', 'Bard'
    CLERIC = 'CLR', 'Cleric'
    DRUID = 'DRD', 'Druid'
    FIGHTER = 'FTR', 'Fighter'
    MONK = 'MNK', 'Monk'
    PALADIN = 'PAL', 'Paladin'
    RANGER = 'RGR', 'Ranger'
    ROGUE = 'ROG', 'Rogue'
    SORCERER = 'SOR', 'Sorcerer'
    WARLOCK = 'WLK', 'Warlock'
    WIZARD = 'WIZ', 'Wizard'


class AdventurerRace(models.TextChoices):
    # Razas de Dungeons & Dragons
    HUMAN = 'HUM', 'Human'
    DWARF = 'DWF', 'Dwarf'
    ELF = 'ELF', 'Elf'
    HALFLING = 'HLF', 'Halfling'
    GNOME = 'GNM', 'Gnome'
    HALF_ELF = 'HEF', 'Half-Elf'
    HALF_ORC = 'HOC', 'Half-Orc'
    DRAGONBORN = 'DGB', 'Dragonborn'
    TIEFLING = 'TIE', 'Tiefling'


class AdventurerGender(models.TextChoices):
    # Géneros para los aventureros
    MALE = 'M', 'Masculino'
    FEMALE = 'F', 'Femenino'
    OTHER = 'O', 'Otro / Misterioso'


class ItemType(models.TextChoices):
    WEAPON_1H = 'W1H', 'Arma (1 Mano)'
    WEAPON_2H = 'W2H', 'Arma (2 Manos)'
    OFFHAND = 'OFF', 'Secundaria / Escudo'
    HEAD = 'HED', 'Cabeza'
    TORSO = 'TRS', 'Torso'
    LEGS = 'LGS', 'Piernas'
    HANDS = 'HND', 'Manos'
    FEET = 'FET', 'Pies'
    NECKLACE = 'NCK', 'Collar'
    RING = 'RNG', 'Anillo'
    BRACELET = 'BRC', 'Brazalete'
    EARRING = 'EAR', 'Aretes'
    CONSUMABLE = 'CNS', 'Consumible'
    MISC = 'MSC', 'Misceláneo'


class ItemRarity(models.TextChoices):
    COMMON = 'COM', 'Común'
    UNCOMMON = 'UNC', 'Poco Común'
    RARE = 'RAR', 'Raro'
    EPIC = 'EPC', 'Épico'
    LEGENDARY = 'LEG', 'Legendario'

    @classmethod
    def get_color(cls, rarity):
        """Devuelve la etiqueta de color Rich de Textual para los logs y la interfaz."""
        colors = {
            cls.COMMON: 'gray',
            cls.UNCOMMON: 'bold green',
            cls.RARE: 'bold blue',
            cls.EPIC: 'bold magenta',
            cls.LEGENDARY: 'bold yellow'
        }
        return colors.get(rarity, 'white')


class ArmorWeight(models.TextChoices):
    NONE = 'NON', 'Sin Armadura'
    LIGHT = 'LGT', 'Ligera'
    MEDIUM = 'MED', 'Media'
    HEAVY = 'HVY', 'Pesada'


class WeaponType(models.TextChoices):
    NONE = 'NON', 'No es arma'
    SLASHING = 'SLS', 'Cortante'
    PIERCING = 'PRC', 'Perforante'
    BLUDGEONING = 'BLD', 'Contundente'
    MAGICAL = 'MAG', 'Mágica / Foco'


class Material(models.TextChoices):
    METAL = 'MTL', 'Metal'
    BONE = 'BNE', 'Hueso'
    WOOD = 'WOD', 'Madera'
    DARKWOOD = 'DW', 'Madera Oscura'
    LEATHER = 'LTH', 'Cuero'
    CLOTH = 'CLT', 'Tela'
    ADAMANTINE = 'ADM', 'Adamantio'
    MITHRAL = 'MTH', 'Mithril'
    SILVER = 'SLV', 'Plata'
    MIXED = 'MIX', 'Mixto'


class OnHitEffect(models.TextChoices):
    """Efectos que se aplican al golpear (DoTs, debuffs, curación vampírica, etc.)"""
    NONE = 'NON', 'Sin Efecto'
    POISON = 'PSN', 'Envenenar (Daño por turno)'
    BLEED = 'BLD', 'Sangrar (Daño por turno)'
    BURN = 'BRN', 'Quemar (Daño por turno)'
    STUN = 'STN', 'Aturdir (Pierde el turno)'
    BLIND = 'BLN', 'Cegar (Desventaja al atacar)'
    LIFESTEAL = 'LFS', 'Drenar Vida (Cura al usuario)'
    THORNS = 'THN', 'Pinchos (Daño de represalia al ser golpeado)'


class ItemConsumableType(models.TextChoices):
    """Categorías para los objetos que pueden ser consumidos."""
    NONE = 'NON', 'No es consumible'
    HEAL = 'HEL', 'Poción de Curación (HP)'
    MANA = 'MAN', 'Poción de Energía (Recurso)'
    FLAVOR = 'FLV', 'Inmersión (Raciones, Cuerdas, etc.)'


class CostMixin(models.Model):
    """Modelo abstracto para definir precios complejos con el sistema de 11 monedas."""
    cost_iron_half_penny = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Medio penique de hierro")
    cost_iron_penny = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Penique de hierro")
    cost_ardite = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Ardite")
    cost_drabin = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Drabín")
    cost_copper_penny = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Penique de cobre")
    cost_iota = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Iota")
    cost_silver_penny = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Penique de plata")
    cost_sueldo = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Sueldo")
    cost_talento = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Talento")
    cost_real = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Real")
    cost_marco = models.PositiveIntegerField(
        default=0, verbose_name="Coste: Marco")

    class Meta:
        abstract = True


class Item(CostMixin):
    """Representa un objeto en el mundo. ¡Úsalo como plantilla para tus Excel!"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=3, choices=ItemType.choices)
    rarity = models.CharField(
        max_length=3, choices=ItemRarity.choices, default=ItemRarity.COMMON)
    armor_weight = models.CharField(
        max_length=3, choices=ArmorWeight.choices, default=ArmorWeight.NONE)
    weapon_type = models.CharField(
        max_length=3, choices=WeaponType.choices, default=WeaponType.NONE)
    material = models.CharField(
        max_length=3, choices=Material.choices, default=Material.MIXED)

    # Modificadores de Combate Base (Armas)
    damage_dice_count = models.PositiveIntegerField(
        default=0, help_text="Dados del arma base (Ej: 1)")
    damage_dice_sides = models.PositiveIntegerField(
        default=0, help_text="Caras del arma base (Ej: 6)")

    # Modificadores Extra Dinámicos (Magia / Anillos / Runas)
    bonus_damage_dice_count = models.PositiveIntegerField(
        default=0, help_text="Dados extra de daño mágico (Ej: 1)")
    bonus_damage_dice_sides = models.PositiveIntegerField(
        default=0, help_text="Caras del dado extra mágico (Ej: 4)")
    bonus_damage = models.PositiveIntegerField(
        default=0, help_text="Daño Plano garantizado adicional")
    bonus_armor = models.PositiveIntegerField(
        default=0, help_text="Suma a la Armadura")

    # Sistema de Efectos Alterados (Procs)
    on_hit_effect = models.CharField(
        max_length=3, choices=OnHitEffect.choices, default=OnHitEffect.NONE)
    effect_chance = models.PositiveIntegerField(
        default=0, help_text="Probabilidad 1-100 de aplicar el efecto")
    effect_dice_count = models.PositiveIntegerField(
        default=1, help_text="Cantidad de dados para el efecto (Ej: 1)")
    effect_dice_sides = models.PositiveIntegerField(
        default=4, help_text="Caras del dado del efecto (Ej: 6)")

    # --- SISTEMA DE CONSUMIBLES ---
    consumable_type = models.CharField(
        max_length=3, choices=ItemConsumableType.choices, default=ItemConsumableType.NONE)
    consumable_amount = models.PositiveIntegerField(
        default=0, help_text="Cantidad que cura o restaura")

    # Modificadores de Atributos RPG
    bonus_str = models.IntegerField(default=0, verbose_name="Fuerza")
    bonus_dex = models.IntegerField(default=0, verbose_name="Destreza")
    bonus_con = models.IntegerField(default=0, verbose_name="Constitución")
    bonus_int = models.IntegerField(default=0, verbose_name="Inteligencia")
    bonus_wis = models.IntegerField(default=0, verbose_name="Sabiduría")
    bonus_cha = models.IntegerField(default=0, verbose_name="Carisma")
    bonus_luk = models.IntegerField(default=0, verbose_name="Suerte")

    def __str__(self):
        return f"{self.name} [{self.get_rarity_display()}]"


class InventorySlot(models.Model):
    """Mochila Infinita: Relación entre un objeto y su dueño (Aventurero o Gremio)."""
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    # Si pertenece a un aventurero, este campo se llena. Si es del cofre, queda nulo.
    adventurer = models.ForeignKey(
        'Adventurer', on_delete=models.CASCADE, null=True, blank=True, related_name='inventory')

    # Si pertenece al cofre del gremio, este campo se llena.
    guild = models.ForeignKey('GuildProfile', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='vault_inventory')

    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        owner = self.adventurer.name if self.adventurer else "Cofre del Gremio"
        return f"{self.quantity}x {self.item.name} ({owner})"


class WealthMixin(models.Model):
    """Modelo abstracto que otorga la economía completa de la Mancomunidad a cualquier entidad."""
    iron_half_penny = models.PositiveIntegerField(
        default=0, verbose_name="Medio penique de hierro")
    iron_penny = models.PositiveIntegerField(
        default=0, verbose_name="Penique de hierro")
    ardite = models.PositiveIntegerField(default=0, verbose_name="Ardite")
    drabin = models.PositiveIntegerField(default=0, verbose_name="Drabín")

    copper_penny = models.PositiveIntegerField(
        default=0, verbose_name="Penique de cobre")
    iota = models.PositiveIntegerField(default=0, verbose_name="Iota")

    silver_penny = models.PositiveIntegerField(
        default=0, verbose_name="Penique de plata")
    sueldo = models.PositiveIntegerField(default=0, verbose_name="Sueldo")
    talento = models.PositiveIntegerField(default=0, verbose_name="Talento")

    real = models.PositiveIntegerField(default=0, verbose_name="Real")
    marco = models.PositiveIntegerField(default=0, verbose_name="Marco")

    class Meta:
        abstract = True


class Adventurer(WealthMixin):
    name = models.CharField(max_length=100)
    adv_class = models.CharField(max_length=3, choices=AdventurerClass.choices)
    race = models.CharField(max_length=3, choices=AdventurerRace.choices)
    gender = models.CharField(
        max_length=1, choices=AdventurerGender.choices, default='O')

    # --- ESTADÍSTICAS BASE ---
    base_str = models.PositiveIntegerField(default=1, verbose_name="Fuerza")
    base_dex = models.PositiveIntegerField(default=1, verbose_name="Destreza")
    base_con = models.PositiveIntegerField(
        default=1, verbose_name="Constitución")
    base_int = models.PositiveIntegerField(
        default=1, verbose_name="Inteligencia")
    base_wis = models.PositiveIntegerField(default=1, verbose_name="Sabiduría")
    base_cha = models.PositiveIntegerField(default=1, verbose_name="Carisma")
    base_luk = models.PositiveIntegerField(default=1, verbose_name="Suerte")

    # --- VIDA ---
    max_hp = models.PositiveIntegerField(default=20)
    current_hp = models.IntegerField(default=20)

    # --- INVENTARIO GRANULAR ---
    equip_head = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_head')
    equip_torso = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_torso')
    equip_legs = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_legs')
    equip_hands = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_hands')
    equip_feet = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_feet')
    equip_necklace = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_necklace')
    equip_ring_1 = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_ring_1')
    equip_ring_2 = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_ring_2')
    equip_bracelet = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_bracelet')
    equip_earring = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_earring')
    equip_main_hand = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_main')
    equip_off_hand = models.ForeignKey(
        Item, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipped_off')

    # --- Límite de Mochila ---
    @property
    def inventory_capacity(self):
        """Calcula la capacidad dinámicamente consultando el árbol de mejoras."""
        base_capacity = 10
        guild = GuildProfile.objects.first()
        if guild and guild.unlocked_upgrades.filter(upgrade__key='mochila_lv2').exists():
            return 15  # Capacidad expandida por mejora del gremio
        return base_capacity

    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)

    # --- REPUTACIÓN Y HAZAÑAS ---
    sessions_survived = models.PositiveIntegerField(default=0)
    monsters_killed = models.PositiveIntegerField(default=0)

    @property
    def reputation_title(self):
        """Retorna el título de reputación basado en las hazañas del aventurero."""
        if self.sessions_survived >= 100 or self.monsters_killed >= 500:
            return "Leyenda"
        if self.sessions_survived >= 60 or self.monsters_killed >= 300:
            return "Héroe"
        if self.sessions_survived >= 30 or self.monsters_killed >= 100:
            return "Veterano"
        if self.sessions_survived >= 10 or self.monsters_killed >= 20:
            return "Aventurero"
        return "Novato"

    # --- GRIMORIO ---
    session_skills_used = models.JSONField(
        default=list, blank=True, help_text="Habilidades de Sesión ya utilizadas.")
    combat_skills_used = models.JSONField(
        default=list, blank=True, help_text="Habilidades de Combate ya utilizadas.")

    # --- RECURSOS DE CLASE ---
    class_resources = models.JSONField(
        default=dict, blank=True, help_text="Reserva de energía (ej: {'ki': 3, 'spell_slots_1': 2})")

    is_active = models.BooleanField(default=False)
    is_recovering = models.BooleanField(default=False)
    recovery_time_left = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.get_adv_class_display()} (Nv. {self.level})"

    def get_equipped_items(self):
        """Retorna una lista filtrada con los objetos físicos que el personaje lleva puestos."""
        return [i for i in [
            self.equip_head, self.equip_torso, self.equip_legs,
            self.equip_hands, self.equip_feet,
            self.equip_necklace, self.equip_ring_1, self.equip_ring_2,
            self.equip_bracelet, self.equip_earring,
            self.equip_main_hand, self.equip_off_hand
        ] if i is not None]

    def get_stat_modifiers(self):

        mods = {'str': 0, 'dex': 0, 'con': 0, 'int': 0, 'wis': 0, 'cha': 0, 'luk': 0,
                'armor': 0, 'damage': 2, 'weapon_dice_count': 0, 'weapon_dice_sides': 0,
                'bonus_dmg_dice_count': 0, 'bonus_dmg_dice_sides': 0,
                'on_hit_effect': 'NON', 'effect_chance': 0, 'effect_dice_count': 1, 'effect_dice_sides': 4}

        # Modificadores de Raza
        race_mods = {
            'HUM': {'str': 1, 'dex': 1, 'con': 1, 'int': 1, 'wis': 1, 'cha': 1, 'luk': 1},
            'DWF': {'con': 2, 'str': 2},
            'ELF': {'dex': 2, 'int': 1, 'wis': 1},
            'HLF': {'dex': 2, 'cha': 1, 'luk': 1},
            'GNM': {'int': 2, 'con': 1},
            'HEF': {'cha': 2, 'dex': 1, 'int': 1},
            'HOC': {'str': 2, 'con': 1},
            'DGB': {'str': 2, 'cha': 1},
            'TIE': {'cha': 2, 'int': 1},
        }

        # Modificadores de Clase
        class_mods = {
            'ART': {'int': 2}, 'BBN': {'str': 2, 'con': 1}, 'BRD': {'cha': 2},
            'CLR': {'wis': 2}, 'DRD': {'wis': 2, 'int': 1}, 'FTR': {'str': 2, 'dex': 1},
            'MNK': {'dex': 2, 'wis': 1}, 'PAL': {'str': 2, 'cha': 1}, 'RGR': {'dex': 2, 'wis': 1},
            'ROG': {'dex': 2, 'luk': 1}, 'SOR': {'cha': 2, 'luk': 1}, 'WLK': {'cha': 2},
            'WIZ': {'int': 2, 'wis': 1}
        }

        for stat, val in race_mods.get(self.race, {}).items():
            mods[stat] += val
        for stat, val in class_mods.get(self.adv_class, {}).items():
            mods[stat] += val

        # Modificadores de Equipamiento Físico
        for item in self.get_equipped_items():
            mods['str'] += item.bonus_str
            mods['dex'] += item.bonus_dex
            mods['con'] += item.bonus_con
            mods['int'] += item.bonus_int
            mods['wis'] += item.bonus_wis
            mods['cha'] += item.bonus_cha
            mods['luk'] += item.bonus_luk
            mods['armor'] += item.bonus_armor
            mods['damage'] += item.bonus_damage

            # --- Acumular dados extra y efectos ---
            mods['bonus_dmg_dice_count'] += item.bonus_damage_dice_count
            if item.bonus_damage_dice_sides > mods['bonus_dmg_dice_sides']:
                # Guarda el dado más grande
                mods['bonus_dmg_dice_sides'] = item.bonus_damage_dice_sides

            # Si un arma tiene un efecto, el aventurero lo adquiere para atacar
            if item.on_hit_effect != 'NON' and item.item_type in ['W1H', 'W2H', 'RNG', 'NCK']:
                mods['on_hit_effect'] = item.on_hit_effect
                mods['effect_chance'] = item.effect_chance
                mods['effect_dice_count'] = item.effect_dice_count
                mods['effect_dice_sides'] = item.effect_dice_sides

        # --- LÓGICA DE DEFENSA SIN ARMADURA ---
        is_unarmored = True
        for item in self.get_equipped_items():
            # Si tiene casco, torso, pantalones o escudo que no sean 'NON'
            if item.item_type in ['TRS', 'HED', 'LGS', 'OFF'] and item.armor_weight != 'NON':
                is_unarmored = False

        # Monje: Suma su Sabiduría a la Armadura si está ligero
        if self.adv_class == 'MNK' and is_unarmored:
            mods['armor'] += mods['wis']

        # Bárbaro (Nv 4+): Piel Curtida (+1 CA permanente sin armadura)
        if self.adv_class == 'BBN' and self.level >= 4 and is_unarmored:
            mods['armor'] += 1

        # Si usa arma, quita el daño base desarmado y usa los
        if self.equip_main_hand and self.equip_main_hand.damage_dice_count > 0:
            mods['weapon_dice_count'] = self.equip_main_hand.damage_dice_count
            mods['weapon_dice_sides'] = self.equip_main_hand.damage_dice_sides
            mods['damage'] -= 2

        return mods


class GuildProfile(WealthMixin):
    # --- NUEVO SISTEMA DE PRESTIGIO ---
    prestige_level = models.PositiveIntegerField(default=1)
    # Permite números negativos (Deuda de Honor)
    prestige = models.IntegerField(default=0)

    @property
    def net_worth_in_talents(self):
        total = self.talento + (self.marco * 10) + (self.real * 2.5) + \
            (self.sueldo / 32.0) + (self.iota / 10.0)
        return round(total, 2)

    @property
    def prestige_meta(self):
        return int(500 * (self.prestige_level ** 1.5))

    def add_prestige(self, amount):
        """Añade prestigio y calcula si el gremio sube de nivel (curva exponencial). Retorna True si subió."""
        self.prestige += amount
        leveled_up = False
        while True:
            meta = self.prestige_meta
            if self.prestige >= meta:
                self.prestige -= meta
                self.prestige_level += 1
                leveled_up = True
            else:
                break
        self.save()
        return leveled_up

    def __str__(self):
        return f"Gremio Nivel {self.prestige_level} - Prestigio: {self.prestige}/{self.prestige_meta}"


class DeepWorkSession(models.Model):
    """
    Registra cada sesión del temporizador. Mantiene el historial para dar
    seguimiento a tus hábitos y calcular las recompensas post-sesión.
    """
    start_time = models.DateTimeField(default=timezone.now)
    duration_minutes = models.PositiveIntegerField(
        help_text="Duración objetivo de la sesión en minutos")
    category = models.CharField(
        max_length=100, help_text="Ej: Inglés, Programación, Ayudantía")

    # Participantes de la sesión
    adventurers_involved = models.ManyToManyField(
        Adventurer, related_name='sessions_participated')

    completed = models.BooleanField(
        default=False, help_text="¿Se terminó el tiempo sin cancelar?")

    # Registro narrativo tipo MUD
    event_log = models.JSONField(
        default=list, blank=True, help_text="Historial de eventos ocurridos en esta sesión")

    def __str__(self):
        status = "Completada" if self.completed else "Incompleta/En progreso"
        return f"[{self.category}] {self.duration_minutes} min - {status}"


class HabitDifficulty(models.TextChoices):
    S = 'S', 'Rango S (Épico)'
    A = 'A', 'Rango A (Difícil)'
    B = 'B', 'Rango B (Medio)'
    C = 'C', 'Rango C (Fácil)'


class DailyHabit(models.Model):
    name = models.CharField(max_length=100)
    difficulty = models.CharField(
        max_length=1, choices=HabitDifficulty.choices, default=HabitDifficulty.C)
    valid_days = models.CharField(max_length=20, default="0,1,2,3,4,5,6")

    # --- Hábito Inverso ---
    is_bad_habit = models.BooleanField(
        default=False, help_text="Si es True, marcarlo es una recaída (castigo).")

    last_completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)
    current_streak = models.PositiveIntegerField(default=0)

    # Fecha de la última evaluación automática de recompensas/penalizaciones
    last_evaluated_date = models.DateField(null=True, blank=True)

    # --- Undo Cache ---
    # Para recuperar la racha al deshacer recaídas
    previous_streak = models.PositiveIntegerField(default=0)
    last_prestige_reward = models.PositiveIntegerField(default=0)
    last_coin_type = models.CharField(max_length=20, blank=True, null=True)
    last_coin_amount = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"[{self.difficulty}] {self.name}"


class DailyStatistic(models.Model):
    """Guarda data agregada por día para alimentar los gráficos de Textual-Plotext."""
    date = models.DateField(unique=True, default=timezone.now)
    deep_work_minutes = models.PositiveIntegerField(default=0)

    screen_time_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Stats {self.date}: {self.deep_work_minutes} min DW"


class MonsterCategory(models.TextChoices):
    SMALL = 'SML', 'Pequeño (15 pts)'
    MEDIUM = 'MED', 'Mediano (25 pts)'
    LARGE = 'LRG', 'Grande (45 pts)'
    EPIC = 'EPC', 'Épico (65 pts)'


class Monster(models.Model):
    """Template para los enemigos. Tú rellenas los básicos, el motor reparte los stats."""
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=3, choices=MonsterCategory.choices)
    rarity = models.CharField(
        max_length=3, choices=ItemRarity.choices, default=ItemRarity.COMMON)

    # Cantidad de monstruos que pueden aparecer en un solo grupo
    min_spawn = models.PositiveIntegerField(default=1)
    max_spawn = models.PositiveIntegerField(default=1)

    # Rango de Salud
    min_hp = models.PositiveIntegerField(default=10)
    max_hp = models.PositiveIntegerField(default=15)

    # Rangos de Atributos RPG
    min_str = models.IntegerField(default=0)
    max_str = models.IntegerField(default=0)
    min_dex = models.IntegerField(default=0)
    max_dex = models.IntegerField(default=0)
    min_con = models.IntegerField(default=0)
    max_con = models.IntegerField(default=0)
    min_int = models.IntegerField(default=0)
    max_int = models.IntegerField(default=0)
    min_wis = models.IntegerField(default=0)
    max_wis = models.IntegerField(default=0)
    min_cha = models.IntegerField(default=0)
    max_cha = models.IntegerField(default=0)
    min_armor = models.IntegerField(default=0)
    max_armor = models.IntegerField(default=0)

    # Daño basado en dados
    damage_dice_count = models.PositiveIntegerField(default=1)
    damage_dice_sides = models.PositiveIntegerField(default=4)

    # Daño Extra Dinámico
    bonus_damage_dice_count = models.PositiveIntegerField(default=0)
    bonus_damage_dice_sides = models.PositiveIntegerField(default=0)
    bonus_damage = models.PositiveIntegerField(default=0)

    # Sistema de Efectos Alterados (Procs)
    on_hit_effect = models.CharField(
        max_length=3, choices=OnHitEffect.choices, default=OnHitEffect.NONE)
    effect_chance = models.PositiveIntegerField(
        default=0, help_text="Probabilidad 1-100 de aplicar el efecto")
    effect_dice_count = models.PositiveIntegerField(
        default=1, help_text="Cantidad de dados para el efecto (Ej: 1)")
    effect_dice_sides = models.PositiveIntegerField(
        default=4, help_text="Caras del dado del efecto (Ej: 6)")

    loot_multiplier = models.FloatField(default=1.0)
    xp_reward = models.PositiveIntegerField(default=50)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"


class ChartPolarity(models.TextChoices):
    POSITIVE = 'POS', 'Positivo (Más alto es mejor)'
    NEGATIVE = 'NEG', 'Negativo (Más bajo es mejor)'


class CustomChart(models.Model):
    """Define la estructura y las reglas de un gráfico personalizable."""
    title = models.CharField(
        max_length=100, help_text="Ej: 'Horas de Deep Work' o 'Tiempo en Pantalla'")
    y_axis_label = models.CharField(
        max_length=50, default="Horas", help_text="Unidad del Eje Y")
    x_axis_label = models.CharField(
        max_length=50, default="Día del Mes", help_text="Unidad del Eje X")

    polarity = models.CharField(
        max_length=3, choices=ChartPolarity.choices, default=ChartPolarity.POSITIVE)

    # --- LÍMITES ABSOLUTOS ---
    x_min = models.FloatField(
        default=1.0, help_text="Inicio del Eje X (Ej: Día 1)")
    goal_x_value = models.PositiveIntegerField(
        default=30, help_text="Fin del Eje X / Meta (Ej: Día 30)")
    y_min = models.FloatField(
        default=0.0, help_text="Suelo del Eje Y (Ej: 0 horas)")
    y_max = models.FloatField(
        default=10.0, help_text="Techo del Eje Y (Ej: 6 horas máximo)")

    # Estado del gráfico
    is_active = models.BooleanField(
        default=True, help_text="Si es False, el gráfico fue reclamado/reiniciado.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gráfico: {self.title} (Rango Y: {self.y_min}-{self.y_max})"


class ChartDataPoint(models.Model):
    """Una coordenada individual (X, Y) dentro de un gráfico específico."""
    chart = models.ForeignKey(
        CustomChart, on_delete=models.CASCADE, related_name='data_points')

    # Coordenadas
    x_value = models.FloatField(help_text="Ej: Día 1, Día 2...")
    y_value = models.FloatField(
        help_text="Ej: 4.5 (representando 4 horas y 30 mins)")

    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Asegura que no haya dos puntos en la misma "X" (por ejemplo, dos registros para el Día 4)
        unique_together = ('chart', 'x_value')
        ordering = ['x_value']

    def __str__(self):
        return f"{self.chart.title}: X={self.x_value}, Y={self.y_value}"


class JournalEntry(models.Model):
    """Registros del Diario de Viaje con timestamps automáticos."""
    content = models.TextField(
        help_text="Pensamiento o registro del aventurero")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Entrada del {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class GuildUpgrade(models.Model):
    """El catálogo de mejoras disponibles en la tienda del Gremio."""
    key = models.CharField(max_length=50, unique=True,
                           help_text="ID interno (ej: mensajeria_arcana)")
    name = models.CharField(max_length=100)
    description = models.TextField()
    cost_coin = models.CharField(
        max_length=20, default='talento', help_text="Moneda requerida")
    cost_amount = models.PositiveIntegerField(default=1)
    req_prestige_level = models.PositiveIntegerField(
        default=1, help_text="Nivel de Gremio requerido")

    def __str__(self):
        return self.name


class GuildUnlockedUpgrade(models.Model):
    """Registro de las mejoras que el Gremio ya ha comprado."""
    guild = models.ForeignKey(
        GuildProfile, on_delete=models.CASCADE, related_name='unlocked_upgrades')
    upgrade = models.ForeignKey(GuildUpgrade, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('guild', 'upgrade')

    def __str__(self):
        return f"{self.guild} -> {self.upgrade.name}"


# --- SISTEMA KANBAN ---

class KanbanBoard(models.Model):
    """Un tablero Kanban personalizable."""
    name = models.CharField(max_length=100, default="Mi Tablero")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class KanbanColumn(models.Model):
    """Una columna del tablero (Por Hacer, Haciendo, Listo, etc.)."""
    board = models.ForeignKey(
        KanbanBoard, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=50)
    position = models.PositiveIntegerField(default=0)
    color = models.CharField(max_length=20, default="cyan")

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.board.name} / {self.title}"


class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'Baja'
    MEDIUM = 'MED', 'Media'
    HIGH = 'HGH', 'Alta'
    CRITICAL = 'CRT', 'Crítica'


class KanbanTask(models.Model):
    """Una tarea individual dentro de una columna."""
    column = models.ForeignKey(
        KanbanColumn, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=3, choices=TaskPriority.choices, default=TaskPriority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Integración RPG
    prestige_reward = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"


# --- SISTEMA DE CALENDARIO ---

class CalendarEvent(models.Model):
    """Un evento o nota en el calendario."""
    date = models.DateField()
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_important = models.BooleanField(default=False)
    color = models.CharField(max_length=20, default="white")
    status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'created_at']

    def __str__(self):
        return f"{self.date} - {self.title}"

