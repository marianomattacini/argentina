from django.db import models

class Provincia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    region = models.CharField(max_length=50, blank=True)

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

class OpcionRespuesta(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    texto = models.CharField(max_length=255)
    es_correcta = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.texto} ({'Correcta' if self.es_correcta else 'Incorrecta'})"