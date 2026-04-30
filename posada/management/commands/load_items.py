from django.core.management.base import BaseCommand
from posada.models import Item, ItemType, ItemRarity


class Command(BaseCommand):
    help = 'Puebla la base de datos con el catálogo completo de Armas, Armaduras y Objetos.'

    def handle(self, *args, **kwargs):
        CATALOGO = [
            # --- TEMPLATE BASE PARA COPIAR Y PEGAR ---
            # {
            #     "name": "Nombre del Item",
            #     "description": "Descripción narrativa (opcional)",
            #     "item_type": "W1H|W2H|OFF|HED|TRS|LGS|HND|FET|NCK|RNG|BRC|EAR|CNS|MSC",
            #     "rarity": "COM|UNC|RAR|EPC|LEG",
            #     "allowed_classes": ["WIZ", "SOR", "DRD"],  # Lista de clases que pueden usarlo, dejar vacío si no hay restricciones
            #     # --- ECONOMÍA (Borra las monedas que no uses o déjalas en 0) ---
            #     "cost_iron_half_penny": 0, "cost_iron_penny": 0, "cost_ardite": 0,
            #     "cost_drabin": 0, "cost_copper_penny": 0, "cost_iota": 0,
            #     "cost_silver_penny": 0, "cost_sueldo": 0, "cost_talento": 0,
            #     "cost_real": 0, "cost_marco": 0,
            #     # --- COMBATE ---
            #     "bonus_damage": 0, "bonus_armor": 0,
            #     # --- ESTADÍSTICAS RPG ---
            #     "bonus_str": 0, "bonus_dex": 0, "bonus_con": 0, "bonus_int": 0,
            #     "bonus_wis": 0, "bonus_cha": 0, "bonus_luk": 0,
            # },

            # CONJUNTO DE ARMADURA DE TELA (Común)
            {
                "name": "Capucha de Tela",
                "description": "Una capucha hecha de tela cómoda. Proporciona cobertura ligera para la cabeza.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Túnica de Tela",
                "description": "Una túnica hecha de tela cómoda. Proporciona cobertura ligera para el cuerpo.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Pantalones de Tela",
                "description": "Unos pantalones hechos de tela cómoda. Proporciona cobertura ligera para las piernas.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Botas de Tela",
                "description": "Unas botas hechas de tela cómoda. Proporciona cobertura ligera para los pies.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Guantes de Tela",
                "description": "Unos guantes hechos de tela cómoda. Proporciona cobertura ligera para las manos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            # CONJUNTO DE ARMADURA ACOLCHADA (COMÚN)

            {
                "name": "Gorro Acolchado",
                "description": "Un gorro en capas acolchadas de tela y guata. Es cómodo y protegido.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Atuendo Acolchado",
                "description": "Un atuendo en capas acolchadas de tela y guata. Es cómodo y protegido.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Pantalones Acolchados",
                "description": "Unos pantalones en capas acolchadas de tela y guata. Son cómodos y protegidos.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Botas Acolchadas",
                "description": "Unas botas en capas acolchadas de tela y guata. Son cómodas y protegidas.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            {
                "name": "Guantes Acolchados",
                "description": "Unos guantes en capas acolchadas de tela y guata. Son cómodos y protegidos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK"],
                "cost_iota": 5,
                "bonus_armor": 1,
            },

            # CONJUNTO DE ARMADURA DE CUERO (COMÚN)

            {
                "name": "Yelmo de Cuero",
                "description": "Un yelmo hecho con materiales más suaves y flexibles.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART", "FTR", "PAL"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pechera de Cuero",
                "description": "Una pechera hecha con cuero que ha sido endurecido al ser hervido en aceite, a diferencia de las otras piezas.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART", "FTR", "PAL"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pantalones de Cuero",
                "description": "Unos pantalones hechos con materiales más suaves y flexibles.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART", "FTR", "PAL"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Botas de Cuero",
                "description": "Unas botas hechas con materiales más suaves y flexibles.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART", "FTR", "PAL"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Guantes de Cuero",
                "description": "Unos guantes hechos con materiales más suaves y flexibles.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART", "FTR", "PAL"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            # CONJUNTO DE ARMADURA DE PIELES (COMÚN)

            {
                "name": "Yelmo de Piel",
                "description": "Un yelmo hecho con gruesas pieles y pelajes. Es además de resistente, muy cálido, ideal para climas fríos.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "ART", "DRD", "FTR", "PAL"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pechera de Piel",
                "description": "Una pechera hecha con gruesas pieles y pelajes. Es además de resistente, muy cálida, ideal para climas fríos.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "ART", "DRD", "FTR", "PAL"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pantalones de Piel",
                "description": "Unos pantalones hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "ART", "DRD", "FTR", "PAL"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Botas de Piel",
                "description": "Unas botas hechas con gruesas pieles y pelajes. Son además de resistentes, muy cálidas, ideales para climas fríos.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "ART", "DRD", "FTR", "PAL"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Guantes de Piel",
                "description": "Unos guantes hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "ART", "DRD", "FTR", "PAL"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            # CONJUNTO DE ARMADURA DE MALLA DE COBRE (COMÚN)

            {
                "name": "Cofia de Malla de Cobre",
                "description": "Una cofia hecha de mallas de cobre. Es además de resistente, una pieza flexible.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 1,
                "bonus_armor": 4,
            },

            {
                "name": "Peto de Malla de Cobre",
                "description": "Un peto hecho de mallas de cobre. Brinda una protección sólida para el torso.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 1,
                "bonus_armor": 4,
            },

            {
                "name": "Brafoneras de Malla de Cobre",
                "description": "Unas brafoneras hechas de mallas de cobre. Son además de resistentes, flexibles.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 1,
                "bonus_armor": 4,
            },

            {
                "name": "Botas de Malla de Cobre",
                "description": "Unas botas hechas de mallas de cobre. Son además de resistentes, flexibles.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 1,
                "bonus_armor": 4,
            },

            {
                "name": "Guantes de Malla de Cobre",
                "description": "Unos guantes hechos de mallas de cobre. Son además de resistentes, flexibles.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 1,
                "bonus_armor": 4,
                "bonus_con": 1,
            },

            # CONJUNTO DE COTA DE ANILLAS (COMÚN)

            {
                "name": "Cofia de Cota de Anillas",
                "description": "Una cofia hecha de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "DRD", "RGR", "ART"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            {
                "name": "Peto de Cota de Anillas",
                "description": "Un peto hecho de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "DRD", "RGR", "ART"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            {
                "name": "Brafoneras de Cota de Anillas",
                "description": "Unas brafoneras hechos de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "DRD", "RGR", "ART"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            {
                "name": "Botas de Cota de Anillas",
                "description": "Unas botas hechas de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "DRD", "RGR", "ART"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            {
                "name": "Guanteletes de Cota de Anillas",
                "description": "Unos guantes hechos de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "DRD", "RGR", "ART"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            # CONJUNTO DE ARMADURA DE PLACAS DE BRONCE (COMÚN)

            {
                "name": "Yelmo de Placas de Bronce",
                "description": "Un yelmo formado por placas de bronce interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para la cabeza.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 2,
                "bonus_armor": 5,
            },

            {
                "name": "Peto de Placas de Bronce",
                "description": "Un peto formado por placas de bronce interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para el torso.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 2,
                "bonus_armor": 5,
            },

            {
                "name": "Grebas de Placas de Bronce",
                "description": "Unas grebas formadas por placas de bronce interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para las piernas.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 2,
                "bonus_armor": 5,
            },

            {
                "name": "Botas de Placas de Bronce",
                "description": "Unas botas formadas por placas de bronce interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para los pies.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 2,
                "bonus_armor": 5,
            },

            {
                "name": "Guanteletes de Placas de Bronce",
                "description": "Unos guanteletes formadas por placas de bronce interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para las manos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 2,
                "bonus_armor": 5,
            },

            # DAGA DE HIERRO (COMÚN)

            {
                "name": "Daga de Hierro",
                "description": "Una daga hecha de hierro, ligera para el combate cuerpo a cuerpo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["RGR", "BBN", "ART", "DRD", "FTR", "PAL", "WIZ", "SOR", "WLK", "ROG", "BRD", "MNK"],
                "cost_talento": 1,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 0,
            },

            # ESPADA CORTA DE HIERRO (COMÚN)

            {
                "name": "Espada Corta de Hierro",
                "description": "Una espada corta hecha de hierro, adecuada para el combate cuerpo a cuerpo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["RGR", "BBN", "ART", "DRD", "FTR", "PAL", "ROG", "BRD"],
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 0,
            },

            # MAZA DE MADERA Y HIERRO (COMÚN)

            {
                "name": "Maza de Madera y Hierro",
                "description": "Una maza hecha de madera y hierro, adecuada para el combate cuerpo a cuerpo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["CLR", "BBN", "FTR", "PAL"],
                "cost_real": 1,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 0,
            },

            # CIMITARRA DE COBRE (COMÚN)

            {
                "name": "Cimitarra de Cobre",
                "description": "Un sable de hoja curva y un solo filo, ideal para el combate cuerpo a cuerpo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["RGR", "BBN", "DRD", "FTR", "PAL", "ROG"],
                "cost_marco": 1,
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_dex": 1,
                "bonus_damage": 1,
            },





        ]

        self.stdout.write("Forjando los ítems en la base de datos...")
        items_creados = 0

        for data in CATALOGO:
            # Usamos update_or_create para que, si corres el script de nuevo,
            # se actualicen los precios en lugar de duplicar los ítems.
            item, created = Item.objects.update_or_create(
                name=data["name"],
                defaults={k: v for k, v in data.items() if k != "name"}
            )
            if created:
                items_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f'¡Éxito! Se forjaron {items_creados} ítems nuevos.'))
