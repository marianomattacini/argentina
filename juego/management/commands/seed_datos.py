from django.core.management.base import BaseCommand
from juego.models import Provincia, Municipio, MunicipioLimite, Trivia

class Command(BaseCommand):
    help = 'Pobla la base de datos con información inicial geográfica y trivias para Patria Grande'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Seed de Datos ---'))

        # 1. Carga de Provincias
        mendoza, _ = Provincia.objects.get_or_create(nombre='Mendoza', bonus_ejercitos=3)
        buenos_aires, _ = Provincia.objects.get_or_create(nombre='Buenos Aires', bonus_ejercitos=5)
        cordoba, _ = Provincia.objects.get_or_create(nombre='Córdoba', bonus_ejercitos=4)
        santa_fe, _ = Provincia.objects.get_or_create(nombre='Santa Fe', bonus_ejercitos=3)

        # 2. Carga de Municipios
        m1, _ = Municipio.objects.get_or_create(provincia=mendoza, nombre='Maipú', codigo_referencia='MND-MAIPU')
        m2, _ = Municipio.objects.get_or_create(provincia=mendoza, nombre='Luján de Cuyo', codigo_referencia='MND-LUJAN')
        m3, _ = Municipio.objects.get_or_create(provincia=mendoza, nombre='Guaymallén', codigo_referencia='MND-GUAYM')
        m4, _ = Municipio.objects.get_or_create(provincia=buenos_aires, nombre='La Matanza', codigo_referencia='BNS-MATAN')
        m5, _ = Municipio.objects.get_or_create(provincia=buenos_aires, nombre='La Plata', codigo_referencia='BNS-LPLAT')
        m6, _ = Municipio.objects.get_or_create(provincia=cordoba, nombre='Capital', codigo_referencia='CDB-CAPIT')

        # 3. Carga de Limites Bi-direccionales
        limites = [
            (m1, m2), (m1, m3), (m2, m3), # Mendoza
            (m4, m5), # Buenos Aires
        ]

        for orig, dest in limites:
            MunicipioLimite.objects.get_or_create(municipio_origen=orig, municipio_destino=dest)
            MunicipioLimite.objects.get_or_create(municipio_origen=dest, municipio_destino=orig)

        # 4. Carga de Trivias Iniciales
        Trivia.objects.get_or_create(
            categoria='GEOGRAFIA',
            campo_info='La Argentina cuenta con diversas regiones vitivinícolas de renombre internacional.',
            campo_gateway='¿En qué provincia se ubica el departamento de Maipú, conocido como la cuna del vino?',
            opcion_a='Mendoza',
            opcion_b='San Juan',
            opcion_c='Salto',
            opcion_d='La Rioja',
            opcion_correcta='A',
            campo_accion='Maipú es una de las regiones históricas vitivinícolas más importantes de la Provincia de Mendoza.'
        )

        Trivia.objects.get_or_create(
            categoria='HISTORIA',
            campo_info='El Cruce de los Andes fue una de las gestas militares más grandes de la historia sudamericana.',
            campo_gateway='¿Quién lideró el Ejército de los Andes desde la provincia de Mendoza?',
            opcion_a='Manuel Belgrano',
            opcion_b='José de San Martín',
            opcion_c='Mártin Miguel de Güemes',
            opcion_d='Cornelio Saavedra',
            opcion_correcta='B',
            campo_accion='El General José de San Martín organizó el Ejército de los Andes desde Mendoza entre 1814 y 1817.'
        )

        self.stdout.write(self.style.SUCCESS('--- Seed completado con éxito ---'))