from django.core.management.base import BaseCommand
from posada.models import Monster


class Command(BaseCommand):
    help = 'Puebla la base de datos con el bestiario de Monstruos.'

    def handle(self, *args, **kwargs):
        # ==========================================
        # BESTIARIO
        # ==========================================

        # --- TEMPLATE MONSTRUO BASE (VERSION FINAL) ---
        # {
        #     "name": "Nombre Monstruo",
        #     "category": "SML|MED|LRG|EPC", # Esto define la Probabilidad de que aparezca (60%, 30%, 8%, 2%) y su Botín.
        #     "min_spawn": 1, "max_spawn": 1,
        #     # --- SALUD Y ATRIBUTOS D&D ---
        #     "min_hp": 8, "max_hp": 12,
        #     "min_str": -1, "max_str": 1, "min_dex": 1, "max_dex": 3,
        #     "min_con": 0, "max_con": 2, "min_int": -2, "max_int": 0,
        #     "min_wis": -1, "max_wis": 1, "min_cha": -2, "max_cha": -1,
        #     "min_armor": 0, "max_armor": 2,
        #     # --- DAÑO BASE ---
        #     "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,
        #     # --- DAÑO EXTRA MAGICO ---
        #     "bonus_damage_dice_count": 0, "bonus_damage_dice_sides": 0,
        #     # --- EFECTOS AL IMPACTAR ---
        #     "on_hit_effect": "NON|PSN|BLD|BRN|STN|BLN|LFS",
        #     "effect_chance": 0, # 1 a 100
        #     "effect_dice_count": 0, "effect_dice_sides": 0, # Dado del efecto
        #     # --- RECOMPENSAS ---
        #     "loot_multiplier": 1.0, "xp_reward": 50
        # }
        BESTIARIO = [
            # 🟢 EJEMPLO 1: Monstruo Pequeño en grupo
            {
                "name": "Goblin Saqueador",
                "category": "SML",  # Pequeño
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 5,  # Aparecen en grupos de 2 a 5
                "base_hp": 8,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,  # Daño 1d4
                "loot_multiplier": 1.0, "xp_reward": 15
            },
            # 🟡 EJEMPLO 2: Monstruo Mediano solo o en pareja
            {
                "name": "Orco Berserker",
                "category": "MED",  # Mediano
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 2,
                "base_hp": 25,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 2,  # Daño 1d8 + 2
                "loot_multiplier": 2.5, "xp_reward": 60
            },
            # 🔴 EJEMPLO 3: Jefe Épico (Siempre solo)
            {
                "name": "Beholder Anciano",
                "category": "EPC",  # Épico
                "rarity": "LEG",
                "min_spawn": 1, "max_spawn": 1,
                "base_hp": 150,
                "damage_dice_count": 3, "damage_dice_sides": 6, "bonus_damage": 5,  # Daño 3d6 + 5
                "loot_multiplier": 10.0, "xp_reward": 500
            },
        ]

        self.stdout.write("Engendrando monstruos en el mundo...")
        creados = 0
        for data in BESTIARIO:
            obj, created = Monster.objects.update_or_create(
                name=data["name"],
                defaults={k: v for k, v in data.items() if k != "name"}
            )
            if created:
                creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'¡Se engendraron {creados} monstruos nuevos!'))
