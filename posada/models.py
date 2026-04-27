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
    allowed_classes = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de códigos (WIZ, BBN, etc.) que pueden usar este item."
    )
    description = models.TextField(blank=True)
    item_type = models.CharField(max_length=3, choices=ItemType.choices)
    rarity = models.CharField(
        max_length=3, choices=ItemRarity.choices, default=ItemRarity.COMMON)

    # Modificadores de Combate
    bonus_damage = models.PositiveIntegerField(
        default=0, help_text="Suma al Daño (Armas)")
    bonus_armor = models.PositiveIntegerField(
        default=0, help_text="Suma a la Armadura (Ropa/Escudos)")

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

    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=False)
    is_recovering = models.BooleanField(default=False)
    recovery_time_left = models.PositiveIntegerField(default=0)
    fatigue_stacks = models.PositiveIntegerField(
        default=0, help_text="Cada stack resta -1 a todos los stats.")

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
        """Calcula los bonos genéticos (Raza/Clase) y del equipamiento."""
        mods = {'str': 0, 'dex': 0, 'con': 0, 'int': 0, 'wis': 0,
                'cha': 0, 'luk': 0, 'armor': 0, 'damage': 0}

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

        if self.fatigue_stacks > 0:
            for stat in ['str', 'dex', 'con', 'int', 'wis', 'cha', 'luk']:
                mods[stat] -= self.fatigue_stacks

        return mods


class GuildProfile(WealthMixin):
    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)

    @property
    def net_worth_in_talents(self):
        """Calcula el valor neto aproximado de toda la bóveda expresado en Talentos."""
        total = self.talento
        total += self.marco * 10
        total += self.real * 2.5
        total += self.sueldo / 32.0
        total += self.iota / 10.0
        return round(total, 2)

    def __str__(self):
        return f"Gremio Nivel {self.level} - XP: {self.experience}"


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
    S = 'S', 'Rango S (Épico - Mucha XP)'
    A = 'A', 'Rango A (Difícil)'
    B = 'B', 'Rango B (Medio)'
    C = 'C', 'Rango C (Fácil - Poca XP)'


class DailyHabit(models.Model):
    """Hábitos de la vida real que el usuario debe marcar diariamente."""
    name = models.CharField(max_length=100)
    difficulty = models.CharField(
        max_length=1, choices=HabitDifficulty.choices, default=HabitDifficulty.C)

    # Compara esto con la fecha de hoy.
    last_completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateField(auto_now_add=True)

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

    # Valores base que tú definirás en tu Excel
    base_hp = models.PositiveIntegerField(default=10)
    base_damage = models.PositiveIntegerField(default=2)

    # Recompensas (Multiplicadores de botín al morir)
    loot_multiplier = models.FloatField(default=1.0)
    xp_reward = models.PositiveIntegerField(default=50)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"
