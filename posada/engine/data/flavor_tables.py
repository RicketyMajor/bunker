"""Tablas de texto narrativo exclusivas del motor de sesiones.

Contiene los diccionarios de flavor text para exploración (skill checks,
consumibles) y combate (acciones de aventureros y monstruos).
"""

# --- TEXTOS NARRATIVOS DE EXPLORACIÓN: SKILL CHECKS ---
EVENT_TEXTS = {
    "Atletismo": [
        ("escalar un muro de roca suelta", "llega a la cima demostrando una fuerza bruta envidiable", "resbala y cae torpemente de espaldas"),
        ("mover una pesada columna caída", "la levanta con un rugido monumental de esfuerzo", "termina con un tirón muscular y la columna ni se mueve"),
        ("saltar sobre una profunda grieta", "cae firmemente al otro lado y sigue corriendo", "se queda corto y debe trepar agónicamente"),
    ],
    "Sigilo": [
        ("moverse sin hacer ruido entre la maleza", "pasa como una sombra indetectable", "pisa una rama seca que hace eco en toda la cueva"),
        ("pasar junto a unos guardias distraídos", "se desliza sin que ni siquiera sientan su presencia", "tira una jarra de metal por error"),
        ("esconderse detrás de unas cajas", "se funde perfectamente con las sombras del lugar", "deja medio cuerpo a la vista como un novato"),
    ],
    "Percepción": [
        ("agudizar sus sentidos buscando peligros", "nota unas tenues marcas de garras en la pared", "solo logra ver formas confusas en la oscuridad"),
        ("escuchar a través de una puerta de madera", "distingue los pasos pesados de una bestia del otro lado", "solo escucha su propio zumbido en los oídos"),
        ("revisar el techo en busca de amenazas", "avista a una criatura acechando entre estalactitas", "el polvo le entra a los ojos y no ve nada"),
    ],
    "Acrobacias": [
        ("cruzar un abismo sobre un tronco húmedo", "mantiene un equilibrio perfecto como un felino", "casi cae al vacío, recuperándose a duras penas"),
        ("deslizarse por debajo de una rampa", "pasa con elegancia rozando el suelo", "se atasca de hombros a la mitad del camino"),
        ("esquivar una trampa de cuchillas", "hace una voltereta grácil y sale ileso", "tropieza de boca y por suerte la cuchilla falla"),
    ],
    "Supervivencia": [
        ("buscar rastros frescos en la tierra", "identifica claramente hacia dónde fueron los monstruos", "pierde el rastro en el fango denso"),
        ("buscar bayas para recuperar energías", "encuentra frutos nutritivos en un arbusto", "se pincha con espinas tóxicas y no saca nada"),
        ("orientarse en la laberíntica cueva", "deduce correctamente el camino hacia el norte", "acaba dando un giro en círculos de 360 grados"),
    ],
    "Arcano": [
        ("intentar descifrar unas runas brillantes", "comprende el flujo de magia antigua", "le da dolor de cabeza al intentar leerlas"),
        ("identificar el origen de un aura mágica", "descubre la esencia evocadora del hechizo", "confunde la magia y siente pánico inútil"),
        ("detectar una ilusión en el pasillo", "parpadea y ve a través del engaño", "cree ciegamente en la falsa pared de ladrillos"),
    ],
    "Juego de Manos": [
        ("intentar forzar el cerrojo de un cofre viejo", "lo abre con un click maestro", "rompe su ganzúa dentro de la cerradura"),
        ("robar la llave del cinturón de un guardia dormido", "la obtiene suavemente con dos dedos", "hace tintinear las llaves despertando al guardia (casi)"),
        ("esconder un objeto valioso en su bota", "lo hace en un parpadeo mágico", "se le cae al suelo ruidosamente"),
    ],
    "Historia": [
        ("recordar a qué dinastía pertenece una estatua", "recuerda exactamente el nombre del rey antiguo", "la estatua está demasiado desgastada para saberlo"),
        ("hacer memoria sobre la guerra en este lugar", "deduce las tácticas que usaron los caídos", "mezcla leyendas con hechos y se confunde"),
        ("identificar un blasón en un escudo roto", "reconoce la noble familia extinta", "lo confunde con un garabato sin sentido"),
    ],
    "Religión": [
        ("identificar un altar profano", "reconoce los símbolos impíos de inmediato", "siente un escalofrío pero no logra descifrar nada"),
        ("rezar para apartar espíritus oscuros", "su deidad lo protege y el aire se purifica", "las deidades oscuras se ríen de su torpeza"),
        ("recordar el mito de creación del dios local", "recita un pasaje que revela un secreto de la cueva", "no puede recordar más allá de cantos de taberna"),
    ],
    "Medicina": [
        ("evaluar unas extrañas plantas pálidas", "descubre que sus hojas son cicatrizantes", "cree que son venenosas y prefiere no tocarlas"),
        ("examinar el cadáver de un aventurero", "determina con precisión cómo murió", "siente náuseas y tiene que apartar la vista"),
        ("vendar rápidamente un corte menor", "aplica presión y detiene el sangrado maravillosamente", "hace un nudo mal hecho que se deshace"),
    ],
    "Naturaleza": [
        ("identificar a una criatura subterránea", "reconoce sus debilidades y su hábitat", "no logra distinguirla de un animal común"),
        ("examinar el tipo de piedra de la cueva", "determina que la cueva es volcánica", "no tiene idea de geología"),
        ("predecir si habrá un sismo por los ruidos", "se siente seguro de que el túnel aguantará", "entra en pánico creyendo que colapsará"),
    ],
    "Intimidación": [
        ("amenazar a las sombras para que huyan", "gruñe y unas pequeñas ratas huyen despavoridas", "pega un grito que se quiebra en un gallo vergonzoso"),
        ("golpear su arma contra la pared", "las chispas asustan a los murciélagos", "rompe una parte de su empuñadura por bruto"),
    ],
    "Investigación": [
        ("buscar mecanismos ocultos en el suelo", "halla una baldosa que activa una trampa", "solo ve tierra y piedras inútiles"),
        ("deducir la combinación de un panel", "entiende el patrón lógico enseguida", "presiona botones al azar sin éxito"),
    ],
}


