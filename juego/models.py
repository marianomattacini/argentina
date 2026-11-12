import random
import string
import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password

def generar_codigo_sala():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generar_token_jugador():
    return uuid.uuid4().hex

class Provincia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=50, blank=True, default='')
    bonus_ejercitos = models.IntegerField(default=2)

    def __str__(self):
        return self.nombre

class Municipio(models.Model):
    nombre = models.CharField(max_length=100)
    provincia = models.ForeignKey(Provincia, on_delete=models.CASCADE, related_name='municipios')
    limites = models.ManyToManyField('self', symmetrical=True, blank=True)

    def __str__(self):
        return f"{self.nombre} ({self.provincia.nombre})"

class Pregunta(models.Model):
    DIFICULTAD_CHOICES = [
        ('facil', 'Fácil'),
        ('medio', 'Medio'),
        ('dificil', 'Difícil'),
    ]
    texto = models.TextField()
    categoria = models.CharField(max_length=50, default='Geografía e Historia')
    dificultad = models.CharField(max_length=10, choices=DIFICULTAD_CHOICES, default='medio')

    def __str__(self):
        return self.texto[:50]

Trivia = Pregunta

class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.texto} ({'Correcta' if self.es_correcta else 'Incorrecta'})"

class Partida(models.Model):
    TIPO_MAPA_CHOICES = [
        ('NACIONAL', 'Mapa Nacional (Provincias e Islas Malvinas)'),
        ('PROVINCIAL', 'Mapa Provincial (Departamentos)'),
    ]
    MODO_CHOICES = [
        ('VS_IA', '1 Jugador vs IA'),
        ('MULTIJUGADOR', 'Multijugador (2 a 8 Jugadores)'),
    ]
    PRIVACIDAD_CHOICES = [
        ('ABIERTA', 'Pública / Abierta'),
        ('CERRADA', 'Privada con Contraseña'),
    ]

    nombre = models.CharField(max_length=100, default="Batalla Argentina: Estrategia Nacional")
    codigo_sala = models.CharField(max_length=10, default=generar_codigo_sala, unique=True)
    tipo_mapa = models.CharField(max_length=20, choices=TIPO_MAPA_CHOICES, default='PROVINCIAL')
    provincia_seleccionada = models.CharField(max_length=100, blank=True, null=True, default='Mendoza')
    modo_juego = models.CharField(max_length=20, choices=MODO_CHOICES, default='VS_IA')
    privacidad = models.CharField(max_length=10, choices=PRIVACIDAD_CHOICES, default='ABIERTA')
    password = models.CharField(max_length=128, blank=True, null=True)
    
    creada_en = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    conquisto_en_turno = models.BooleanField(default=False)
    jugador_turno = models.ForeignKey('Jugador', on_delete=models.SET_NULL, null=True, blank=True, related_name='turnos_activos')
    ganador = models.ForeignKey('Jugador', on_delete=models.SET_NULL, null=True, blank=True, related_name='partidas_ganadas')

    def set_password_segura(self, raw_password):
        if raw_password:
            self.password = make_password(raw_password)
        else:
            self.password = None

    def verificar_password(self, raw_password):
        if self.privacidad != 'CERRADA':
            return True
        if not self.password or not raw_password:
            return False
        if self.password.startswith(('pbkdf2_', 'argon2$', 'bcrypt')):
            return check_password(raw_password, self.password)
        return self.password == raw_password

    def __str__(self):
        return f"Sala #{self.codigo_sala} - {self.nombre} ({self.privacidad})"

class Jugador(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='jugadores')
    nombre = models.CharField(max_length=50)
    color = models.CharField(max_length=20, default="Rojo")
    es_ia = models.BooleanField(default=False)
    orden = models.IntegerField(default=0)
    tropas_disponibles = models.IntegerField(default=0)
    canjes_realizados = models.IntegerField(default=0)
    token = models.CharField(max_length=64, default=generar_token_jugador)

    def __str__(self):
        return f"{self.nombre} {'(IA)' if self.es_ia else ''} - {self.color}"

class EstadoTablero(models.Model):
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='tablero')
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, null=True, blank=True)
    tropas = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.municipio.nombre} - {self.jugador.nombre if self.jugador else 'Libre'} ({self.tropas} tropas)"

class CartaTerritorio(models.Model):
    SIMBOLO_CHOICES = [
        ('CONDOR', 'Cóndor Andino (Fauna)'),
        ('YAGUARETE', 'Yaguareté (Fauna)'),
        ('OBELISCO', 'Obelisco / Monumento (Ciudad)'),
        ('COMODIN', 'Escarapela Nacional (Comodín)'),
    ]
    partida = models.ForeignKey(Partida, on_delete=models.CASCADE, related_name='cartas')
    jugador = models.ForeignKey(Jugador, on_delete=models.CASCADE, related_name='cartas')
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    simbolo = models.CharField(max_length=20, choices=SIMBOLO_CHOICES)
    emblema_titulo = models.CharField(max_length=100)
    emblema_icono = models.CharField(max_length=16, default='🇦🇷')
    canjeada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.municipio.nombre} [{self.simbolo}] - {self.jugador.nombre}"