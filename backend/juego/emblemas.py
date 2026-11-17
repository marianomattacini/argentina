"""Emblemas propios de cada territorio.

Cada tarjeta de territorio muestra el emblema del municipio/provincia al que
pertenece (su lugar emblematico), en vez de uno sorteado al azar.

El campo "simbolo" se usa para el canje de tarjetas (3 iguales o 3 distintos):
    CONDOR     -> montanas, volcanes, glaciares, cordillera
    YAGUARETE  -> fauna, esteros, rios, selva, monte
    OBELISCO   -> ciudad, cultura, historia, vinos y produccion

Para editar o agregar un emblema alcanza con tocar los diccionarios de abajo:
    'clave en minusculas y sin tildes': (simbolo, 'Titulo visible', 'icono')
"""
import unicodedata


def _norm(texto):
    texto = unicodedata.normalize('NFD', str(texto or ''))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower().strip()


# ---------------------------------------------------------------------------
# Departamentos de Mendoza (mapa provincial por defecto)
# ---------------------------------------------------------------------------
EMBLEMAS_MENDOZA = {
    'capital': ('OBELISCO', 'Plaza Independencia y Cerro de la Gloria', '🏛️'),
    'godoy cruz': ('OBELISCO', 'Bodegas históricas de Godoy Cruz', '🍷'),
    'guaymallen': ('OBELISCO', 'Mercado Cooperativo de Guaymallén', '🥕'),
    'las heras': ('CONDOR', 'Aconcagua', '⛰️'),
    'lavalle': ('YAGUARETE', 'Lagunas de Guanacache', '🪶'),
    'lujan de cuyo': ('OBELISCO', 'Cuna del Malbec', '🍇'),
    'maipu': ('OBELISCO', 'Olivares y bodegas de Maipú', '🫒'),
    'san martin': ('OBELISCO', 'Viñedos del Este', '🍇'),
    'junin': ('OBELISCO', 'Chacras y viñas de Junín', '🍅'),
    'rivadavia': ('OBELISCO', 'Oasis del Este mendocino', '🌾'),
    'la paz': ('YAGUARETE', 'Río Desaguadero', '🌊'),
    'santa rosa': ('YAGUARETE', 'Reserva de Ñacuñán', '🌵'),
    'san carlos': ('CONDOR', 'Laguna del Diamante y Volcán Maipo', '🌋'),
    'tunuyan': ('CONDOR', 'Valle de Uco: viñedos de altura', '🏔️'),
    'tupungato': ('CONDOR', 'Volcán Tupungato', '🌋'),
    'san rafael': ('CONDOR', 'Cañón del Atuel', '🏞️'),
    'general alvear': ('OBELISCO', 'Ajo y vid del sur mendocino', '🧄'),
    'malargue': ('YAGUARETE', 'Laguna de Llancanelo y sus flamencos', '🦩'),
}

# ---------------------------------------------------------------------------
# Provincias (mapa nacional). Tambien se usan como emblema de respaldo para
# los departamentos de cualquier otra provincia en el mapa provincial.
# ---------------------------------------------------------------------------
EMBLEMAS_PROVINCIAS = {
    'jujuy': ('CONDOR', 'Cerro de los Siete Colores', '🌈'),
    'salta': ('OBELISCO', 'Tren a las Nubes', '🚂'),
    'formosa': ('YAGUARETE', 'Bañado La Estrella', '🐊'),
    'tucuman': ('OBELISCO', 'Casa Histórica de la Independencia', '🏛️'),
    'catamarca': ('OBELISCO', 'Virgen del Valle', '⛪'),
    'chaco': ('OBELISCO', 'Campo del Cielo', '☄️'),
    'misiones': ('YAGUARETE', 'Cataratas del Iguazú', '💦'),
    'corrientes': ('YAGUARETE', 'Esteros del Iberá', '🐊'),
    'santiago del estero': ('OBELISCO', 'Termas de Río Hondo', '♨️'),
    'la rioja': ('CONDOR', 'Parque Talampaya', '🏜️'),
    'santa fe': ('OBELISCO', 'Monumento a la Bandera', '🇦🇷'),
    'entre rios': ('OBELISCO', 'Carnaval de Gualeguaychú', '🎭'),
    'san juan': ('CONDOR', 'Valle de la Luna (Ischigualasto)', '🌙'),
    'cordoba': ('OBELISCO', 'Manzana Jesuítica', '⛪'),
    'mendoza': ('CONDOR', 'Aconcagua', '⛰️'),
    'san luis': ('CONDOR', 'Sierra de las Quijadas', '🦖'),
    'ciudad autonoma de buenos aires': ('OBELISCO', 'Obelisco Porteño', '🏛️'),
    'buenos aires': ('YAGUARETE', 'Pampa húmeda y gauchos', '🐎'),
    'la pampa': ('YAGUARETE', 'Parque Nacional Lihué Calel', '🌵'),
    'neuquen': ('CONDOR', 'Volcán Lanín', '🌋'),
    'rio negro': ('CONDOR', 'Lago Nahuel Huapi y Cerro Catedral', '🏔️'),
    'chubut': ('YAGUARETE', 'Ballenas de Península Valdés', '🐋'),
    'santa cruz': ('CONDOR', 'Glaciar Perito Moreno', '🧊'),
    'tierra del fuego, antartida e islas del atlantico sur': ('OBELISCO', 'Tren del Fin del Mundo', '🚂'),
    'islas malvinas': ('YAGUARETE', 'Pingüinos de las Malvinas', '🐧'),
}


def emblema_para_municipio(municipio):
    """Devuelve (simbolo, titulo, icono) del municipio, o None si no hay uno."""
    nombre = _norm(municipio.nombre)
    provincia = _norm(municipio.provincia.nombre)

    # Mapa nacional: el territorio ES la provincia.
    if nombre == provincia and nombre in EMBLEMAS_PROVINCIAS:
        return EMBLEMAS_PROVINCIAS[nombre]

    # Departamentos de Mendoza.
    if provincia == 'mendoza' and nombre in EMBLEMAS_MENDOZA:
        return EMBLEMAS_MENDOZA[nombre]

    # Departamentos de otras provincias: emblema de su provincia.
    return EMBLEMAS_PROVINCIAS.get(provincia)
