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
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 50, "max_hp": 75,
                "min_str": 4, "max_str": 6, "min_dex": 1, "max_dex": 3,
                "min_con": 4, "max_con": 6, "min_int": 0, "max_int": 2,
                "min_wis": 1, "max_wis": 3, "min_cha": 1, "max_cha": 3,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 4, "bonus_damage": 12,
                "loot_multiplier": 3.0, "xp_reward": 450
            },

            # ==========================================
            # 🔴 ENEMIGOS GRANDES (TIER 3 / RANGO LRG)
            # ==========================================
            {
                "name": "Ogro",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 50, "max_hp": 70,
                "min_str": 4, "max_str": 6, "min_dex": -1, "max_dex": 1,
                "min_con": 4, "max_con": 6, "min_int": -3, "max_int": -1,
                "min_wis": -2, "max_wis": 0, "min_cha": -2, "max_cha": 0,
                "min_armor": 2, "max_armor": 4,
                "damage_dice_count": 2, "damage_dice_sides": 8, "bonus_damage": 6,
                "loot_multiplier": 4.0, "xp_reward": 450
            },
            {
                "name": "Troll",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 70, "max_hp": 95,
                "min_str": 4, "max_str": 6, "min_dex": 1, "max_dex": 3,
                "min_con": 5, "max_con": 8, "min_int": -2, "max_int": 0,
                "min_wis": -1, "max_wis": 1, "min_cha": -2, "max_cha": 0,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 2, "damage_dice_sides": 10, "bonus_damage": 5,
                "on_hit_effect": "LFS", "effect_chance": 40, "effect_dice_count": 2, "effect_dice_sides": 6,
                "loot_multiplier": 5.0, "xp_reward": 700
            },
            {
                "name": "Gigante de las Colinas",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 90, "max_hp": 120,
                "min_str": 6, "max_str": 9, "min_dex": -1, "max_dex": 1,
                "min_con": 5, "max_con": 7, "min_int": -3, "max_int": -1,
                "min_wis": -1, "max_wis": 1, "min_cha": -2, "max_cha": 0,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 3, "damage_dice_sides": 8, "bonus_damage": 8,
                "on_hit_effect": "STN", "effect_chance": 15,
                "loot_multiplier": 6.0, "xp_reward": 1100
            },
            {
                "name": "Owlbear",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 50, "max_hp": 75,
                "min_str": 5, "max_str": 7, "min_dex": 1, "max_dex": 2,
                "min_con": 4, "max_con": 6, "min_int": -4, "max_int": -2,
                "min_wis": 1, "max_wis": 3, "min_cha": -2, "max_cha": 0,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 2, "damage_dice_sides": 8, "bonus_damage": 6,
                "on_hit_effect": "BLD", "effect_chance": 20, "effect_dice_count": 1, "effect_dice_sides": 6,
                "loot_multiplier": 4.5, "xp_reward": 700
            },
            {
                "name": "Mantícora",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 55, "max_hp": 80,
                "min_str": 3, "max_str": 5, "min_dex": 2, "max_dex": 4,
                "min_con": 3, "max_con": 5, "min_int": -1, "max_int": 1,
                "min_wis": 1, "max_wis": 2, "min_cha": -1, "max_cha": 1,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 6, "bonus_damage": 5,
                "on_hit_effect": "PSN", "effect_chance": 10, "effect_dice_count": 1, "effect_dice_sides": 6,
                "loot_multiplier": 5.0, "xp_reward": 700
            },
            {
                "name": "Quimera",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 100, "max_hp": 130,
                "min_str": 4, "max_str": 6, "min_dex": 1, "max_dex": 2,
                "min_con": 4, "max_con": 7, "min_int": -2, "max_int": 0,
                "min_wis": 1, "max_wis": 3, "min_cha": 0, "max_cha": 2,
                "min_armor": 5, "max_armor": 8,
                "damage_dice_count": 3, "damage_dice_sides": 10, "bonus_damage": 5,
                "on_hit_effect": "BRN", "effect_chance": 15, "effect_dice_count": 2, "effect_dice_sides": 6,
                "loot_multiplier": 7.0, "xp_reward": 1800
            },
            {
                "name": "Cubo Gelatinoso",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 70, "max_hp": 100,
                "min_str": 2, "max_str": 4, "min_dex": -4, "max_dex": -2,
                "min_con": 6, "max_con": 9, "min_int": -5, "max_int": -5,
                "min_wis": -2, "max_wis": 0, "min_cha": -5, "max_cha": -5,
                "min_armor": 0, "max_armor": 2,
                "damage_dice_count": 3, "damage_dice_sides": 6, "bonus_damage": 4,
                "on_hit_effect": "STN", "effect_chance": 25,
                "loot_multiplier": 4.0, "xp_reward": 450
            },
            {
                "name": "Dríder",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 100, "max_hp": 140,
                "min_str": 3, "max_str": 5, "min_dex": 3, "max_dex": 5,
                "min_con": 4, "max_con": 6, "min_int": 1, "max_int": 3,
                "min_wis": 1, "max_wis": 3, "min_cha": 1, "max_cha": 3,
                "min_armor": 6, "max_armor": 9,
                "damage_dice_count": 2, "damage_dice_sides": 8, "bonus_damage": 4,
                "on_hit_effect": "STN", "effect_chance": 20,
                "loot_multiplier": 8.0, "xp_reward": 2300
            },
            {
                "name": "Wyvern",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 90, "max_hp": 130,
                "min_str": 4, "max_str": 6, "min_dex": 1, "max_dex": 3,
                "min_con": 3, "max_con": 6, "min_int": -3, "max_int": -1,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 5, "max_armor": 7,
                "damage_dice_count": 2, "damage_dice_sides": 12, "bonus_damage": 6,
                "on_hit_effect": "PSN", "effect_chance": 30, "effect_dice_count": 3, "effect_dice_sides": 6,
                "loot_multiplier": 8.0, "xp_reward": 2300
            },
            {
                "name": "Golem de Carne",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 80, "max_hp": 110,
                "min_str": 4, "max_str": 7, "min_dex": -1, "max_dex": 1,
                "min_con": 4, "max_con": 8, "min_int": -5, "max_int": -5,
                "min_wis": 0, "max_wis": 1, "min_cha": -5, "max_cha": -5,
                "min_armor": 1, "max_armor": 3,
                "damage_dice_count": 2, "damage_dice_sides": 10, "bonus_damage": 8,
                "loot_multiplier": 7.0, "xp_reward": 1800
            },
            {
                "name": "Cíclope",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 120, "max_hp": 155,
                "min_str": 6, "max_str": 8, "min_dex": 0, "max_dex": 2,
                "min_con": 5, "max_con": 7, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 1, "min_cha": 0, "max_cha": 1,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 3, "damage_dice_sides": 10, "bonus_damage": 6,
                "on_hit_effect": "STN", "effect_chance": 10,
                "loot_multiplier": 8.0, "xp_reward": 2300
            },
            {
                "name": "Elemental de Fuego",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 80, "max_hp": 110,
                "min_str": 0, "max_str": 2, "min_dex": 3, "max_dex": 5,
                "min_con": 2, "max_con": 4, "min_int": -2, "max_int": 0,
                "min_wis": 0, "max_wis": 1, "min_cha": -1, "max_cha": 1,
                "min_armor": 3, "max_armor": 5,
                "damage_dice_count": 2, "damage_dice_sides": 8, "bonus_damage": 4,
                "on_hit_effect": "BRN", "effect_chance": 50, "effect_dice_count": 1, "effect_dice_sides": 8,
                "loot_multiplier": 6.0, "xp_reward": 1100
            },
            {
                "name": "Beholder",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 150, "max_hp": 200,
                "min_str": 0, "max_str": 2, "min_dex": 2, "max_dex": 4,
                "min_con": 4, "max_con": 6, "min_int": 4, "max_int": 6,
                "min_wis": 3, "max_wis": 5, "min_cha": 3, "max_cha": 5,
                "min_armor": 8, "max_armor": 12,
                "damage_dice_count": 4, "damage_dice_sides": 10, "bonus_damage": 10,
                "on_hit_effect": "BLN", "effect_chance": 60,
                "loot_multiplier": 15.0, "xp_reward": 5000
            },
            {
                "name": "Rinoceronte Lanudo",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 2,
                "min_hp": 60, "max_hp": 90,
                "min_str": 5, "max_str": 7, "min_dex": -1, "max_dex": 1,
                "min_con": 4, "max_con": 6, "min_int": -4, "max_int": -2,
                "min_wis": 0, "max_wis": 2, "min_cha": -2, "max_cha": 0,
                "min_armor": 4, "max_armor": 6,
                "damage_dice_count": 2, "damage_dice_sides": 8, "bonus_damage": 6,
                "on_hit_effect": "STN", "effect_chance": 25,
                "loot_multiplier": 4.0, "xp_reward": 450
            },
            {
                "name": "Behir",
                "category": "LRG",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 150, "max_hp": 180,
                "min_str": 6, "max_str": 8, "min_dex": 3, "max_dex": 5,
                "min_con": 4, "max_con": 6, "min_int": -1, "max_int": 1,
                "min_wis": 1, "max_wis": 3, "min_cha": 1, "max_cha": 3,
                "min_armor": 7, "max_armor": 10,
                "damage_dice_count": 4, "damage_dice_sides": 8, "bonus_damage": 8,
                "on_hit_effect": "STN", "effect_chance": 20,
                "loot_multiplier": 12.0, "xp_reward": 7200
            },

            # ==========================================
            # ⭐ ENEMIGOS ÉPICOS (TIER 4 / RANGO EPC)
            # ==========================================
            {
                "name": "Tarrasque",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 350, "max_hp": 450,
                "min_str": 8, "max_str": 10, "min_dex": -1, "max_dex": 1,
                "min_con": 8, "max_con": 10, "min_int": -4, "max_int": -2,
                "min_wis": 1, "max_wis": 3, "min_cha": -2, "max_cha": 0,
                "min_armor": 10, "max_armor": 13,
                "damage_dice_count": 4, "damage_dice_sides": 12, "bonus_damage": 18,
                "on_hit_effect": "BLD", "effect_chance": 35, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 15.0, "xp_reward": 8000
            },
            {
                "name": "Dragón Rojo Antiguo",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 280, "max_hp": 380,
                "min_str": 7, "max_str": 9, "min_dex": 2, "max_dex": 4,
                "min_con": 7, "max_con": 9, "min_int": 2, "max_int": 4,
                "min_wis": 1, "max_wis": 3, "min_cha": 2, "max_cha": 4,
                "min_armor": 9, "max_armor": 12,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 15,
                "on_hit_effect": "BRN", "effect_chance": 40, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 12.0, "xp_reward": 6500
            },
            {
                "name": "Liche",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 120, "max_hp": 180,
                "min_str": 0, "max_str": 2, "min_dex": 2, "max_dex": 4,
                "min_con": 4, "max_con": 6, "min_int": 6, "max_int": 8,
                "min_wis": 4, "max_wis": 6, "min_cha": 2, "max_cha": 4,
                "min_armor": 7, "max_armor": 10,
                "damage_dice_count": 2, "damage_dice_sides": 12, "bonus_damage": 8,
                "on_hit_effect": "STN", "effect_chance": 30, "effect_dice_count": 1, "effect_dice_sides": 8,
                "loot_multiplier": 9.0, "xp_reward": 4500
            },
            {
                "name": "Kraken",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 250, "max_hp": 350,
                "min_str": 8, "max_str": 10, "min_dex": 1, "max_dex": 3,
                "min_con": 7, "max_con": 9, "min_int": 1, "max_int": 3,
                "min_wis": 2, "max_wis": 4, "min_cha": 0, "max_cha": 2,
                "min_armor": 10, "max_armor": 13,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 20,
                "on_hit_effect": "STN", "effect_chance": 35, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 14.0, "xp_reward": 7500
            },
            {
                "name": "Demogorgon (Príncipe Demonio)",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 280, "max_hp": 350,
                "min_str": 7, "max_str": 9, "min_dex": 3, "max_dex": 5,
                "min_con": 6, "max_con": 8, "min_int": 3, "max_int": 5,
                "min_wis": 2, "max_wis": 4, "min_cha": 4, "max_cha": 6,
                "min_armor": 8, "max_armor": 11,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 12,
                "on_hit_effect": "BRN", "effect_chance": 35, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 11.0, "xp_reward": 6000
            },
            {
                "name": "Tiamat (Diosa de los Dragones)",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 350, "max_hp": 450,
                "min_str": 8, "max_str": 10, "min_dex": 2, "max_dex": 4,
                "min_con": 8, "max_con": 10, "min_int": 4, "max_int": 6,
                "min_wis": 3, "max_wis": 5, "min_cha": 4, "max_cha": 6,
                "min_armor": 10, "max_armor": 13,
                "damage_dice_count": 4, "damage_dice_sides": 12, "bonus_damage": 25,
                "on_hit_effect": "BRN", "effect_chance": 45, "effect_dice_count": 3, "effect_dice_sides": 8,
                "loot_multiplier": 16.0, "xp_reward": 9000
            },
            {
                "name": "Orcus (Señor de los No-Muertos)",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 250, "max_hp": 320,
                "min_str": 6, "max_str": 8, "min_dex": 2, "max_dex": 4,
                "min_con": 7, "max_con": 9, "min_int": 4, "max_int": 6,
                "min_wis": 3, "max_wis": 5, "min_cha": 3, "max_cha": 5,
                "min_armor": 9, "max_armor": 12,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 12,
                "on_hit_effect": "BLD", "effect_chance": 40, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 12.0, "xp_reward": 6000
            },
            {
                "name": "Zariel (Archidiablesa)",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 320, "max_hp": 400,
                "min_str": 7, "max_str": 9, "min_dex": 4, "max_dex": 6,
                "min_con": 7, "max_con": 9, "min_int": 4, "max_int": 6,
                "min_wis": 3, "max_wis": 5, "min_cha": 5, "max_cha": 7,
                "min_armor": 10, "max_armor": 12,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 18,
                "on_hit_effect": "BRN", "effect_chance": 35, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 13.0, "xp_reward": 7000
            },
            {
                "name": "Empíreo (Empyrean)",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 180, "max_hp": 250,
                "min_str": 5, "max_str": 7, "min_dex": 4, "max_dex": 6,
                "min_con": 5, "max_con": 7, "min_int": 4, "max_int": 6,
                "min_wis": 5, "max_wis": 7, "min_cha": 5, "max_cha": 7,
                "min_armor": 7, "max_armor": 10,
                "damage_dice_count": 2, "damage_dice_sides": 12, "bonus_damage": 10,
                "on_hit_effect": "LFS", "effect_chance": 25, "effect_dice_count": 1, "effect_dice_sides": 8,
                "loot_multiplier": 8.0, "xp_reward": 4000
            },
            {
                "name": "Dragón de Oro Antiguo",
                "category": "EPC",
                "min_spawn": 1, "max_spawn": 1,
                "min_hp": 280, "max_hp": 380,
                "min_str": 7, "max_str": 9, "min_dex": 3, "max_dex": 5,
                "min_con": 7, "max_con": 9, "min_int": 3, "max_int": 5,
                "min_wis": 3, "max_wis": 5, "min_cha": 4, "max_cha": 6,
                "min_armor": 9, "max_armor": 12,
                "damage_dice_count": 3, "damage_dice_sides": 12, "bonus_damage": 8,
                "on_hit_effect": "BRN", "effect_chance": 40, "effect_dice_count": 2, "effect_dice_sides": 8,
                "loot_multiplier": 12.0, "xp_reward": 6000
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
