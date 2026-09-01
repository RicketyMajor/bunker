"""El `create()` compartido de los tableros de deseos de cine y musica.

Los dos ViewSets eran la MISMA funcion escrita dos veces. Medido el 2026-08-31 diffando los dos
cuerpos normalizados: de 27 lineas, las unicas diferencias EJECUTABLES eran dos — el campo de
persona (`director` / `artist`) y una `a` de genero en el mensaje ('rechazada' / 'rechazado').
Todo lo demas era comentario. El resto de la variacion —modelo, watcher, serializador— ya viajaba
en atributos de clase, que es por lo que este corte es mecanico y no un rediseno.

⚠ **SON TRES TABLEROS, NO DOS.** `books/views.py:add_wishlist_item` hace exactamente estos tres
pasos y NO hereda de aqui: es una vista de funcion que construye el `WishlistItem` a mano en vez
de pasar por un serializador, asi que unificarla seria cambiarle la forma, no moverla. Un cambio
en la regla toca DOS ficheros desde hoy (este y el de libros), no uno. Contar dos y editar dos
fue como el 2026-08-31 se rompio el alta manual del movil: la regla vivia en tres sedes y la
revision conto las que se parecian entre si.
"""
from rest_framework import status
from rest_framework.response import Response

from bunker_core.dedup import desglosar, es_vigilado, ya_conocido


class GuardiaDeTablon:
    """Mixin de `create()`: descarta el duplicado y lo que no menciona a un vigilado.

    La clase que lo use declara `watcher_model`, `campo_persona` y `genero_rechazo`, y hereda de
    el ANTES que de `ModelViewSet` para que su `create` gane al de DRF.
    """

    #: El modelo de vigilados de ese tablon (`MovieWatcher`, `MusicWatcher`).
    watcher_model = None
    #: La clave del POST que trae a la persona: 'director' en cine, 'artist' en musica.
    campo_persona = None
    #: 'a' u 'o'. Concuerda con el sustantivo del tablon: la pelicula, el disco.
    genero_rechazo = 'o'

    def __init_subclass__(cls, **kwargs):
        """Falla CERRADO, y falla al importar.

        Sacar el nombre del campo a un atributo de clase creo una forma de que FALTE, que el
        `request.data.get('director')` literal de antes no tenia. Medido el 2026-08-31 sobre un
        tablon de prueba sin `campo_persona`: `request.data.get(None)` devuelve `None`, la puerta
        `persona is not None` no se cumple, la guardia se salta entera y la basura entra con
        **201**. Un fail-open silencioso, introducido por este mismo refactor.

        Va en `__init_subclass__` y no en `create()` a proposito: asi salta al IMPORTAR, donde lo
        ven `manage.py check`, `test_cli_imports` y las 18 suites, en vez de en el primer POST de
        un barrido nocturno.
        """
        super().__init_subclass__(**kwargs)
        faltan = [m for m in ('watcher_model', 'campo_persona', 'queryset')
                  if getattr(cls, m, None) is None]
        if faltan:
            raise TypeError(
                f"{cls.__name__} hereda de GuardiaDeTablon y no declara: {', '.join(faltan)}. "
                f"Sin eso la guardia de relevancia se salta EN SILENCIO y el tablon acepta todo.")

    def create(self, request, *args, **kwargs):
        title = request.data.get('title')

        if title:
            # Regla compartida (bunker_core/dedup.py): mismo numero de entrega Y base parecida.
            # Lee `.objects` SIN filtrar, asi que la lista negra tambien cuenta como conocido —
            # el `queryset` de la clase excluye `is_rejected`, y usarlo aqui resucitaria en el
            # siguiente barrido todo lo que se rechazo a mano.
            if ya_conocido(self.queryset.model.objects.all(), title):
                return Response(
                    {"message": f"'{title}' ya está en el radar o fue "
                                f"rechazad{self.genero_rechazo}. Ignorando."},
                    status=status.HTTP_200_OK,
                )

        # La sede unica de relevancia. Casa por titulo O por el campo de persona, y el segundo no
        # es un extra: los vigilados de cine son DIRECTORES y los de musica BANDAS, y un nombre
        # asi no aparece dentro del titulo. Medido el 2026-08-30 sobre las filas vivas: 10 de 13
        # en cine y 7 de 10 en musica NO mencionan a su vigilado en el titulo ('Incendies',
        # 'Arrival' y 'Dune' son de Villeneuve; 'Random Access Memories', 'Discovery' y
        # 'Homework', de Daft Punk). Un filtro que solo mirase ahi borraria los dos tableros.
        vigilados, exclusiones = desglosar(
            self.watcher_model.objects.filter(is_active=True)
            .values_list('keyword', 'exclusiones'))
        persona = request.data.get(self.campo_persona)
        # La guardia juzga la manguera del scraper, que SIEMPRE etiqueta (0 de 519 filas
        # producidas sin campo de persona). Un POST que OMITE el campo es un alta a mano desde el
        # movil (movil/app.js:571 postea solo {title}) y no se juzga: rechazarla devuelve 200, la
        # cola lo lee como transmitido y la fila se pierde en silencio.
        if vigilados and persona is not None and not es_vigilado(title, persona, vigilados,
                                                                 exclusiones):
            return Response({"message": "No menciona a ningún vigilado."},
                            status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)
