"""Daily habits and the calendar sweep: what a missed day costs and what an avoided one pays.

Moved out of `legacy.py` unchanged (Phase 3, Task 8). Keeps `@transaction.atomic` and the
`ponytail:` marker on the calendar branch, which records that an event expires WITHOUT paying.
"""
from collections import Counter
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from posada.models import GuildProfile, DailyHabit, CalendarEvent

# Toca el gremio, los habitos y los eventos del calendario en un solo barrido, y lo llaman
# dos endpoints GET. Sin la transaccion, una excepcion a mitad dejaba habitos con el marcador
# de evaluacion avanzado y el gremio sin cobrar ni pagar.
@transaction.atomic
def evaluate_daily_penalties():
    """Resta prestigio por pereza o PREMIA por evitar malos hábitos.
    
    Usa `last_evaluated_date` como marcador de la última fecha procesada.
    `last_completed_date` queda exclusivamente para acciones del usuario.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    habits = DailyHabit.objects.all()
    guild, _ = GuildProfile.objects.get_or_create(id=1)

    # Collected here and paid at the end, in order. Each movement still becomes its own
    # ledger entry — a bad week can no longer hide inside a good net number — but WHEN they
    # are paid decides the guild's level, and that must not depend on row order. See the
    # comment at the payment loop below.
    movimientos = []
    penalty_log = []

    for habit in habits:
        # El marcador de evaluación indica hasta qué fecha ya se procesó
        eval_ref = habit.last_evaluated_date if habit.last_evaluated_date else habit.created_at
        eval_delta = (today - eval_ref).days

        if eval_delta < 1:
            continue  # Ya evaluado hoy, nada que hacer

        if habit.is_bad_habit:
            # --- MALOS HÁBITOS: Recompensar por cada día válido sobrevivido ---
            # Verificar cada día desde eval_ref+1 hasta ayer (inclusive).
            # Si el usuario recayó en alguno de esos días (last_completed_date cae en el rango),
            # los días DESPUÉS de la recaída no cuentan.
            relapse_date = habit.last_completed_date  # None si nunca recayó

            survived_valid_days = 0
            check_date = eval_ref + timedelta(days=1)
            while check_date <= yesterday:
                if relapse_date and check_date == relapse_date:
                    # Recayó este día. No hay recompensa y la racha se reinicia.
                    habit.current_streak = 0
                elif str(check_date.weekday()) in habit.valid_days:
                    survived_valid_days += 1
                    habit.current_streak += 1
                check_date += timedelta(days=1)

            if survived_valid_days > 0:
                reward_map = {'S': 50, 'A': 25, 'B': 10, 'C': 5}
                prestige_gain = reward_map.get(
                    habit.difficulty, 5) * survived_valid_days
                movimientos.append((prestige_gain, 'habito_evitado', habit.name, habit.id))
                penalty_log.append(
                    f"Evitaste '{habit.name}' por {survived_valid_days} día(s) (+{prestige_gain} Prestigio).")

            # Avanza el marcador de evaluación a ayer
            habit.last_evaluated_date = yesterday
            habit.save()

        else:
            # --- BUENOS HÁBITOS: Penalizar por días válidos no completados ---
            # Solo penalizar si hay días no cubiertos entre la última evaluación y hoy.
            # La referencia real es el máximo entre last_evaluated_date y last_completed_date,
            # ya que completar un hábito "cubre" ese día.
            completed_ref = habit.last_completed_date or habit.created_at
            ref_date = max(eval_ref, completed_ref)
            delta = (today - ref_date).days

            if delta > 1:
                missed_valid_days = 0
                for i in range(1, delta):
                    check_date = ref_date + timedelta(days=i)
                    if str(check_date.weekday()) in habit.valid_days:
                        missed_valid_days += 1

                if missed_valid_days > 0:
                    prestige_loss = missed_valid_days * 15
                    movimientos.append(
                        (-prestige_loss, 'habito_incumplido', habit.name, habit.id))
                    habit.current_streak = 0
                    
                    coin_hierarchy = [
                        'marco', 'real', 'talento', 'iota', 'sueldo', 'drabin', 
                        'silver_penny', 'ardite', 'copper_penny', 'iron_penny', 'iron_half_penny'
                    ]
                    
                    coins_lost = []
                    for _ in range(missed_valid_days):
                        for coin in coin_hierarchy:
                            if getattr(guild, coin) > 0:
                                setattr(guild, coin, getattr(guild, coin) - 1)
                                coins_lost.append(coin)
                                break
                    
                    if coins_lost:
                        lost_counts = Counter(coins_lost)
                        lost_str = ", ".join(f"{count} {c.replace('_', ' ').title()}" for c, count in lost_counts.items())
                        penalty_log.append(
                            f"Hábito roto: '{habit.name}' (-{prestige_loss} Prestigio, -{lost_str}).")
                    else:
                        penalty_log.append(
                            f"Hábito roto: '{habit.name}' (-{prestige_loss} Prestigio).")

            habit.last_evaluated_date = yesterday
            habit.save()

    # --- EVALUACIÓN DEL CALENDARIO DE EVENTOS ---
    events = CalendarEvent.objects.filter(status__in=['PENDING', 'TODAY'])
    for event in events:
        if event.date == today and event.status == 'PENDING':
            event.status = 'TODAY'
            event.save()
            penalty_log.append(f"📅 El evento '{event.title}' es HOY.")
        elif event.date < today:
            # ponytail: expires without paying. Prestige for a past event used to be
            # random.randint(5, 15) with no attendance check — the cheapest prestige in the
            # project since the 2026-07-27 audit, and unauditable in a ledger because no row
            # could be reproduced from its cause. Attendance is confirmed now, not assumed.
            # Ceiling: an event you really attended pays nothing until you say so, from the
            # calendar with `m`. Upgrade: none needed unless confirming turns out to be a
            # chore nobody does.
            event.status = 'EXPIRED'
            event.save()
            penalty_log.append(f"📅 El evento '{event.title}' venció sin confirmar.")


    # Penalties first, then rewards, and never in row order. `add_prestige` crosses
    # `prestige_meta` against whatever balance it sees, so paying a gross reward before a
    # penalty the same sweep is about to charge can level the guild up on points it then
    # loses — and `prestige_level` only ever goes UP (nothing lowers it but `reset_guild`),
    # while it gates `max_adventurers` and every `req_prestige_level` upgrade. Applying every
    # negative first makes the balance climb monotonically to exactly the net, which is where
    # the single netted call this replaced used to leave it. `DailyHabit.objects.all()` has
    # no `Meta.ordering`, so without this sort the level a sweep grants depends on the order
    # Postgres happens to return rows in.
    for monto, fuente, detalle, ref in sorted(movimientos, key=lambda m: m[0]):
        guild.add_prestige(monto, fuente, detail=detalle, ref_id=ref)

    neto = sum(m[0] for m in movimientos)
    if neto < 0:
        penalty_log.append(
            f"El Gremio pierde influencia. (Impacto Neto: {neto})")

    # Each movement above already saved the guild, but the coin changes between them are
    # in memory only, and a sweep that moves no prestige at all saves nothing. Always save.
    guild.save()

    return penalty_log
