from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Partida, Jugador, Provincia, Municipio, EstadoTablero, CartaTerritorio, Pregunta, OpcionRespuesta

REGIONES_BIOMAS = {
    'Mendoza': {
        'bioma': 'Cordillera y Alta Montaña',
        'icono': '🏔️',
        'beneficio_def': '+1 defensa territorial y desgaste cordillerano',
        'perjuicio_ataq': 'Si el atacante pierde con >=3 tropas, sufre -1 tropa extra por altura'
    },
    'San Juan': {
        'bioma': 'Cordillera y Alta Montaña',
        'icono': '🏔️',
        'beneficio_def': '+1 defensa territorial y desgaste cordillerano',
        'perjuicio_ataq': 'Si el atacante pierde con >=3 tropas, sufre -1 tropa extra por altura'
    },
    'Neuquén': {
        'bioma': 'Cordillera y Alta Montaña',
        'icono': '🏔️',
        'beneficio_def': '+1 defensa territorial y desgaste cordillerano',
        'perjuicio_ataq': 'Si el atacante pierde con >=3 tropas, sufre -1 tropa extra por altura'
    },
    'Río Negro': {
        'bioma': 'Patagonia Austral y Viento',
        'icono': '❄️',
        'beneficio_def': '+1 defensa por clima patagónico extremo',
        'perjuicio_ataq': 'Bajas por frío si el asalto fracasa'
    },
    'Chubut': {
        'bioma': 'Patagonia Austral y Viento',
        'icono': '❄️',
        'beneficio_def': '+1 defensa por clima patagónico extremo',
        'perjuicio_ataq': 'Bajas por frío si el asalto fracasa'
    },
    'Santa Cruz': {
        'bioma': 'Patagonia Austral y Viento',
        'icono': '❄️',
        'beneficio_def': '+1 defensa por clima patagónico extremo',
        'perjuicio_ataq': 'Bajas por frío si el asalto fracasa'
    },
    'Tierra del Fuego, Antártida e Islas del Atlántico Sur': {
        'bioma': 'Patagonia Austral y Viento',
        'icono': '❄️',
        'beneficio_def': '+1 defensa por clima patagónico extremo',
        'perjuicio_ataq': 'Bajas por frío si el asalto fracasa'
    },
    'Misiones': {
        'bioma': 'Selva Subtropical y Monte',
        'icono': '🌿',
        'beneficio_def': 'Empate de dados favorece al defensor (emboscada)',
        'perjuicio_ataq': 'Visibilidad reducida en selva cerrada'
    },
    'Corrientes': {
        'bioma': 'Selva Subtropical y Monte',
        'icono': '🌿',
        'beneficio_def': 'Empate de dados favorece al defensor (esteros)',
        'perjuicio_ataq': 'Avance lento en esteros'
    },
    'Formosa': {
        'bioma': 'Selva Subtropical y Monte',
        'icono': '🌿',
        'beneficio_def': 'Empate de dados favorece al defensor',
        'perjuicio_ataq': 'Terreno de monte cerrado'
    },
    'Chaco': {
        'bioma': 'Selva Subtropical y Monte',
        'icono': '🌿',
        'beneficio_def': 'Empate de dados favorece al defensor',
        'perjuicio_ataq': 'Terreno de monte cerrado'
    },
    'Jujuy': {
        'bioma': 'Puna y Quebradas del Norte',
        'icono': '🌵',
        'beneficio_def': '+1 defensa en pasos de quebrada',
        'perjuicio_ataq': 'Terreno escarpado de altura'
    },
    'Salta': {
        'bioma': 'Puna y Quebradas del Norte',
        'icono': '🌵',
        'beneficio_def': '+1 defensa en pasos de quebrada',
        'perjuicio_ataq': 'Terreno escarpado de altura'
    },
    'Catamarca': {
        'bioma': 'Puna y Quebradas del Norte',
        'icono': '🌵',
        'beneficio_def': '+1 defensa en pasos de quebrada',
        'perjuicio_ataq': 'Terreno escarpado de altura'
    },
    'La Rioja': {
        'bioma': 'Puna y Quebradas del Norte',
        'icono': '🌵',
        'beneficio_def': '+1 defensa en pasos de quebrada',
        'perjuicio_ataq': 'Terreno escarpado de altura'
    },
}

