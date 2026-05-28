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
            # ==========================================
            # 🟢 ENEMIGOS PEQUEÑOS (TIER 1 / RANGO SML)
            # ==========================================
            {
                "name": "Goblin",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 5, "max_hp": 12,
                "min_str": -1, "max_str": 0, "min_dex": 1, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -1, "max_int": 0,
                "min_wis": -1, "max_wis": 0, "min_cha": -2, "max_cha": -1,
                "min_armor": 0, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 1,
                "loot_multiplier": 1.0, "xp_reward": 15
            },
            {
                "name": "Kobold",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 3, "max_spawn": 6,
                "min_hp": 3, "max_hp": 8,
                "min_str": -2, "max_str": -1, "min_dex": 1, "max_dex": 3,
                "min_con": -1, "max_con": 0, "min_int": -1, "max_int": 0,
                "min_wis": -1, "max_wis": 0, "min_cha": -1, "max_cha": 0,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 1,
                "loot_multiplier": 0.8, "xp_reward": 10
            },
            {
                "name": "Rata Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 5,
                "min_hp": 4, "max_hp": 9,
                "min_str": -1, "max_str": 0, "min_dex": 1, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -3, "max_cha": -2,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 1,
                "on_hit_effect": "PSN", "effect_chance": 15, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.5, "xp_reward": 15
            },
            {
                "name": "Bandido Novato",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 9, "max_hp": 15,
                "min_str": 0, "max_str": 1, "min_dex": 0, "max_dex": 2,
                "min_con": 0, "max_con": 1, "min_int": -1, "max_int": 1,
                "min_wis": -1, "max_wis": 1, "min_cha": -1, "max_cha": 1,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "loot_multiplier": 2.0, "xp_reward": 25
            },
            {
                "name": "Esqueleto",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 10, "max_hp": 16,
                "min_str": 0, "max_str": 1, "min_dex": 1, "max_dex": 2,
                "min_con": 1, "max_con": 2, "min_int": -2, "max_int": -1,
                "min_wis": -1, "max_wis": 0, "min_cha": -2, "max_cha": -1,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "loot_multiplier": 0.8, "xp_reward": 20
            },
            {
                "name": "Zombi",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 15, "max_hp": 25,
                "min_str": 1, "max_str": 2, "min_dex": -2, "max_dex": -1,
                "min_con": 2, "max_con": 3, "min_int": -4, "max_int": -3,
                "min_wis": -2, "max_wis": -1, "min_cha": -3, "max_cha": -2,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "loot_multiplier": 0.8, "xp_reward": 25
            },
            {
                "name": "Lobo",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 8, "max_hp": 15,
                "min_str": 0, "max_str": 1, "min_dex": 1, "max_dex": 2,
                "min_con": 0, "max_con": 1, "min_int": -3, "max_int": -2,
                "min_wis": 0, "max_wis": 1, "min_cha": -2, "max_cha": -1,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "on_hit_effect": "BLD", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.5, "xp_reward": 25
            },
            {
                "name": "Araña Lobo Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 9, "max_hp": 16,
                "min_str": 0, "max_str": 1, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -3, "max_cha": -2,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "on_hit_effect": "PSN", "effect_chance": 30, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.6, "xp_reward": 30
            },
            {
                "name": "Imp",
                "category": "SML",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 10, "max_hp": 15,
                "min_str": -2, "max_str": -1, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": 0, "max_int": 1,
                "min_wis": 0, "max_wis": 1, "min_cha": 1, "max_cha": 2,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 2,
                "on_hit_effect": "PSN", "effect_chance": 35, "effect_dice_count": 2, "effect_dice_sides": 4,
                "loot_multiplier": 2.0, "xp_reward": 40
            },
            {
                "name": "Duende (Sprite)",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 2, "max_hp": 5,
                "min_str": -3, "max_str": -2, "min_dex": 3, "max_dex": 4,
                "min_con": -1, "max_con": 0, "min_int": 1, "max_int": 2,
                "min_wis": 1, "max_wis": 2, "min_cha": 0, "max_cha": 1,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,
                "loot_multiplier": 1.5, "xp_reward": 10
            },
            {
                "name": "Pseudodragón",
                "category": "SML",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 5, "max_hp": 10,
                "min_str": -2, "max_str": -1, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -1, "max_int": 0,
                "min_wis": 1, "max_wis": 2, "min_cha": 0, "max_cha": 1,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 2,
                "on_hit_effect": "PSN", "effect_chance": 25, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 2.5, "xp_reward": 35
            },
            {
                "name": "Lémure",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 10, "max_hp": 18,
                "min_str": 0, "max_str": 1, "min_dex": -3, "max_dex": -2,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": -2, "max_wis": -1, "min_cha": -4, "max_cha": -3,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 1,
                "loot_multiplier": 0.5, "xp_reward": 15
            },
            {
                "name": "Ciempiés Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 3, "max_hp": 7,
                "min_str": -3, "max_str": -2, "min_dex": 1, "max_dex": 2,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": -2, "max_wis": -1, "min_cha": -4, "max_cha": -3,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,
                "on_hit_effect": "PSN", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.3, "xp_reward": 15
            },
            {
                "name": "Cangrejo Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 8, "max_hp": 15,
                "min_str": 0, "max_str": 1, "min_dex": 0, "max_dex": 1,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": -1, "max_wis": 0, "min_cha": -4, "max_cha": -3,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "on_hit_effect": "BLD", "effect_chance": 15, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.5, "xp_reward": 20
            },
            {
                "name": "Rana Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 12, "max_hp": 25,
                "min_str": 0, "max_str": 1, "min_dex": 1, "max_dex": 2,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": -1, "max_wis": 0, "min_cha": -4, "max_cha": -3,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "loot_multiplier": 0.4, "xp_reward": 25
            },
            {
                "name": "Serpiente Venenosa",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 2, "max_hp": 5,
                "min_str": -4, "max_str": -3, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -4, "max_cha": -3,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,
                "on_hit_effect": "PSN", "effect_chance": 40, "effect_dice_count": 2, "effect_dice_sides": 4,
                "loot_multiplier": 0.5, "xp_reward": 20
            },
            {
                "name": "Murciélago Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 10, "max_hp": 22,
                "min_str": 1, "max_str": 2, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -3, "max_cha": -2,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "on_hit_effect": "LFS", "effect_chance": 25, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.8, "xp_reward": 25
            },
            {
                "name": "Tejón Gigante",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 10, "max_hp": 18,
                "min_str": 1, "max_str": 2, "min_dex": 0, "max_dex": 1,
                "min_con": 2, "max_con": 3, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -3, "max_cha": -2,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 2,
                "on_hit_effect": "BLD", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.7, "xp_reward": 30
            },
            {
                "name": "Limo Gris",
                "category": "SML",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 18, "max_hp": 28,
                "min_str": 1, "max_str": 2, "min_dex": -3, "max_dex": -2,
                "min_con": 2, "max_con": 3, "min_int": -4, "max_int": -3,
                "min_wis": -2, "max_wis": -1, "min_cha": -4, "max_cha": -3,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 1,
                "on_hit_effect": "BRN", "effect_chance": 40, "effect_dice_count": 1, "effect_dice_sides": 6,
                "loot_multiplier": 1.5, "xp_reward": 50
            },
            {
                "name": "Pixie",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 1, "max_hp": 4,
                "min_str": -4, "max_str": -3, "min_dex": 3, "max_dex": 5,
                "min_con": -1, "max_con": 0, "min_int": 0, "max_int": 1,
                "min_wis": 1, "max_wis": 2, "min_cha": 1, "max_cha": 2,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 0,
                "loot_multiplier": 1.5, "xp_reward": 15
            },
            {
                "name": "Enjambre de Ratas",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 20, "max_hp": 30,
                "min_str": -1, "max_str": 0, "min_dex": 1, "max_dex": 2,
                "min_con": 0, "max_con": 1, "min_int": -4, "max_int": -3,
                "min_wis": 0, "max_wis": 1, "min_cha": -3, "max_cha": -2,
                "min_armor": 0, "max_armor": 1,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 0,
                "on_hit_effect": "BLD", "effect_chance": 25, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 0.5, "xp_reward": 40
            },
            {
                "name": "Cultista Raso",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 7, "max_hp": 12,
                "min_str": 0, "max_str": 1, "min_dex": 0, "max_dex": 1,
                "min_con": 0, "max_con": 1, "min_int": 0, "max_int": 1,
                "min_wis": 0, "max_wis": 1, "min_cha": 0, "max_cha": 1,
                "min_armor": 0, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 1,
                "loot_multiplier": 1.5, "xp_reward": 20
            },
            {
                "name": "Svirfneblin (Gnomo de las Profundidades)",
                "category": "SML",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 12, "max_hp": 20,
                "min_str": 1, "max_str": 2, "min_dex": 1, "max_dex": 2,
                "min_con": 1, "max_con": 2, "min_int": 1, "max_int": 2,
                "min_wis": 0, "max_wis": 1, "min_cha": -1, "max_cha": 0,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 2,
                "loot_multiplier": 3.0, "xp_reward": 40
            },
            {
                "name": "Guardia de la Ciudad",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 9, "max_hp": 15,
                "min_str": 1, "max_str": 2, "min_dex": 0, "max_dex": 1,
                "min_con": 1, "max_con": 2, "min_int": 0, "max_int": 1,
                "min_wis": 0, "max_wis": 1, "min_cha": 0, "max_cha": 1,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 1,
                "loot_multiplier": 2.5, "xp_reward": 35
            },
            {
                "name": "Homúnculo",
                "category": "SML",
                "rarity": "COM",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 3, "max_hp": 8,
                "min_str": -3, "max_str": -2, "min_dex": 2, "max_dex": 3,
                "min_con": 0, "max_con": 1, "min_int": 0, "max_int": 1,
                "min_wis": 0, "max_wis": 1, "min_cha": -2, "max_cha": -1,
                "min_armor": 1, "max_armor": 2,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 1,
                "on_hit_effect": "PSN", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 1.2, "xp_reward": 20
            },

            # ==========================================
            # 🟡 ENEMIGOS MEDIANOS (TIER 2 / RANGO MED)
            # ==========================================
            {
                "name": "Orco",
                "category": "MED",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 4,
                "min_hp": 12, "max_hp": 22,
                "min_str": 2, "max_str": 4, "min_dex": 0, "max_dex": 2,
                "min_con": 2, "max_con": 4, "min_int": -1, "max_int": 1,
                "min_wis": 0, "max_wis": 2, "min_cha": -1, "max_cha": 1,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 6,
                "loot_multiplier": 1.5, "xp_reward": 200
            },
            {
                "name": "Hobgoblin",
                "category": "MED",
                "rarity": "UNC",
                "min_spawn": 2, "max_spawn": 6,
                "min_hp": 9, "max_hp": 18,
                "min_str": 1, "max_str": 3, "min_dex": 1, "max_dex": 3,
                "min_con": 1, "max_con": 3, "min_int": 0, "max_int": 2,
                "min_wis": 0, "max_wis": 2, "min_cha": 0, "max_cha": 2,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 4,
                "loot_multiplier": 1.5, "xp_reward": 150
            },
            {
                "name": "Gnoll",
                "category": "MED",
                "rarity": "UNC",
                "min_spawn": 2, "max_spawn": 5,
                "min_hp": 15, "max_hp": 25,
                "min_str": 2, "max_str": 4, "min_dex": 1, "max_dex": 3,
                "min_con": 1, "max_con": 3, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 5,
                "on_hit_effect": "BLD", "effect_chance": 10, "effect_dice_count": 1, "effect_dice_sides": 4,
                "loot_multiplier": 1.8, "xp_reward": 200
            },
            {
                "name": "Bugbear",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 20, "max_hp": 35,
                "min_str": 3, "max_str": 5, "min_dex": 1, "max_dex": 3,
                "min_con": 2, "max_con": 4, "min_int": -1, "max_int": 1,
                "min_wis": 0, "max_wis": 2, "min_cha": -1, "max_cha": 1,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 2, "damage_dice_sides": 4, "bonus_damage": 8,
                "on_hit_effect": "STN", "effect_chance": 10,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Hombre Lobo",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 45, "max_hp": 70,
                "min_str": 4, "max_str": 6, "min_dex": 2, "max_dex": 4,
                "min_con": 3, "max_con": 5, "min_int": 0, "max_int": 2,
                "min_wis": 1, "max_wis": 3, "min_cha": 0, "max_cha": 2,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 8,
                "on_hit_effect": "BLD", "effect_chance": 20, "effect_dice_count": 2, "effect_dice_sides": 4,
                "loot_multiplier": 3.0, "xp_reward": 700
            },
            {
                "name": "Doppelganger",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 40, "max_hp": 60,
                "min_str": 1, "max_str": 3, "min_dex": 3, "max_dex": 5,
                "min_con": 1, "max_con": 3, "min_int": 2, "max_int": 4,
                "min_wis": 2, "max_wis": 4, "min_cha": 3, "max_cha": 5,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 7,
                "loot_multiplier": 3.0, "xp_reward": 700
            },
            {
                "name": "Ghoul",
                "category": "MED",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 15, "max_hp": 30,
                "min_str": 2, "max_str": 4, "min_dex": 2, "max_dex": 4,
                "min_con": 1, "max_con": 3, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 6,
                "on_hit_effect": "STN", "effect_chance": 15,
                "loot_multiplier": 1.8, "xp_reward": 200
            },
            {
                "name": "Sombra",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 12, "max_hp": 22,
                "min_str": -2, "max_str": 0, "min_dex": 2, "max_dex": 4,
                "min_con": 1, "max_con": 3, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 0, "max_armor": 0,
                "damage_dice_count": 1, "damage_dice_sides": 4, "bonus_damage": 6,
                "on_hit_effect": "BLN", "effect_chance": 20,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Espectro",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 18, "max_hp": 30,
                "min_str": -2, "max_str": 0, "min_dex": 2, "max_dex": 4,
                "min_con": 2, "max_con": 4, "min_int": 0, "max_int": 2,
                "min_wis": 1, "max_wis": 3, "min_cha": 1, "max_cha": 3,
                "min_armor": 0, "max_armor": 0,
                "damage_dice_count": 1, "damage_dice_sides": 6, "bonus_damage": 8,
                "on_hit_effect": "LFS", "effect_chance": 15, "effect_dice_count": 2, "effect_dice_sides": 4,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Arpía",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 2, "max_spawn": 4,
                "min_hp": 30, "max_hp": 45,
                "min_str": 1, "max_str": 3, "min_dex": 2, "max_dex": 4,
                "min_con": 1, "max_con": 3, "min_int": -1, "max_int": 1,
                "min_wis": 0, "max_wis": 2, "min_cha": 2, "max_cha": 4,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 6,
                "on_hit_effect": "STN", "effect_chance": 20,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Gárgola",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 40, "max_hp": 60,
                "min_str": 3, "max_str": 5, "min_dex": 1, "max_dex": 3,
                "min_con": 3, "max_con": 5, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 5, "max_armor": 7,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 10,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Perro del Infierno",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 35, "max_hp": 55,
                "min_str": 3, "max_str": 5, "min_dex": 2, "max_dex": 4,
                "min_con": 2, "max_con": 4, "min_int": -2, "max_int": 0,
                "min_wis": 1, "max_wis": 3, "min_cha": -2, "max_cha": 0,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 12,
                "on_hit_effect": "BRN", "effect_chance": 25, "effect_dice_count": 2, "effect_dice_sides": 6,
                "loot_multiplier": 3.0, "xp_reward": 700
            },
            {
                "name": "Engendro Vampírico",
                "category": "MED",
                "rarity": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 60, "max_hp": 90,
                "min_str": 4, "max_str": 6, "min_dex": 4, "max_dex": 6,
                "min_con": 3, "max_con": 5, "min_int": 2, "max_int": 4,
                "min_wis": 2, "max_wis": 4, "min_cha": 2, "max_cha": 4,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 13,
                "on_hit_effect": "LFS", "effect_chance": 30, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 5.0, "xp_reward": 1100
            },
            {
                "name": "Medusa",
                "category": "MED",
                "rarity": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 60, "max_hp": 85,
                "min_str": 1, "max_str": 3, "min_dex": 2, "max_dex": 4,
                "min_con": 2, "max_con": 4, "min_int": 2, "max_int": 4,
                "min_wis": 2, "max_wis": 4, "min_cha": 3, "max_cha": 5,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 1, "damage_dice_sides": 10, "bonus_damage": 10,
                "on_hit_effect": "STN", "effect_chance": 20,
                "loot_multiplier": 5.0, "xp_reward": 1100
            },
            {
                "name": "Cambion",
                "category": "MED",
                "rarity": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 60, "max_hp": 85,
                "min_str": 4, "max_str": 6, "min_dex": 3, "max_dex": 5,
                "min_con": 4, "max_con": 6, "min_int": 2, "max_int": 4,
                "min_wis": 2, "max_wis": 4, "min_cha": 4, "max_cha": 6,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 10,
                "loot_multiplier": 6.0, "xp_reward": 1800
            },
            {
                "name": "Súcubo / Íncubo",
                "category": "MED",
                "rarity": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 50, "max_hp": 75,
                "min_str": 1, "max_str": 3, "min_dex": 3, "max_dex": 5,
                "min_con": 2, "max_con": 4, "min_int": 3, "max_int": 5,
                "min_wis": 2, "max_wis": 4, "min_cha": 5, "max_cha": 7,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 10, "bonus_damage": 10,
                "on_hit_effect": "LFS", "effect_chance": 20, "effect_dice_count": 3, "effect_dice_sides": 6,
                "loot_multiplier": 5.0, "xp_reward": 1100
            },
            {
                "name": "Veterano Mercenario",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 3,
                "min_hp": 45, "max_hp": 65,
                "min_str": 3, "max_str": 5, "min_dex": 2, "max_dex": 4,
                "min_con": 3, "max_con": 5, "min_int": 0, "max_int": 2,
                "min_wis": 0, "max_wis": 2, "min_cha": 0, "max_cha": 2,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 4, "bonus_damage": 12,
                "loot_multiplier": 3.0, "xp_reward": 700
            },
            {
                "name": "Ghast",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 25, "max_hp": 45,
                "min_str": 3, "max_str": 5, "min_dex": 3, "max_dex": 5,
                "min_con": 2, "max_con": 4, "min_int": -1, "max_int": 1,
                "min_wis": 0, "max_wis": 2, "min_cha": -1, "max_cha": 1,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 7,
                "on_hit_effect": "STN", "effect_chance": 20,
                "loot_multiplier": 2.5, "xp_reward": 450
            },
            {
                "name": "Mefito de Fuego",
                "category": "MED",
                "rarity": "UNC",
                "min_spawn": 1, "max_spawn": 4,
                "min_hp": 15, "max_hp": 25,
                "min_str": 0, "max_str": 2, "min_dex": 1, "max_dex": 3,
                "min_con": 1, "max_con": 3, "min_int": -1, "max_int": 1,
                "min_wis": 0, "max_wis": 2, "min_cha": -1, "max_cha": 1,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 1, "damage_dice_sides": 8, "bonus_damage": 4,
                "on_hit_effect": "BRN", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 6,
                "loot_multiplier": 1.5, "xp_reward": 100
            },
            {
                "name": "Capataz Orco",
                "category": "MED",
                "rarity": "RAR",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 50, "max_hp": 75,
                "min_str": 4, "max_str": 6, "min_dex": 1, "max_dex": 3,
                "min_con": 4, "max_con": 6, "min_int": 0, "max_int": 2,
                "min_wis": 1, "max_wis": 3, "min_cha": 1, "max_cha": 3,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 4, "bonus_damage": 12,
                "loot_multiplier": 3.0, "xp_reward": 450
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
