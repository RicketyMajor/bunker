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
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pechera de Cuero",
                "description": "Una pechera hecha con cuero que ha sido endurecido al ser hervido en aceite, a diferencia de las otras piezas.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Pantalones de Cuero",
                "description": "Unos pantalones hechos con materiales más suaves y flexibles.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Botas de Cuero",
                "description": "Unas botas hechas con materiales más suaves y flexibles.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            {
                "name": "Guantes de Cuero",
                "description": "Unos guantes hechos con materiales más suaves y flexibles.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_talento": 1,
                "bonus_armor": 2,
            },

            # CONJUNTO DE ARMADURA DE PIELES (COMÚN)

            {
                "name": "Yelmo de Piel",
                "description": "Un yelmo hecho con gruesas pieles y pelajes. Es además de resistente, muy cálido, ideal para climas fríos.",
                "item_type": "HED",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pechera de Piel",
                "description": "Una pechera hecha con gruesas pieles y pelajes. Es además de resistente, muy cálida, ideal para climas fríos.",
                "item_type": "TRS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Pantalones de Piel",
                "description": "Unos pantalones hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "LGS",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Botas de Piel",
                "description": "Unas botas hechas con gruesas pieles y pelajes. Son además de resistentes, muy cálidas, ideales para climas fríos.",
                "item_type": "FET",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
            },

            {
                "name": "Guantes de Piel",
                "description": "Unos guantes hechos con gruesas pieles y pelajes. Son además de resistentes, muy cálidos, ideales para climas fríos.",
                "item_type": "HND",
                "rarity": "COM",
                "allowed_classes": ["ROG", "RGR", "BRD", "MNK", "BBN", "ART"],
                "cost_real": 2,
                "bonus_armor": 3,
                "bonus_con": 1,
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
