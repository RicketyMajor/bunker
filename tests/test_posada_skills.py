import os
import sys
import django
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bunker_core.settings')
django.setup()

from posada.skills import SkillRegistry
from posada.models import Adventurer, AdventurerClass, Item

# Mock Item DB call
import unittest.mock
Item.objects = unittest.mock.MagicMock()
Item.objects.filter.return_value = [
    unittest.mock.MagicMock(id=1, name="Poción", rarity="COM"),
    unittest.mock.MagicMock(id=2, name="Vendaje", rarity="UNC")
]
Item.objects.all.return_value = [
    unittest.mock.MagicMock(id=1, name="Poción", rarity="COM")
]

class MockAdventurer:
    def __init__(self, id, name, adv_class, level=10):
        self.id = id
        self.name = name
        self.adv_class = adv_class
        self.level = level
        self.max_hp = 100
        self.current_hp = 100
        self.class_resources = {}
        
    def get_stat_modifiers(self):
        # The real `Adventurer.get_stat_modifiers` (posada/models.py:405-408) declares
        # SEVENTEEN keys; this mock declared six, so any skill indexing one of the other
        # eleven directly raised KeyError. `golpe_brutal:102` does `adv_mods['damage']` --
        # note the lines around it use `.get(..., default)` -- and it only runs when the
        # attack lands, which is why it surfaced as "the gate fails about 1 run in 10"
        # rather than as a test that simply fails. Measured 2026-08-24: seeds 3 and 33 of
        # the first 40. It was never an engine bug: the model always seeds `damage: 2`.
        #
        # Mirrored by hand rather than called for real, because the real method walks
        # `get_equipped_items()` and that hits the database. If the model gains a key, the
        # seed sweep described at SEMILLA is what finds it.
        return {'str': 3, 'dex': 3, 'con': 3, 'int': 3, 'wis': 3, 'cha': 3, 'luk': 3,
                'armor': 0, 'damage': 2, 'weapon_dice_count': 0, 'weapon_dice_sides': 0,
                'bonus_dmg_dice_count': 0, 'bonus_dmg_dice_sides': 0,
                'on_hit_effect': 'NON', 'effect_chance': 0, 'effect_dice_count': 1,
                'effect_dice_sides': 4}

def create_mock_enemy():
    return {
        'id': random.randint(100, 999),
        'name': 'Mock Monster',
        'hp': 200,
        'max_hp': 200,
        'stats': {'str': 12, 'dex': 12, 'con': 12, 'int': 12, 'wis': 12, 'cha': 12, 'armor': 14}
    }

# The gate is seeded, the fuzzing is kept, and the two are the same knob.
#
# Nothing seeded the global RNG here, so every run simulated a different 50-turn combat and
# roughly 1 run in 10 missed an assertion. `bunker doctor` is the only automated gate this
# project has and every session starts with it: a gate that cries wolf once in ten teaches its
# reader to ignore it, which is worse than a test that simply fails.
#
# But the accidental fuzzing was the only thing in this project that ever exercised the combat
# engine across many seeds, and pinning it alone would hide whatever it was finding. So the
# seed is a variable with a default: `bunker doctor` gets a reproducible run, and a sweep is
#     for s in $(seq 1 200); do BUNKER_SEMILLA=$s python -m tests.test_posada_skills || \
#       echo "SEMILLA MALA: $s"; done
# A seed that fails is reproducible by definition -- pin it in its own check and fix it.
SEMILLA = int(os.environ.get('BUNKER_SEMILLA', '4242'))


