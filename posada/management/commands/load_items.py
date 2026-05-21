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
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pechera de Cuero",
                "description": "Una pechera hecha con cuero que ha sido endurecido al ser hervido en aceite, a diferencia de las otras piezas.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pantalones de Cuero",
                "description": "Unos pantalones hechos con materiales más suaves y flexibles.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Botas de Cuero",
                "description": "Unas botas hechas con materiales más suaves y flexibles.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Guantes de Cuero",
                "description": "Unos guantes hechos con materiales más suaves y flexibles.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            # CONJUNTO DE ARMADURA DE PIELES (COMÚN)

            {
                "name": "Yelmo de Piel",
                "description": "Un yelmo hecho con gruesas pieles y pelajes. Es además de resistente, muy cálido, ideal para climas fríos.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "DRD", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pechera de Piel",
                "description": "Una pechera hecha con gruesas pieles y pelajes. Es además de resistente, muy cálida, ideal para climas fríos.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "DRD", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pantalones de Piel",
                "description": "Unos pantalones hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "DRD", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Botas de Piel",
                "description": "Unas botas hechas con gruesas pieles y pelajes. Son además de resistentes, muy cálidas, ideales para climas fríos.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "DRD", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Guantes de Piel",
                "description": "Unos guantes hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["CLR", "RGR", "MNK", "BBN", "DRD", "ART"],
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
            },

            # CONJUNTO DE COTA DE ANILLAS (COMÚN)

            {
                "name": "Cofia de Cota de Anillas",
                "description": "Una cofia hecha de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
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
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
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
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
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
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "bonus_armor": 4,
            },

            {
                "name": "Guanteletes de Cota de Anillas",
                "description": "Unos guanteletes hechos de cuero con unas pesadas anillas cosidas, que ayudan a reforzar la armadura contra los golpes de hachas y espadas.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
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
                "allowed_classes": ["RGR", "BBN", "FTR", "PAL", "ROG", "BRD"],
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
                "allowed_classes": ["RGR", "BBN", "FTR", "PAL", "ROG", "BRD"],
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
                "allowed_classes": ["BBN", "FTR", "PAL", "ROG"],
                "cost_marco": 1,
                "cost_talento": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_dex": 1,
                "bonus_damage": 0,
            },

            # HOZ OXIDADA (COMÚN)

            {
                "name": "Hoz Oxidada",
                "description": "Una hoz con una hoja oxidada, seguramente robada de alguna granja.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["RGR", "BBN", "FTR", "PAL", "ROG", "BRD"],
                "cost_iota": 8,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 0,
            },

            # LÁTIGO DE CUERO (COMÚN)

            {
                "name": "Látigo de Cuero",
                "description": "Un látigo hecho de cuero, adecuado para mantener la distancia.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["CLR", "BBN", "FTR", "PAL", "ROG"],
                "cost_talento": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 0,
            },

            # BO DE MADERA (COMÚN)

            {
                "name": "Bō de Madera",
                "description": "Un bastón de casi dos metros de longitud hecho de madera, adecuado para artes marciales.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["MNK"],
                "cost_real": 2,
                "cost_talento": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 1,
            },

            # MANOPLAS DE HIERRO (COMÚN)

            {
                "name": "Manoplas de Hierro",
                "description": "Unas manoplas hechas de hierro, usadas por aquellos aque saben defenderse con los puños.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["MNK"],
                "cost_talento": 1,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 0,
            },

            # MANGUAL (COMÚN)

            {
                "name": "Mangual",
                "description": "Un mango de madera unido a varias bolas de hierro con púas mediante cadenas.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["CLR", "BBN", "FTR", "PAL"],
                "cost_real": 3,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 8,
                "bonus_damage": 0,
            },

            # MARTILLO LIGERO DE HIERRO (COMÚN)

            {
                "name": "Martillo Ligero de Hierro",
                "description": "Un martillo hecho de hierro, ligero y contundente.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["CLR", "BBN", "FTR", "PAL"],
                "cost_talento": 1,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 0,
            },

            # ESCUDO DE MADERA (COMÚN)

            {
                "name": "Escudo de Madera",
                "description": "Un escudo hecho de madera, adecuado para defenderse en combate.",
                "item_type": "OFF",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR", "PAL", "CLR"],
                "cost_talento": 2,
                "bonus_armor": 1,
            },

            # ESCUDO DE HIERRO (COMÚN)

            {
                "name": "Escudo de Hierro",
                "description": "Un escudo hecho de hierro, más pesado, más resistente.",
                "item_type": "OFF",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR", "PAL", "CLR"],
                "cost_real": 3,
                "cost_iota": 5,
                "bonus_armor": 2,
            },

            # VARITA DE APRENDIZ (COMÚN)

            {
                "name": "Varita de Aprendiz",
                "description": "Una varita hecha de madera, adecuada para lanzar hechizos de nivel bajo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_marco": 1,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 1,
            },

            # LIBRO DE HECHIZOS DE APRENDIZ (COMÚN)

            {
                "name": "Libro de Hechizos de Aprendiz",
                "description": "Un libro que contiene hechizos de nivel bajo.",
                "item_type": "OFF",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_marco": 1,
                "cost_talento": 2,
                "bonus_int": 1,
                "bonus_damage": 1,
            },

            # ESPADA LARGA DE HIERRO (COMÚN)

            {
                "name": "Espada Larga de Hierro",
                "description": "Una espada larga hecha de hierro. Inflinge un daño devastador.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR"],
                "cost_marco": 1,
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 10,
                "bonus_damage": 0,
            },

            # GRAN HACHA DE BATALLA (COMÚN)

            {
                "name": "Gran Hacha de Batalla",
                "description": "Una hacha grande y pesada. Es difícil de manejar, pero inflige mucho daño.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR"],
                "cost_marco": 1,
                "cost_real": 3,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 12,
                "bonus_damage": 0,
                "bonus_dex": -1,
            },

            # LANZA DE MADERA CON PUNTA DE HIERRO (COMÚN)


            {
                "name": "Lanza de Madera con Punta de Hierro",
                "description": "Una lanza hecha de madera con una punta de hierro. Es adecuada para mantener la distancia en el combate.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR"],
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 8,
                "bonus_damage": 0,
            },

            # ALABARDA BÁSICA (COMÚN)

            {
                "name": "Alabarda Básica",
                "description": "Una alabarda simple. Gran rango y poderosa en combate, pero difícil de manejar.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BBN", "FTR"],
                "cost_marco": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 12,
                "bonus_damage": 0,
                "bonus_dex": -1,
            },

            # ARCO CORTO (COMÚN)

            {
                "name": "Arco Corto",
                "description": "Un arco corto. Es adecuado para el combate a distancia.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["RGR"],
                "cost_marco": 1,
                "cost_talento": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 0,
            },

            # ARCO LARGO (COMÚN)

            {
                "name": "Arco Largo",
                "description": "Un arco largo. Las flechas llegan a una mayor distancia y mayor poder de penetración.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["RGR"],
                "cost_marco": 2,
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 8,
                "bonus_damage": 1,
            },

            # BALLESTA LIGERA (COMÚN)

            {
                "name": "Ballesta Ligera",
                "description": "Una ballesta ligera, con un mayor poder perforante que un arco.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["RGR", "ART"],
                "cost_marco": 2,
                "cost_real": 2,
                "damage_dice_count": 1,
                "damage_dice_sides": 8,
                "bonus_damage": 2,
                "bonus_dex": -1,
            },

            # BÁCULO DE ROBLE (COMÚN)

            {
                "name": "Báculo de Roble",
                "description": "Un báculo de roble para lanzar hechizos de nivel medio.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["WIZ", "SOR", "DRD", "WLK"],
                "cost_marco": 1,
                "cost_real": 2,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 8,
                "bonus_damage": 1,
            },

            # PISTOLA DE CHISPAS (COMÚN)

            {
                "name": "Pistola de Chispas",
                "description": "Una pistola de chispas que usa como munición balas de plomo.",
                "item_type": "W1H",
                "rarity": "COM",
                "allowed_classes": ["ART"],
                "cost_real": 1,
                "cost_talento": 1,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 1,
            },

            # MOSQUETE OXIDADO (COMÚN)

            {
                "name": "Mosquete Oxidado",
                "description": "Un mosquete oxidado, pero aún funcional.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["ART"],
                "cost_marco": 1,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 1,
            },

            # ARPA LIRA (COMÚN)

            {
                "name": "Arpa Lira",
                "description": "Una arpa lira, utilizada para tocar melodías y lanzar hechizos de nivel bajo.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BRD"],
                "cost_real": 1,
                "damage_dice_count": 1,
                "damage_dice_sides": 4,
                "bonus_damage": 1,
                "bonus_cha": 1,
            },

            # LAÚD DE 7 CUERDAS (COMÚN)

            {
                "name": "Laúd de 7 Cuerdas",
                "description": "Un laúd de 7 cuerdas, utilizado para tocar melodías y subir la moral de los aliados.",
                "item_type": "W2H",
                "rarity": "COM",
                "allowed_classes": ["BRD"],
                "cost_real": 3,
                "cost_talento": 1,
                "cost_iota": 5,
                "damage_dice_count": 1,
                "damage_dice_sides": 6,
                "bonus_damage": 1,
                "bonus_cha": 2,
            },

            # CONJUNTO DE ARMADURA DE CUERO TACHONADA (POCO COMÚN)

            {
                "name": "Yelmo de Cuero Tachonado",
                "description": "Un yelmo de cuero tachonado, hecha de cuero resistente pero flexible, está reforzada con pinchos o remaches dispuestos muy juntos.",
                "item_type": "HED",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 4,
                "cost_real": 2,
                "bonus_armor": 3,
            },

            {
                "name": "Pechera de Cuero Tachonado",
                "description": "Una pechera de cuero tachonado, hecha de cuero resistente pero flexible, está reforzada con pinchos o remaches dispuestos muy juntos.",
                "item_type": "TRS",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 4,
                "cost_real": 2,
                "bonus_armor": 3,
            },

            {
                "name": "Pantalones de Cuero Tachonado",
                "description": "Unos pantalones de cuero tachonado, hechos de cuero resistente pero flexible, están reforzados con pinchos o remaches dispuestos muy juntos.",
                "item_type": "LGS",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 4,
                "cost_real": 2,
                "bonus_armor": 3,
            },

            {
                "name": "Botas de Cuero Tachonado",
                "description": "Unas botas de cuero tachonado, hechos de cuero resistente pero flexible, están reforzadas con pinchos o remaches dispuestos muy juntos.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 4,
                "cost_real": 2,
                "bonus_armor": 3,
            },

            {
                "name": "Guantes de Cuero Tachonado",
                "description": "Unos guantes de cuero tachonado, hechos de cuero resistente pero flexible, están reforzados con pinchos o remaches dispuestos muy juntos.",
                "item_type": "HND",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 4,
                "cost_real": 2,
                "bonus_armor": 3,
            },

            # CONJUNTO DE MALLA DE ACERO (POCO COMÚN)

            {
                "name": "Cofia de Malla de Acero",
                "description": "Una cofia hecha de mallas de acero. Es además de resistente, una pieza flexible.",
                "item_type": "HED",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 7,
                "cost_real": 2,
                "bonus_armor": 6,
            },

            {
                "name": "Peto de Malla de Acero",
                "description": "Un peto hecho de mallas de acero. Brinda una protección sólida para el torso.",
                "item_type": "TRS",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 7,
                "cost_real": 2,
                "bonus_armor": 6,
            },

            {
                "name": "Brafoneras de Malla de Acero",
                "description": "Unas brafoneras hechas de mallas de acero. Son además de resistentes, flexibles.",
                "item_type": "LGS",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 7,
                "cost_real": 2,
                "bonus_armor": 6,
            },

            {
                "name": "Botas de Malla de Acero",
                "description": "Unas botas hechas de mallas de acero. Son además de resistentes, flexibles.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 7,
                "cost_real": 2,
                "bonus_armor": 6,
            },

            {
                "name": "Guantes de Malla de Acero",
                "description": "Unos guantes hechos de mallas de acero. Son además de resistentes, flexibles.",
                "item_type": "HND",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 7,
                "cost_real": 2,
                "bonus_armor": 6,
            },

            # CONJUNTO DE CORAZA DE ACERO (POCO COMÚN)

            {
                "name": "Celada de Acero",
                "description": "Una celada hecha de acero ligero que no bloquean la visión.",
                "item_type": "HED",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_marco": 10,
                "bonus_armor": 5,
            },

            {
                "name": "Coraza de Acero",
                "description": "Una coraza de metal ajustado que protege los órganos vitales, a menudo combinado con cuero flexible para proteger extremidades sin limitar el movimiento.",
                "item_type": "TRS",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_marco": 10,
                "bonus_armor": 5,
            },

            {
                "name": "Escarcelas de Acero",
                "description": "Unas escarcelas de metal que protegen los muslos sin rigidez.",
                "item_type": "LGS",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_marco": 10,
                "bonus_armor": 5,
            },

            {
                "name": "Botas con punteras de Acero",
                "description": "Unas botas hechas de cuero reforzadas en las puntas con láminas de acero.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_marco": 10,
                "bonus_armor": 5,
            },

            {
                "name": "Mitones reforzados con Acero",
                "description": "Unos mitones de cuero reforzados con láminas de acero sobre el dorso.",
                "item_type": "HND",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL", "CLR", "RGR", "BBN"],
                "cost_marco": 10,
                "bonus_armor": 5,
            },

            # CONJUNTO DE ARMADURA DE PLACAS DE ACERO (POCO COMÚN)

            {
                "name": "Yelmo de Placas de Acero",
                "description": "Un yelmo formado por placas de acero interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para la cabeza.",
                "item_type": "HED",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 15,
                "bonus_armor": 8,
            },

            {
                "name": "Peto de Placas de Acero",
                "description": "Un peto formado por placas de acero interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para el torso.",
                "item_type": "TRS",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 15,
                "bonus_armor": 8,
            },

            {
                "name": "Grebas de Placas de Acero",
                "description": "Unas grebas formadas por placas de acero interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para las piernas.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 15,
                "bonus_armor": 8,
            },

            {
                "name": "Botas de Placas de Acero",
                "description": "Unas botas formadas por placas de acero interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para los pies.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 15,
                "bonus_armor": 8,
            },

            {
                "name": "Guanteletes de Placas de Acero",
                "description": "Unos guanteletes formadas por placas de acero interconectadas. Es una pieza de armadura pesada que ofrece una protección sólida para las manos.",
                "item_type": "HND",
                "rarity": "UNC",
                "allowed_classes": ["FTR", "PAL"],
                "cost_marco": 15,
                "bonus_armor": 8,
            },

            # CONJUNTO DE ARMADURA DE EXPLORADOR ÉLFICO (POCO COMÚN)

            {
                "name": "Yelmo de Explorador Élfico",
                "description": "Un yelmo hecho de hierro, cuero y adularia refinada, un material común en artesanía élfica.",
                "item_type": "HED",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 12,
                "bonus_armor": 3,
                "bonus_dex": 1,
            },

            {
                "name": "Pechera de Explorador Élfico",
                "description": "Una pechera hecha de hierro, cuero y adularia refinada, un material común en artesanía élfica.",
                "item_type": "TRS",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 12,
                "bonus_armor": 3,
                "bonus_dex": 1,
            },

            {
                "name": "Pantalones de Explorador Élfico",
                "description": "Unos pantalones hechos de hierro, cuero y adularia refinada, un material común en artesanía élfica.",
                "item_type": "LGS",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 12,
                "cost_real": 3,
                "bonus_armor": 3,
                "bonus_dex": 1,
            },

            {
                "name": "Botas de Explorador Élfico",
                "description": "Unas botas hechas de hierro, cuero y adularia refinada, un material común en artesanía élfica.",
                "item_type": "FET",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 12,
                "bonus_armor": 3,
                "bonus_dex": 1,
            },

            {
                "name": "Guanteletes de Explorador Élfico",
                "description": "Unos guanteletes hechos de hierro, cuero y adularia refinada, un material común en artesanía élfica.",
                "item_type": "HND",
                "rarity": "UNC",
                "allowed_classes": ["ROG", "RGR", "BRD", "ART"],
                "cost_marco": 12,
                "bonus_armor": 3,
                "bonus_dex": 1,
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
