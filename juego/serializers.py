from rest_framework import serializers
from .models import Partida, Jugador, EstadoTablero, CartaTerritorio, Pregunta, OpcionRespuesta

class JugadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jugador
        fields = ['id', 'nombre', 'color', 'es_ia', 'orden', 'tropas_disponibles', 'canjes_realizados']

class CartaTerritorioSerializer(serializers.ModelSerializer):
    municipio_id = serializers.IntegerField(source='municipio.id', read_only=True)
    municipio_nombre = serializers.CharField(source='municipio.nombre', read_only=True)
    jugador_id = serializers.IntegerField(source='jugador.id', read_only=True)

    class Meta:
        model = CartaTerritorio
        fields = [
            'id', 'jugador_id', 'municipio_id', 'municipio_nombre',
            'simbolo', 'emblema_titulo', 'emblema_icono', 'canjeada'
        ]

class EstadoTableroSerializer(serializers.ModelSerializer):
    municipio_id = serializers.IntegerField(source='municipio.id', read_only=True)
    municipio_nombre = serializers.CharField(source='municipio.nombre', read_only=True)
    provincia_nombre = serializers.CharField(source='municipio.provincia.nombre', read_only=True)
    jugador_id = serializers.IntegerField(source='jugador.id', read_only=True)
    jugador_nombre = serializers.CharField(source='jugador.nombre', read_only=True)
    jugador_color = serializers.CharField(source='jugador.color', read_only=True)

    class Meta:
        model = EstadoTablero
        fields = [
            'id', 'municipio_id', 'municipio_nombre', 'provincia_nombre',
            'jugador_id', 'jugador_nombre', 'jugador_color', 'tropas'
        ]

class PartidaSerializer(serializers.ModelSerializer):
    jugadores = JugadorSerializer(many=True, read_only=True)
    tablero = EstadoTableroSerializer(many=True, read_only=True)
    cartas = serializers.SerializerMethodField()
    jugador_turno_id = serializers.IntegerField(source='jugador_turno.id', read_only=True)
    jugador_turno_nombre = serializers.CharField(source='jugador_turno.nombre', read_only=True)
    jugador_turno_tropas = serializers.IntegerField(source='jugador_turno.tropas_disponibles', read_only=True)
    ganador_nombre = serializers.CharField(source='ganador.nombre', read_only=True, default=None)

    class Meta:
        model = Partida
        fields = [
            'id', 'nombre', 'codigo_sala', 'tipo_mapa', 'provincia_seleccionada',
            'modo_juego', 'privacidad', 'activa', 'conquisto_en_turno',
            'jugador_turno_id', 'jugador_turno_nombre', 'jugador_turno_tropas',
            'ganador_nombre', 'jugadores', 'tablero', 'cartas'
        ]

    def get_cartas(self, obj):
        activas = obj.cartas.filter(canjeada=False)
        return CartaTerritorioSerializer(activas, many=True).data

class OpcionRespuestaSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpcionRespuesta
        fields = ['id', 'texto']

class TriviaSerializer(serializers.ModelSerializer):
    opciones = OpcionRespuestaSerializer(many=True, read_only=True)

    class Meta:
        model = Pregunta
        fields = ['id', 'texto', 'categoria', 'dificultad', 'opciones']