DEFAULT_BIOMA = {
    'bioma': 'Llanura Pampeana y Litoral',
    'icono': '🌾',
    'beneficio_def': 'Sin defensa natural extra (-1 si tiene <3 tropas)',
    'perjuicio_ataq': 'Permite hasta 3 reagrupamientos tácticos por turno'
}


def obtener_info_bioma(nombre_provincia):
    return REGIONES_BIOMAS.get(nombre_provincia, DEFAULT_BIOMA)


class OpcionRespuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ['id', 'texto']


class TriviaSerializer(serializers.ModelSerializer):
    opciones = OpcionRespuestaSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = ['id', 'texto', 'categoria', 'dificultad', 'opciones']


class JugadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jugador
        fields = ['id', 'nombre', 'color', 'es_ia', 'orden', 'tropas_disponibles', 'reagrupamientos_turno', 'sabotaje_activo', 'rendido']


class EstadoTableroSerializer(serializers.ModelSerializer):
    municipio_id = serializers.IntegerField(source='municipio.id')
    municipio_nombre = serializers.CharField(source='municipio.nombre')
    provincia_nombre = serializers.CharField(source='municipio.provincia.nombre')
    jugador_id = serializers.IntegerField(source='jugador.id', allow_null=True)
    jugador_nombre = serializers.CharField(source='jugador.nombre', allow_null=True)
    jugador_color = serializers.CharField(source='jugador.color', allow_null=True)
    info_terreno = serializers.SerializerMethodField()

    class Meta:
        model = EstadoTablero
        fields = [
            'id', 'municipio_id', 'municipio_nombre', 'provincia_nombre',
            'jugador_id', 'jugador_nombre', 'jugador_color', 'tropas', 'blindado_turno', 'info_terreno'
        ]

    def get_info_terreno(self, obj):
        return obtener_info_bioma(obj.municipio.provincia.nombre)


class CartaTerritorioSerializer(serializers.ModelSerializer):
    municipio_id = serializers.IntegerField(source='municipio.id')
    municipio_nombre = serializers.CharField(source='municipio.nombre')
    jugador_id = serializers.IntegerField(source='jugador.id')

    class Meta:
        model = CartaTerritorio
        fields = [
            'id', 'municipio_id', 'municipio_nombre', 'jugador_id',
            'simbolo', 'tipo_carta', 'efecto_codigo', 'emblema_titulo', 'emblema_icono', 'canjeada'
        ]


class PartidaSerializer(serializers.ModelSerializer):
    jugadores = JugadorSerializer(many=True, read_only=True)
    tablero = EstadoTableroSerializer(many=True, read_only=True)
    cartas = CartaTerritorioSerializer(many=True, read_only=True)
    jugador_turno_id = serializers.IntegerField(source='jugador_turno.id', allow_null=True)
    jugador_turno_nombre = serializers.CharField(source='jugador_turno.nombre', allow_null=True)
    jugador_turno_tropas = serializers.IntegerField(source='jugador_turno.tropas_disponibles', default=0)
    jugador_turno_reagrupamientos = serializers.IntegerField(source='jugador_turno.reagrupamientos_turno', default=0)
    jugador_turno_limite_reagrupamientos = serializers.SerializerMethodField()
    ganador_nombre = serializers.CharField(source='ganador.nombre', allow_null=True)
    segundos_restantes = serializers.SerializerMethodField()

    def get_segundos_restantes(self, obj):
        if not obj.iniciada or not obj.turno_inicio or not obj.activa:
            return obj.tiempo_turno
        vencimiento = obj.turno_inicio + timedelta(seconds=obj.tiempo_turno)
        return max(0, int((vencimiento - timezone.now()).total_seconds() + 0.999))

    class Meta:
        model = Partida
        fields = [
            'id', 'nombre', 'codigo_sala', 'tipo_mapa', 'provincia_seleccionada',
            'modo_juego', 'privacidad', 'tiempo_turno', 'activa', 'iniciada',
            'turno_inicio', 'segundos_restantes', 'jugador_turno_id',
            'jugador_turno_nombre', 'jugador_turno_tropas', 'jugador_turno_reagrupamientos',
            'jugador_turno_limite_reagrupamientos', 'ganador_nombre',
            'jugadores', 'tablero', 'cartas'
        ]

    def get_jugador_turno_limite_reagrupamientos(self, obj):
        if obj.tipo_mapa == 'PROVINCIAL' and obj.provincia_seleccionada:
            info = obtener_info_bioma(obj.provincia_seleccionada)
            return 3 if 'Llanura' in info['bioma'] else 1
        return 1