def run_tests():
    random.seed(SEMILLA)
    skills = SkillRegistry.get_all_skills()
    print(f"Testing {len(skills)} skills... (semilla {SEMILLA})")
    
    errors = []
    
    for skill_id, skill_data in skills.items():
        func = skill_data['execute']
        
        # Eval mode
        for hp_ratio in [1.0, 0.5, 0.2]:
            adv_class = skill_data['allowed_classes'][0] if skill_data['allowed_classes'] else 'FTR'
            caster = MockAdventurer(id=1, name="Caster", adv_class=adv_class)
            caster.current_hp = int(caster.max_hp * hp_ratio)
            
            allies = [
                MockAdventurer(id=2, name="Ally1", adv_class="CLR"),
                MockAdventurer(id=3, name="Ally2", adv_class="ROG"),
                MockAdventurer(id=4, name="Ally3", adv_class="WIZ")
            ]
            allies[0].current_hp = int(allies[0].max_hp * hp_ratio)
            
            enemies = [create_mock_enemy(), create_mock_enemy()]
            
            context = {
                'caster': caster,
                'allies': allies,
                'enemies': enemies,
                'adv_status': {1: set(), 2: set(), 3: set(), 4: set()},
                'log': [],
                'current_second': 10,
                'eval_mode': True,
                'session_duration': 7200,
                'base_gold': 500
            }
            
            try:
                score = func(context)
                if not isinstance(score, (int, float, bool)):
                    errors.append(f"{skill_id} eval_mode at hp {hp_ratio} returned {type(score)} instead of number/bool")
            except Exception as e:
                errors.append(f"{skill_id} eval_mode failed: {str(e)}")
                
        # Execution mode
        adv_class = skill_data['allowed_classes'][0] if skill_data['allowed_classes'] else 'FTR'
        caster = MockAdventurer(id=1, name="Caster", adv_class=adv_class)
        caster.current_hp = 50
        
        allies = [
            MockAdventurer(id=2, name="Ally1", adv_class="CLR"),
            MockAdventurer(id=3, name="Ally2", adv_class="ROG"),
            MockAdventurer(id=4, name="Ally3", adv_class="WIZ")
        ]
        allies[0].current_hp = 20
        
        enemies = [create_mock_enemy(), create_mock_enemy()]
        
        context = {
            'caster': caster,
            'allies': allies,
            'enemies': enemies,
            'adv_status': {1: set(), 2: set(), 3: set(), 4: set()},
            'log': [],
            'current_second': 10,
            'eval_mode': False,
            'session_duration': 7200,
            'base_gold': 500
        }
        
        try:
            result = func(context)
            if not isinstance(result, bool):
                errors.append(f"{skill_id} exec_mode returned {type(result)} instead of bool")
                
            # Check HP constraints
            for adv in [caster] + allies:
                if adv.current_hp > adv.max_hp:
                    errors.append(f"{skill_id} healed {adv.name} beyond max_hp ({adv.current_hp} > {adv.max_hp})")
                    
        except Exception as e:
            import traceback
            errors.append(f"{skill_id} exec_mode failed: {str(e)}\n{traceback.format_exc()}")
            
    if errors:
        print(f"Found {len(errors)} errors:")
        for err in errors:
            print(f"- {err}")
    else:
        print(f"All {len(skills)} skills tested successfully with 0 exceptions and strict constraints met.")

    cubiertas = {c for d in skills.values() for c in d['allowed_classes']}
    faltan = set(AdventurerClass.values) - cubiertas
    if faltan:
        errors.append(f"clases sin ninguna skill registrada: {sorted(faltan)}")
    print(f"  {len(skills)} skills sobre {len(cubiertas)} clases reales")
    return len(errors)

def simulate_combat_balance():
    # Seeded again rather than relying on run_tests' seed: the two are run together today, but
    # a caller that runs only this one would otherwise get an unseeded RNG and the flakiness
    # back. See SEMILLA above for how to sweep.
    random.seed(SEMILLA)
    print("\n--- Phase 2: Combat Balance Simulation ---")
    # Derivado del modelo, no escrito a mano: la lista literal traía BDR, CL y FGT — tres
    # códigos que no existen — así que tres iteraciones corrían sobre una lista de skills
    # vacía e imprimían un tranquilizador `Dealt 0 Dmg`, y 30 de las 132 skills (Bardo 10,
    # Clérigo 10, Guerrero 10) no se simulaban nunca.
    classes = list(AdventurerClass.values)
    
    for cls in classes:
        caster = MockAdventurer(id=1, name=f"{cls}_Tester", adv_class=cls, level=10)
        allies = [
            MockAdventurer(id=2, name="Ally1", adv_class="FTR"),
            MockAdventurer(id=3, name="Ally2", adv_class="CLR")
        ]
        enemies = [create_mock_enemy()] # Boss
        
        total_dmg = 0
        total_heal = 0
        
        # Give them all their skills
        available_skills = []
        for skill_id, skill_data in SkillRegistry.get_all_skills().items():
            if cls in skill_data["allowed_classes"] and caster.level >= skill_data["req_level"]:
                if skill_data["type"] == "COMBAT":
                    available_skills.append(skill_data)
        
        for turn in range(50):
            # Reset HP to avoid being at max
            caster.current_hp = 50
            for a in allies: a.current_hp = 50
            enemies[0]['hp'] = 1000 # keep boss alive
            
            # Evaluate best skill
            best_score = 0
            best_skill = None
            
            context = {
                'caster': caster,
                'allies': allies,
                'enemies': enemies,
                'adv_status': {1: set(), 2: set(), 3: set()},
                'log': [],
                'current_second': turn * 10,
                'eval_mode': True,
                'session_duration': 7200,
                'base_gold': 500
            }
            
            for skill in available_skills:
                try:
                    score = skill['execute'](context)
                    if type(score) == bool: score = 0
                    if score > best_score:
                        best_score = score
                        best_skill = skill
                except:
                    pass
            
            if best_skill:
                context['eval_mode'] = False
                context['log'] = []
                try:
                    best_skill['execute'](context)
                    
                    for event in context['log']:
                        if event.get('type') == 'heal':
                            total_heal += event.get('amount', 0)
                except:
                    pass
            
            # Check dmg dealt
            dmg_dealt = 1000 - enemies[0]['hp']
            if dmg_dealt > 0:
                total_dmg += dmg_dealt
                if cls == 'BBN': print(f"Turn {turn}: Used {best_skill['id']} dealt {dmg_dealt}")
                
        print(f"Class {cls:3}: Dealt {total_dmg:4} Dmg | Healed {total_heal:4} HP in 50 simulated turns.")

if __name__ == '__main__':
    # The exit code is the whole point of running this from `bunker doctor`: without it the
    # script printed its errors and still exited 0, so the runner reported a green check
    # against a broken module and swallowed the error list with it.
    fallos = run_tests()
    simulate_combat_balance()
    raise SystemExit(1 if fallos else 0)