# --- TEXTOS NARRATIVOS DE CONSUMIBLES DE EXPLORACIÓN ---
FLAVOR_DATABASE = {
    "cuerda de escalada mágica": [
        "pronuncia una palabra de mando y la {item} se anuda sola en las alturas.",
        "observa cómo la {item} trepa por la pared como si fuera una serpiente."
    ],
    "cuerda": [
        "desenrolla su {item} para asegurar el descenso del grupo por una pendiente.",
        "lanza su {item} hacia una saliente alta, trepando para explorar un nivel superior.",
        "usa una {item} para amarrar firmemente una puerta sospechosa y evitar emboscadas."
    ],
    "ración": [
        "hace una pausa para consumir su {item}, recuperando aliento.",
        "comparte un pedazo de su {item} mientras revisa el mapa de la mazmorra."
    ],
    "antorcha": [
        "enciende una {item}, iluminando rincones oscuros y revelando un pasadizo.",
        "blande su {item} encendida para ahuyentar a una bandada de murciélagos molestos."
    ],
    "mapa": [
        "extiende un {item} antiguo sobre una roca, tratando de orientar la marcha de la party."
    ],
    "pala": [
        "usa su {item} para remover unos escombros del camino, buscando pasajes secretos."
    ],
    "odre": [
        "toma un largo trago de su {item}, refrescando su reseca garganta.",
        "vierte un poco de agua de su {item} para limpiar una vieja inscripción en la pared."
    ],
    "yesquero": [
        "hace saltar chispas de su {item} tratando de encender una fogata improvisada."
    ],
    "saco de dormir": [
        "desenrolla su {item}, preparando un sitio cómodo para el próximo descanso largo."
    ],
    "mochila": [
        "ajusta las correas de su {item} para distribuir mejor el peso del botín."
    ],
    "alforjas": [
        "revisa el contenido de sus {item}, organizando sus provisiones con cuidado."
    ],
    "saco": [
        "abre su {item} preparándolo para guardar las riquezas que encuentren."
    ],
    "tiza": [
        "marca una 'X' en la pared con su {item} para no perderse en el laberinto."
    ],
    "espejo": [
        "usa su {item} para espiar por la esquina del pasillo sin exponerse."
    ],
    "jabón": [
        "se frota un poco de {item} en las manos para quitarse la mugre de la mazmorra."
    ],
    "garfio": [
        "lanza hábilmente el {item}, enganchándolo en un balcón superior."
    ],
    "linterna": [
        "enciende su {item}, proyectando un cono de luz que perfora las tinieblas."
    ],
    "aceite": [
        "vierte su {item} sobre unas bisagras oxidadas para abrir la puerta sin ruido."
    ],
    "palanca": [
        "hace fuerza con su {item} para forzar la apertura de un cofre bloqueado."
    ],
    "pitones": [
        "clava unos {item} en la pared, creando asideros seguros para escalar."
    ],
    "martillo": [
        "da golpes precisos con su {item} comprobando la solidez del muro."
    ],
    "pluma": [
        "saca su {item}, preparándose para cartografiar el pasadizo."
    ],
    "tinta": [
        "destapa un {item} con cuidado de no manchar sus ropas."
    ],
    "pergamino": [
        "extiende un {item} liso y comienza a trazar un esquema del lugar."
    ],
    "campana": [
        "coloca una {item} atada a un hilo para alertar de cualquier movimiento nocturno."
    ],
    "catalejo": [
        "despliega su {item} y observa con detalle una estructura a la distancia."
    ],
    "herramientas de ladrón": [
        "saca sus {item} y se concentra en la compleja cerradura del portón."
    ],
    "disfraz": [
        "usa su {item} para ponerse una barba falsa y pasar desapercibido."
    ],
    "falsificación": [
        "revisa los sellos de cera en su {item} preparando un documento engañoso."
    ],
    "envenenador": [
        "extrae una aguja de su {item}, recubriéndola con una toxina mortal."
    ],
    "tienda": [
        "arma rápidamente su {item}, creando un refugio seguro para descansar."
    ],
    "poción de trepar": [
        "bebe la {item} y sus manos se vuelven pegajosas, permitiéndole subir por la pared."
    ],
    "fuego de alquimista": [
        "agita el {item}, amenazando con desatar un infierno de llamas verdes."
    ],
    "agua bendita": [
        "rocía un poco de {item} sobre un altar profano, purificando la zona."
    ],
    "piedra brillante": [
        "saca su {item} que emite una luz perpetua, guiando al grupo."
    ],
    "bolso de trucos": [
        "mete la mano en su {item} y extrae una pequeña bola peluda que pronto será un animal."
    ],
    "bolsa de contención": [
        "guarda un pesado escudo dentro de su {item} sin esfuerzo alguno."
    ],
    "escoba voladora": [
        "monta su {item}, flotando a un par de metros del suelo con elegancia."
    ],
    "gema de visión": [
        "mira a través de la {item}, revelando auras invisibles y trucos mágicos."
    ],
    "zurrón": [
        "piensa en un objeto y lo saca de inmediato de su {item} sin tener que buscar."
    ],
    "piedra de enviar": [
        "susurra un mensaje secreto a la {item}, esperando respuesta telepática."
    ],
    "manual de ganancia": [
        "lee unas páginas del {item}, sintiendo cómo sus músculos se tensan con nuevo vigor."
    ],
    "tomo de entendimiento": [
        "hojea el {item}, sus ojos brillando con una sabiduría celestial."
    ],
    "agujero portátil": [
        "extiende el {item} en el suelo, creando un pozo oscuro instantáneo."
    ],
    "alfombra voladora": [
        "se sienta cómodamente sobre su {item}, planeando suavemente por el corredor."
    ],
    "gema de control": [
        "sostiene en alto la {item}, que palpita con la furia reprimida de un elemental."
    ],
    "grilletes": [
        "hace sonar sus pesados {item}, listos para apresar a un enemigo resbaladizo."
    ],
    "mazo de muchas cosas": [
        "baraja el peligroso {item}, tentando al destino con una leve sonrisa."
    ],
    "esfera de aniquilación": [
        "manipula la {item} con sumo cuidado, temiendo que trague hasta la luz."
    ],
    "piedra filosofal": [
        "contempla la {item}, la joya definitiva que puede transmutar la realidad."
    ],
    "amuleto de los planos": [
        "ajusta el {item}, cuyo cristal parpadea con colores de otros mundos."
    ],
    "libro de la oscuridad vil": [
        "pasa una página del {item}, y las sombras de la habitación parecen susurrar."
    ],
    "elixir de inmortalidad": [
        "observa el dorado {item}, la promesa de una vida sin fin burbujeando dentro."
    ]
}
