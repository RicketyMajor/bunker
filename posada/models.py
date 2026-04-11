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


class Adventurer(WealthMixin):
    name = models.CharField(max_length=100)
    adv_class = models.CharField(max_length=3, choices=AdventurerClass.choices)
    race = models.CharField(max_length=3, choices=AdventurerRace.choices)

    level = models.PositiveIntegerField(default=1)
    experience = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=False)
    is_recovering = models.BooleanField(default=False)
    recovery_time_left = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.get_adv_class_display()} (Nv. {self.level})"


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
