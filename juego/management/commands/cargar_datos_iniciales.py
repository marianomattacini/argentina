from django.core.management.base import BaseCommand
from juego.models import Provincia, Municipio, Pregunta, OpcionRespuesta

class Command(BaseCommand):
    help = 'Siembra las 24 jurisdicciones + Islas Malvinas, departamentos de Mendoza y trivias'

    def handle(self, *args, **kwargs):
        self.stdout.write("Sembrando cartografía política y estratégica de Argentina...")

        # 1. Las 24 Jurisdicciones + Islas Malvinas (para el Mapa Nacional)
        jurisdicciones = [
            ("Jujuy", "NOA", 2),
            ("Salta", "NOA", 3),
            ("Formosa", "NEA", 2),
            ("Tucumán", "NOA", 2),
            ("Catamarca", "NOA", 2),
            ("Chaco", "NEA", 3),
            ("Misiones", "NEA", 2),
            ("Corrientes", "NEA", 3),
            ("Santiago del Estero", "NOA", 3),
            ("La Rioja", "Cuyo", 2),
            ("Santa Fe", "Centro", 4),
            ("Entre Ríos", "Centro", 3),
            ("San Juan", "Cuyo", 2),
            ("Córdoba", "Centro", 4),
            ("Mendoza", "Cuyo", 3),
            ("San Luis", "Cuyo", 2),
            ("Ciudad Autónoma de Buenos Aires", "Pampa", 2),
            ("Buenos Aires", "Pampa", 5),
            ("La Pampa", "Pampa", 2),
            ("Neuquén", "Patagonia", 3),
            ("Río Negro", "Patagonia", 3),
            ("Chubut", "Patagonia", 3),
            ("Santa Cruz", "Patagonia", 3),
            ("Tierra del Fuego, Antártida e Islas del Atlántico Sur", "Patagonia", 2),
            ("Islas Malvinas", "Patagonia", 2),
        ]

        objs_prov = {}
        objs_nac_territorios = {}

        for nombre, region, bonus in jurisdicciones:
            prov, _ = Provincia.objects.get_or_create(
                nombre=nombre,
                defaults={"region": region, "bonus_ejercitos": bonus}
            )
            objs_prov[nombre] = prov

            # Creamos un nodo territorial homónimo para el modo NACIONAL
            if nombre != "Mendoza":
                terr, _ = Municipio.objects.get_or_create(nombre=nombre, provincia=prov)
                objs_nac_territorios[nombre] = terr

        # Nodo nacional de Mendoza
        mendoza_prov = objs_prov["Mendoza"]
        mendoza_nac, _ = Municipio.objects.get_or_create(nombre="Mendoza", provincia=mendoza_prov)
        objs_nac_territorios["Mendoza"] = mendoza_nac

        # Limítrofes Nacionales Clave (incluyendo conexión marítima/aérea a Islas Malvinas desde Santa Cruz y Tierra del Fuego)
        limites_nacionales = [
            ("Jujuy", ["Salta"]),
            ("Salta", ["Formosa", "Chaco", "Santiago del Estero", "Tucumán", "Catamarca"]),
            ("Formosa", ["Chaco"]),
            ("Chaco", ["Santiago del Estero", "Santa Fe", "Corrientes"]),
            ("Misiones", ["Corrientes"]),
            ("Corrientes", ["Entre Ríos", "Santa Fe"]),
            ("Tucumán", ["Catamarca", "Santiago del Estero"]),
            ("Catamarca", ["La Rioja", "Córdoba", "Santiago del Estero"]),
            ("Santiago del Estero", ["Santa Fe", "Córdoba"]),
            ("La Rioja", ["San Juan", "San Luis", "Córdoba"]),
            ("San Juan", ["Mendoza", "San Luis"]),
            ("Mendoza", ["San Luis", "La Pampa", "Neuquén"]),
            ("San Luis", ["Córdoba", "La Pampa"]),
            ("Córdoba", ["Santa Fe", "Buenos Aires", "La Pampa"]),
            ("Santa Fe", ["Entre Ríos", "Buenos Aires"]),
            ("Entre Ríos", ["Buenos Aires"]),
            ("Buenos Aires", ["Ciudad Autónoma de Buenos Aires", "La Pampa", "Río Negro"]),
            ("La Pampa", ["Río Negro", "Neuquén"]),
            ("Neuquén", ["Río Negro"]),
            ("Río Negro", ["Chubut"]),
            ("Chubut", ["Santa Cruz"]),
            ("Santa Cruz", ["Tierra del Fuego, Antártida e Islas del Atlántico Sur", "Islas Malvinas"]),
            ("Tierra del Fuego, Antártida e Islas del Atlántico Sur", ["Islas Malvinas"]),
        ]

        for origen, vecinos in limites_nacionales:
            for v in vecinos:
                objs_nac_territorios[origen].limites.add(objs_nac_territorios[v])

        # 2. Los 18 Departamentos de Mendoza (Modo Provincial)
        deptos_mendoza = [
            "Capital", "Las Heras", "Guaymallén", "Godoy Cruz", "Maipú",
            "Luján de Cuyo", "San Martín", "Junín", "Rivadavia", "Santa Rosa",
            "La Paz", "Lavalle", "Tupungato", "Tunuyán", "San Carlos",
            "San Rafael", "General Alvear", "Malargüe"
        ]

        objs_mza = {}
        for d in deptos_mendoza:
            muni, _ = Municipio.objects.get_or_create(nombre=d, provincia=mendoza_prov)
            objs_mza[d] = muni

        limites_mendoza = [
            ("Capital", ["Las Heras", "Guaymallén", "Godoy Cruz"]),
            ("Godoy Cruz", ["Las Heras", "Guaymallén", "Maipú", "Luján de Cuyo"]),
            ("Guaymallén", ["Las Heras", "Lavalle", "Maipú"]),
            ("Las Heras", ["Lavalle", "Luján de Cuyo"]),
            ("Lavalle", ["San Martín", "Santa Rosa", "La Paz"]),
            ("Maipú", ["Luján de Cuyo", "San Martín", "Junín", "Rivadavia"]),
            ("Luján de Cuyo", ["Tupungato", "Rivadavia"]),
            ("San Martín", ["Junín", "Santa Rosa"]),
            ("Junín", ["Rivadavia", "Santa Rosa"]),
            ("Rivadavia", ["Santa Rosa", "San Carlos", "San Rafael"]),
            ("Santa Rosa", ["La Paz", "San Rafael"]),
            ("La Paz", ["San Rafael"]),
            ("Tupungato", ["Tunuyán"]),
            ("Tunuyán", ["San Carlos"]),
            ("San Carlos", ["San Rafael"]),
            ("San Rafael", ["General Alvear", "Malargüe"]),
        ]

        for origen, vecinos in limites_mendoza:
            for v in vecinos:
                objs_mza[origen].limites.add(objs_mza[v])

        self.stdout.write(self.style.SUCCESS("¡24 Jurisdicciones, Islas Malvinas y Departamentos sembrados!"))