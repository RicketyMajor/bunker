from django.core.management.base import BaseCommand
from django.db.models import Q
from posada.models import Item, InventorySlot, Adventurer, GuildProfile


class Command(BaseCommand):
    help = 'Audita y limpia ítems fantasma: objetos con coste cero, slots vacíos, y equipamiento huérfano.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo reporta las anomalías sin borrar nada.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        total_cleaned = 0

        self.stdout.write(self.style.WARNING(
            '\n══════════════════════════════════════════'
            '\n  AUDITORÍA DE INVENTARIO DEL BUNKER'
            '\n══════════════════════════════════════════\n'
        ))

        # ─── FASE 1: Ítems con coste CERO en la tabla Item ───
        self.stdout.write(self.style.MIGRATE_HEADING('▸ Fase 1: Ítems con coste cero (Ghost Items)'))

        zero_cost_items = []
        for item in Item.objects.all():
            total_cost = (
                item.cost_iron_half_penny + item.cost_iron_penny +
                item.cost_ardite + item.cost_drabin +
                item.cost_copper_penny + item.cost_iota +
                item.cost_silver_penny + item.cost_sueldo +
                item.cost_talento + item.cost_real + item.cost_marco
            )
            if total_cost == 0:
                zero_cost_items.append(item)

        if zero_cost_items:
            for item in zero_cost_items:
                # Contar cuántos slots y equipamientos referencian este ítem
                slot_count = InventorySlot.objects.filter(item=item).count()
                equip_refs = self._count_equipment_refs(item)

                self.stdout.write(
                    f'  [GHOST] ID={item.id} "{item.name}" '
                    f'(Rareza: {item.rarity}, Tipo: {item.item_type}) '
                    f'— {slot_count} slots, {equip_refs} equipados'
                )

                if not dry_run:
                    # Primero: limpiar slots que referencian este ítem
                    deleted_slots = InventorySlot.objects.filter(item=item).delete()[0]

                    # Segundo: limpiar equipamiento de aventureros que lo tengan puesto
                    cleaned_equips = self._purge_equipment_refs(item)

                    # Tercero: borrar el ítem fantasma
                    item.delete()
                    total_cleaned += 1

                    self.stdout.write(self.style.SUCCESS(
                        f'    → ELIMINADO (borrados {deleted_slots} slots, '
                        f'{cleaned_equips} equipamientos limpiados)'
                    ))
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ Sin ítems fantasma. Catálogo limpio.'))

        # ─── FASE 2: Slots con quantity ≤ 0 ───
        self.stdout.write(self.style.MIGRATE_HEADING('\n▸ Fase 2: Slots con cantidad ≤ 0'))

        empty_slots = InventorySlot.objects.filter(quantity__lte=0)
        empty_count = empty_slots.count()

        if empty_count > 0:
            self.stdout.write(f'  [VACÍO] {empty_count} slots con cantidad 0 o negativa.')
            if not dry_run:
                empty_slots.delete()
                total_cleaned += empty_count
                self.stdout.write(self.style.SUCCESS(f'    → {empty_count} slots eliminados.'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✓ Todos los slots tienen cantidad válida.'))

        # ─── FASE 3: Equipamiento huérfano (apunta a ítems inexistentes) ───
        self.stdout.write(self.style.MIGRATE_HEADING('\n▸ Fase 3: Equipamiento huérfano'))

        equip_slots = [
            'equip_main_hand', 'equip_off_hand', 'equip_head', 'equip_torso',
            'equip_legs', 'equip_hands', 'equip_feet', 'equip_necklace',
            'equip_ring_1', 'equip_ring_2', 'equip_bracelet', 'equip_earring'
        ]

        orphan_count = 0
        for adv in Adventurer.objects.all():
            for slot_name in equip_slots:
                item_ref = getattr(adv, slot_name, None)
                if item_ref is not None:
                    # Verificar que el ítem existe y tiene coste válido
                    try:
                        item_obj = Item.objects.get(id=item_ref.id)
                        total_cost = (
                            item_obj.cost_iron_half_penny + item_obj.cost_iron_penny +
                            item_obj.cost_ardite + item_obj.cost_drabin +
                            item_obj.cost_copper_penny + item_obj.cost_iota +
                            item_obj.cost_silver_penny + item_obj.cost_sueldo +
                            item_obj.cost_talento + item_obj.cost_real + item_obj.cost_marco
                        )
                        if total_cost == 0:
                            self.stdout.write(
                                f'  [HUÉRFANO] {adv.name} → {slot_name} = '
                                f'"{item_obj.name}" (coste cero)'
                            )
                            if not dry_run:
                                setattr(adv, slot_name, None)
                                adv.save()
                                orphan_count += 1
                                self.stdout.write(self.style.SUCCESS(
                                    f'    → Ranura {slot_name} limpiada.'
                                ))
                    except Item.DoesNotExist:
                        self.stdout.write(
                            f'  [HUÉRFANO] {adv.name} → {slot_name} = '
                            f'Item ID {item_ref.id} YA NO EXISTE en la DB'
                        )
                        if not dry_run:
                            setattr(adv, slot_name, None)
                            adv.save()
                            orphan_count += 1

        if orphan_count == 0 and not dry_run:
            self.stdout.write(self.style.SUCCESS('  ✓ Todo el equipamiento es válido.'))
        elif dry_run:
            self.stdout.write('  (dry-run: no se aplicaron cambios)')

        total_cleaned += orphan_count

        # ─── RESUMEN ───
        self.stdout.write(self.style.WARNING(
            f'\n══════════════════════════════════════════'
            f'\n  RESUMEN: {total_cleaned} anomalías corregidas.'
            f'\n══════════════════════════════════════════\n'
        ))

        if dry_run:
            self.stdout.write(self.style.NOTICE(
                '  ⚠ Modo --dry-run activo. Ejecuta sin la bandera para aplicar las correcciones.\n'
            ))

    def _count_equipment_refs(self, item):
        """Cuenta cuántos aventureros tienen este ítem equipado."""
        equip_slots = [
            'equip_main_hand', 'equip_off_hand', 'equip_head', 'equip_torso',
            'equip_legs', 'equip_hands', 'equip_feet', 'equip_necklace',
            'equip_ring_1', 'equip_ring_2', 'equip_bracelet', 'equip_earring'
        ]
        count = 0
        for slot_name in equip_slots:
            count += Adventurer.objects.filter(**{slot_name: item}).count()
        return count

    def _purge_equipment_refs(self, item):
        """Desvincula un ítem del equipamiento de todos los aventureros."""
        equip_slots = [
            'equip_main_hand', 'equip_off_hand', 'equip_head', 'equip_torso',
            'equip_legs', 'equip_hands', 'equip_feet', 'equip_necklace',
            'equip_ring_1', 'equip_ring_2', 'equip_bracelet', 'equip_earring'
        ]
        cleaned = 0
        for slot_name in equip_slots:
            affected = Adventurer.objects.filter(**{slot_name: item})
            for adv in affected:
                setattr(adv, slot_name, None)
                adv.save()
                cleaned += 1
        return cleaned
