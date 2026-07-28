from django.core.management.base import BaseCommand

from posada.models import Achievement


class Command(BaseCommand):
    help = 'Siembra el catálogo de logros. Es idempotente: nunca toca los ya desbloqueados.'

    def handle(self, *args, **kwargs):
        # `metric` tiene que coincidir con una clave de los contadores que arma el BFF
        # (bunker_core/views.py). Añadir un logro es añadir una fila aquí y volver a correr
        # el comando; si necesita un contador nuevo, también una línea en el BFF.
        CATALOGO = [
            {
                "key": "lector_25", "name": "Lector Constante", "icon": "📚", "module": "books",
                "description": "25 libros leídos de principio a fin.",
                "metric": "books_read", "threshold": 25, "reward_prestige": 100,
            },
            {
                "key": "lector_100", "name": "Devorador de Tomos", "icon": "📖", "module": "books",
                "description": "100 libros leídos. La biblioteca ya no da abasto.",
                "metric": "books_read", "threshold": 100, "reward_prestige": 250,
            },
            {
                "key": "cinefilo_50", "name": "Cinéfilo", "icon": "🎬", "module": "movies",
                "description": "50 películas vistas del videoclub.",
                "metric": "movies_watched", "threshold": 50, "reward_prestige": 150,
            },
            {
                "key": "melomano_50", "name": "Melómano", "icon": "🎵", "module": "music",
                "description": "50 álbumes escuchados enteros.",
                "metric": "albums_listened", "threshold": 50, "reward_prestige": 150,
            },
            {
                "key": "enfoque_100", "name": "Mente de Acero", "icon": "🧠", "module": "posada",
                "description": "100 sesiones de Trabajo Profundo completadas.",
                "metric": "deep_work_sessions", "threshold": 100, "reward_prestige": 250,
            },
            {
                "key": "tactico_50", "name": "Táctico", "icon": "♟️", "module": "chess",
                "description": "50 puzzles tácticos resueltos.",
                "metric": "puzzles_solved", "threshold": 50, "reward_prestige": 150,
            },
            {
                "key": "racha_30", "name": "Disciplina de Hierro", "icon": "🔥", "module": "posada",
                "description": "Una racha de 30 días en un mismo hábito.",
                "metric": "habit_streak", "threshold": 30, "reward_prestige": 200,
            },
            {
                "key": "renacentista", "name": "Renacentista", "icon": "⚜️", "module": "bunker",
                "description": "Un libro, una película, un álbum, una sesión y un puzzle. "
                               "El único logro que no cabe dentro de un solo módulo.",
                "metric": "renacentista", "threshold": 1, "reward_prestige": 300,
            },
        ]

        self.stdout.write("Grabando la sala de trofeos del gremio...")
        creados = 0
        for data in CATALOGO:
            # update_or_create sin `unlocked_at` en defaults: re-sembrar actualiza textos y
            # recompensas, pero jamás vuelve a bloquear un logro ya conseguido.
            _, created = Achievement.objects.update_or_create(
                key=data["key"],
                defaults={k: v for k, v in data.items() if k != "key"},
            )
            if created:
                creados += 1

        huerfanos = Achievement.objects.exclude(key__in=[d["key"] for d in CATALOGO])
        borrados = huerfanos.count()
        if borrados:
            huerfanos.delete()
            self.stdout.write(self.style.WARNING(
                f'Se eliminaron {borrados} logros obsoletos.'))

        self.stdout.write(self.style.SUCCESS(
            f'Catálogo de logros al día: {len(CATALOGO)} en total, {creados} nuevos.'))
