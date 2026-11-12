import random
from django.db.models import F
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import (
    Partida, Jugador, Provincia, Municipio, EstadoTablero,
    CartaTerritorio, Pregunta, OpcionRespuesta
)
from .serializers import PartidaSerializer, TriviaSerializer, CartaTerritorioSerializer, obtener_info_bioma

COLORES_DISPONIBLES = ['Rojo', 'Azul', 'Verde', 'Amarillo', 'Violeta', 'Naranja']

EMBLEMAS_ARGENTINOS = [
    ('CONDOR', 'Cóndor Andino', '🦅'),
    ('YAGUARETE', 'Yaguareté Misionero', '🐆'),
    ('OBELISCO', 'Obelisco Porteño', '🏛️'),
    ('COMODIN', 'Escarapela Nacional', '🇦🇷'),
]

TRAMPAS_Y_EVENTOS = [
    ('TRAMPA', 'PERDER_TURNO', 'Emboscada en Ruta Nacional', '⚠️', 'Carta Trampa: Perdés tu próximo turno por corte de suministros.'),
    ('TRAMPA', 'BLOQUEO_REFUERZOS', 'Bloqueo Aduanero', '🚧', 'Carta Trampa: Tus refuerzos quedan congelados durante 1 turno.'),
    ('TRAMPA', 'PERDIDA_ARMAS', 'Sabotaje de Polvorín', '💥', 'Carta Trampa: Perdés 1 o 2 tropas en tu territorio más fuerte.'),
    ('BOMBA', 'BOMBA_AEREA', 'Bomba Táctica Federal', '💣', 'Podés bombardear cualquier territorio enemigo del mapa (resta 1 a 3 tropas).'),
    ('ARMA', 'ARSENAL_EXTRA', 'Arsenal de Fabricaciones Militares', '🔫', 'Recibís +2 tropas de refuerzo inmediato.'),
]


def calcular_refuerzos(partida, jugador):
    cantidad_territorios = EstadoTablero.objects.filter(partida=partida, jugador=jugador).count()
    base = max(3, cantidad_territorios // 2)
    bonus_prov = 0
    for prov in Provincia.objects.all():
        total_prov = EstadoTablero.objects.filter(partida=partida, municipio__provincia=prov).count()
        if total_prov > 1:
            propios_prov = EstadoTablero.objects.filter(partida=partida, municipio__provincia=prov, jugador=jugador).count()
            if propios_prov == total_prov:
                bonus_prov += prov.bonus_ejercitos
    return base + bonus_prov


def otorgar_carta_nacional(partida, jugador, permitir_eventos=True):
    todas_celdas = list(EstadoTablero.objects.filter(partida=partida))
    if not todas_celdas:
        return None, None

    if permitir_eventos and random.random() < 0.35:
        tipo_carta, efecto_cod, titulo, icono, desc = random.choice(TRAMPAS_Y_EVENTOS)
        celda_ref = random.choice(todas_celdas)

        if tipo_carta == 'TRAMPA':
            mensaje_evento = f"{icono} <strong>¡CARTA TRAMPA! {titulo}</strong><br>{desc}"
            if efecto_cod == 'PERDER_TURNO':
                jugador.perder_turno = True
                jugador.save()
            elif efecto_cod == 'BLOQUEO_REFUERZOS':
                jugador.bloqueo_refuerzos = True
                jugador.save()
            elif efecto_cod == 'PERDIDA_ARMAS':
                fuerte = EstadoTablero.objects.filter(partida=partida, jugador=jugador, tropas__gte=2).order_by('-tropas').first()
                if fuerte:
                    baja = 2 if fuerte.tropas >= 5 else 1
                    fuerte.tropas -= baja
                    fuerte.save()
                    mensaje_evento += f" (-{baja} tropa(s) en {fuerte.municipio.nombre})"
            return None, mensaje_evento

        if tipo_carta == 'ARMA':
            jugador.tropas_disponibles += 2
            jugador.save()
            return None, f"{icono} <strong>¡HALLAZGO DE ARMAMENTO! {titulo}</strong><br>{desc}"

        if tipo_carta == 'BOMBA':
            carta_bomba = CartaTerritorio.objects.create(
                partida=partida,
                jugador=jugador,
                municipio=celda_ref.municipio,
                simbolo='COMODIN',
                tipo_carta='BOMBA',
                efecto_codigo='BOMBA_AEREA',
                emblema_titulo=titulo,
                emblema_icono=icono
            )
            return carta_bomba, f"{icono} <strong>¡ARMAMENTO ESPECIAL!</strong> Obtuviste una <strong>{titulo}</strong> para lanzar desde tu panel derecho."

    celdas_propias = [c for c in todas_celdas if c.jugador_id == jugador.id]
    elegida = random.choice(celdas_propias) if (celdas_propias and random.random() < 0.5) else random.choice(todas_celdas)
    simbolo, titulo, icono = random.choices(EMBLEMAS_ARGENTINOS, weights=[32, 32, 30, 6], k=1)[0]

    carta = CartaTerritorio.objects.create(
        partida=partida,
        jugador=jugador,
        municipio=elegida.municipio,
        simbolo=simbolo,
        tipo_carta='TERRITORIO',
        efecto_codigo='TERRITORIO_PROPIO' if elegida.jugador_id == jugador.id else '',
        emblema_titulo=titulo,
        emblema_icono=icono
    )
    return carta, None


def validar_autorizacion_turno(request, partida):
    if not partida.activa:
        return False, 'La partida ya finalizó'
    token = request.headers.get('X-Player-Token') or request.data.get('token')
    if token and partida.jugador_turno and partida.jugador_turno.token != token:
        return False, 'No estás autorizado para actuar en el turno de otro jugador'
    return True, None


class CrearPartidaAPIView(APIView):
    def post(self, request):
        nombre = request.data.get('nombre', 'Batalla Argentina: Estrategia Nacional')
        tipo_mapa = request.data.get('tipo_mapa', 'PROVINCIAL')
        modo_juego = request.data.get('modo_juego', 'VS_IA')
        privacidad = request.data.get('privacidad', 'ABIERTA')
        password = request.data.get('password', None)
        nombre_provincia = request.data.get('provincia', 'Mendoza')
        color_creador = request.data.get('color', 'Azul')

        try:
            tiempo_turno = int(request.data.get('tiempo_turno', 20))
        except (TypeError, ValueError):
            tiempo_turno = 20
        tiempo_turno = max(20, min(120, tiempo_turno))

        if privacidad == 'CERRADA' and not password:
            return Response({'error': 'Debés ingresar una contraseña para crear una sala cerrada'}, status=status.HTTP_400_BAD_REQUEST)

        if color_creador not in COLORES_DISPONIBLES:
            color_creador = 'Azul'

        partida = Partida(
            nombre=nombre,
            tipo_mapa=tipo_mapa,
            modo_juego=modo_juego,
            privacidad=privacidad,
            provincia_seleccionada=nombre_provincia,
            tiempo_turno=tiempo_turno
        )
        partida.set_password_segura(password if privacidad == 'CERRADA' else None)
        partida.save()

        nombres_jugadores = request.data.get('jugadores', ['Mariano'])
        colores_restantes = [c for c in COLORES_DISPONIBLES if c != color_creador]

        jugadores_creados = []
        for i, nom in enumerate(nombres_jugadores):
            color_j = color_creador if i == 0 else colores_restantes[(i - 1) % len(colores_restantes)]
            j = Jugador.objects.create(partida=partida, nombre=nom, color=color_j, orden=i, es_ia=False)
            jugadores_creados.append(j)

        if modo_juego == 'VS_IA':
            ia_jugador = Jugador.objects.create(
                partida=partida,
                nombre="Bot Belgrano (IA)",
                color=colores_restantes[0],
                orden=len(jugadores_creados),
                es_ia=True
            )
            jugadores_creados.append(ia_jugador)

        if tipo_mapa == 'PROVINCIAL':
            prov_obj, _ = Provincia.objects.get_or_create(nombre=nombre_provincia)
            municipios = list(
                Municipio.objects.filter(provincia=prov_obj)
                .exclude(nombre__iexact=nombre_provincia)
            )
            if not municipios:
                deptos_enviados = request.data.get('departamentos_provincia', [])
                nuevos_munis = []
                for nom_depto in deptos_enviados:
                    m, _ = Municipio.objects.get_or_create(nombre=nom_depto, provincia=prov_obj)
                    nuevos_munis.append(m)
                for idx, m in enumerate(nuevos_munis):
                    if idx > 0:
                        m.limites.add(nuevos_munis[idx - 1])
                    if idx < len(nuevos_munis) - 1:
                        m.limites.add(nuevos_munis[idx + 1])
                municipios = nuevos_munis
        else:
            municipios = list(Municipio.objects.filter(nombre=F('provincia__nombre')))

        random.shuffle(municipios)
        for i, muni in enumerate(municipios):
            j_asignado = jugadores_creados[i % len(jugadores_creados)]
            EstadoTablero.objects.create(partida=partida, municipio=muni, jugador=j_asignado, tropas=3)

        for jug in jugadores_creados:
            otorgar_carta_nacional(partida, jug, permitir_eventos=False)

        if jugadores_creados:
            primero = jugadores_creados[0]
            primero.tropas_disponibles = calcular_refuerzos(partida, primero)
            primero.save()
            partida.jugador_turno = primero
            partida.save()

        respuesta = PartidaSerializer(partida).data
        respuesta['mi_jugador_id'] = jugadores_creados[0].id
        respuesta['mi_token'] = jugadores_creados[0].token
        return Response(respuesta, status=status.HTTP_201_CREATED)


class UnirsePartidaAPIView(APIView):
    def post(self, request):
        codigo_sala = request.data.get('codigo_sala', '').strip().upper()
        password = request.data.get('password', '')
        nombre_jugador = request.data.get('nombre_jugador', '').strip()
        color_elegido = request.data.get('color', '')

        try:
            partida = Partida.objects.get(codigo_sala=codigo_sala)
        except Partida.DoesNotExist:
            return Response({'error': 'La sala indicada no existe'}, status=status.HTTP_404_NOT_FOUND)

        if not partida.verificar_password(password):
            return Response({'error': 'Contraseña incorrecta para ingresar a esta sala'}, status=status.HTTP_403_FORBIDDEN)

        jugador_actual = None
        if nombre_jugador:
            jugadores_existentes = list(partida.jugadores.all())
            existente = next((j for j in jugadores_existentes if j.nombre.lower() == nombre_jugador.lower()), None)
            if existente:
                jugador_actual = existente
            else:
                if len(jugadores_existentes) >= 8:
                    return Response({'error': 'La sala ya alcanzó el máximo de 8 jugadores'}, status=status.HTTP_400_BAD_REQUEST)

                colores_usados = {j.color for j in jugadores_existentes}
                if not color_elegido or color_elegido in colores_usados or color_elegido not in COLORES_DISPONIBLES:
                    libres = [c for c in COLORES_DISPONIBLES if c not in colores_usados]
                    color_elegido = libres[0] if libres else 'Verde'

                jugador_actual = Jugador.objects.create(
                    partida=partida,
                    nombre=nombre_jugador,
                    color=color_elegido,
                    orden=len(jugadores_existentes),
                    es_ia=False
                )

                todos_jugadores = list(partida.jugadores.filter(rendido=False).order_by('orden'))
                tablero = list(partida.tablero.all())
                random.shuffle(tablero)
                for idx, celda in enumerate(tablero):
                    celda.jugador = todos_jugadores[idx % len(todos_jugadores)]
                    celda.save()

                otorgar_carta_nacional(partida, jugador_actual, permitir_eventos=False)

                if partida.jugador_turno:
                    partida.jugador_turno.tropas_disponibles = calcular_refuerzos(partida, partida.jugador_turno)
                    partida.jugador_turno.save()

        respuesta = PartidaSerializer(partida).data
        if jugador_actual:
            respuesta['mi_jugador_id'] = jugador_actual.id
            respuesta['mi_token'] = jugador_actual.token
        return Response(respuesta)


class EstadoPartidaAPIView(APIView):
    def get(self, request, codigo_sala):
        try:
            partida = Partida.objects.get(codigo_sala=codigo_sala)
            return Response(PartidaSerializer(partida).data)
        except Partida.DoesNotExist:
            return Response({'error': 'Partida no encontrada'}, status=status.HTTP_404_NOT_FOUND)


class ReforzarTerritorioAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        municipio_id = request.data.get('municipio_id')
        cantidad = int(request.data.get('cantidad', 1))

        try:
            partida = Partida.objects.get(id=partida_id)
            celda = EstadoTablero.objects.get(partida=partida, municipio_id=municipio_id)
        except (Partida.DoesNotExist, EstadoTablero.DoesNotExist):
            return Response({'error': 'Territorio o partida no encontrados'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        jugador = partida.jugador_turno
        if celda.jugador != jugador:
            return Response({'error': 'Solo podés desplegar refuerzos en territorios propios'}, status=status.HTTP_400_BAD_REQUEST)

        if jugador.tropas_disponibles < cantidad or cantidad <= 0:
            return Response({'error': 'No tenés suficientes tropas de refuerzo disponibles'}, status=status.HTTP_400_BAD_REQUEST)

        celda.tropas += cantidad
        celda.save()
        jugador.tropas_disponibles -= cantidad
        jugador.save()

        return Response({
            'municipio': celda.municipio.nombre,
            'nuevas_tropas': celda.tropas,
            'tropas_disponibles': jugador.tropas_disponibles
        })


class MoverTropasAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        origen_id = request.data.get('origen_id')
        destino_id = request.data.get('destino_id')
        cantidad = int(request.data.get('cantidad', 1))

        try:
            partida = Partida.objects.get(id=partida_id)
            origen = EstadoTablero.objects.get(partida=partida, municipio_id=origen_id)
            destino = EstadoTablero.objects.get(partida=partida, municipio_id=destino_id)
        except (Partida.DoesNotExist, EstadoTablero.DoesNotExist):
            return Response({'error': 'Territorios no encontrados'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        jugador = partida.jugador_turno
        if origen.jugador != jugador or destino.jugador != jugador:
            return Response({'error': 'Ambos territorios deben ser propios para reagrupar tropas'}, status=status.HTTP_400_BAD_REQUEST)

        if not origen.municipio.limites.filter(id=destino_id).exists():
            return Response({'error': 'Solo podés reagrupar tropas entre territorios limítrofes'}, status=status.HTTP_400_BAD_REQUEST)

        info_bioma = obtener_info_bioma(origen.municipio.provincia.nombre)
        limite_movimientos = 3 if 'Llanura' in info_bioma['bioma'] else 1
        if jugador.reagrupamientos_turno >= limite_movimientos:
            return Response({
                'error': f'Ya alcanzaste el límite de {limite_movimientos} reagrupamiento(s) permitido(s) en este turno.'
            }, status=status.HTTP_400_BAD_REQUEST)

        if cantidad <= 0 or (origen.tropas - cantidad) < 1:
            return Response({'error': 'Debés dejar al menos 1 tropa en el territorio de origen'}, status=status.HTTP_400_BAD_REQUEST)

        origen.tropas -= cantidad
        destino.tropas += cantidad
        origen.save()
        destino.save()

        jugador.reagrupamientos_turno += 1
        jugador.save()

        return Response({
            'mensaje': f'Moviste {cantidad} tropa(s) de {origen.municipio.nombre} a {destino.municipio.nombre}',
            'origen_tropas': origen.tropas,
            'destino_tropas': destino.tropas,
            'reagrupamientos_restantes': max(0, limite_movimientos - jugador.reagrupamientos_turno)
        })


class CanjearCartasAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        cartas_ids = request.data.get('cartas_ids', [])

        try:
            partida = Partida.objects.get(id=partida_id)
        except Partida.DoesNotExist:
            return Response({'error': 'Partida no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        jugador = partida.jugador_turno
        if len(cartas_ids) != 3:
            return Response({'error': 'Debés seleccionar exactamente 3 cartas para realizar un canje'}, status=status.HTTP_400_BAD_REQUEST)

        cartas = list(CartaTerritorio.objects.filter(id__in=cartas_ids, partida=partida, jugador=jugador, canjeada=False, tipo_carta='TERRITORIO'))
        if len(cartas) != 3:
            return Response({'error': 'Las cartas seleccionadas no son válidas o ya fueron canjeadas'}, status=status.HTTP_400_BAD_REQUEST)

        simbolos_sin_comodin = [c.simbolo for c in cartas if c.simbolo != 'COMODIN']
        es_trio_igual = len(set(simbolos_sin_comodin)) <= 1
        es_trio_distinto = len(set(simbolos_sin_comodin)) == len(simbolos_sin_comodin)

        if not (es_trio_igual or es_trio_distinto):
            return Response({'error': 'Combinación inválida: necesitás 3 símbolos iguales, 3 distintos o usar una Escarapela Comodín'}, status=status.HTTP_400_BAD_REQUEST)

        escala_canje = [4, 7, 10, 15, 20]
        bonus_canje = escala_canje[jugador.canjes_realizados] if jugador.canjes_realizados < len(escala_canje) else (20 + (jugador.canjes_realizados - 4) * 5)

        bonus_territorio_propio = []
        for c in cartas:
            c.canjeada = True
            c.save()
            celda = EstadoTablero.objects.filter(partida=partida, municipio=c.municipio, jugador=jugador).first()
            if celda:
                celda.tropas += 2
                celda.save()
                bonus_territorio_propio.append(c.municipio.nombre)

        jugador.canjes_realizados += 1
        jugador.tropas_disponibles += bonus_canje
        jugador.save()

        return Response({
            'bonus_refuerzos': bonus_canje,
            'tropas_disponibles': jugador.tropas_disponibles,
            'bonus_territorios': bonus_territorio_propio
        })


class ElegirBeneficioCartaAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        carta_id = request.data.get('carta_id')
        beneficio = request.data.get('beneficio', 'TROPAS_EXTRA')

        try:
            partida = Partida.objects.get(id=partida_id)
            carta = CartaTerritorio.objects.get(id=carta_id, partida=partida, canjeada=False, tipo_carta='TERRITORIO')
        except (Partida.DoesNotExist, CartaTerritorio.DoesNotExist):
            return Response({'error': 'Carta no disponible'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        jugador = partida.jugador_turno
        if carta.jugador != jugador:
            return Response({'error': 'La carta no pertenece al jugador en turno'}, status=status.HTTP_403_FORBIDDEN)

        celda = EstadoTablero.objects.filter(partida=partida, municipio=carta.municipio, jugador=jugador).first()
        if not celda:
            return Response({'error': 'Solo podés activar este beneficio si ya conquistaste ese territorio'}, status=status.HTTP_400_BAD_REQUEST)

        detalle = ''
        if beneficio == 'TROPAS_EXTRA':
            celda.tropas += 3
            celda.save()
            detalle = f"Desplegaste +3 tropas inmediatas en {celda.municipio.nombre} (ahora tiene {celda.tropas})."
        elif beneficio == 'SABOTAJE':
            jugador.sabotaje_activo = True
            jugador.save()
            detalle = "Sabotaje activado: tu próximo ataque anula los beneficios defensivos del rival."
        elif beneficio == 'BLINDAJE':
            celda.blindado_turno = True
            celda.save()
            detalle = f"Fortificación activada: {celda.municipio.nombre} gana +2 en defensa hasta tu próximo turno."
        else:
            return Response({'error': 'Beneficio elegido no válido'}, status=status.HTTP_400_BAD_REQUEST)

        carta.canjeada = True
        carta.save()

        return Response({'mensaje': detalle, 'beneficio': beneficio})


class UsarBombaAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        carta_id = request.data.get('carta_id')
        destino_id = request.data.get('destino_id')

        try:
            partida = Partida.objects.get(id=partida_id)
            carta = CartaTerritorio.objects.get(id=carta_id, partida=partida, canjeada=False, tipo_carta='BOMBA')
            destino = EstadoTablero.objects.get(partida=partida, municipio_id=destino_id)
        except (Partida.DoesNotExist, CartaTerritorio.DoesNotExist, EstadoTablero.DoesNotExist):
            return Response({'error': 'Bomba o territorio objetivo no encontrados'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        jugador = partida.jugador_turno
        if carta.jugador != jugador:
            return Response({'error': 'No poseés esta bomba táctica'}, status=status.HTTP_403_FORBIDDEN)

        if destino.jugador == jugador:
            return Response({'error': 'No podés bombardear tus propios territorios'}, status=status.HTTP_400_BAD_REQUEST)

        bajas = min(destino.tropas - 1, random.randint(1, 3)) if destino.tropas > 1 else 0
        destino.tropas -= bajas
        destino.save()

        carta.canjeada = True
        carta.save()

        return Response({
            'destino': destino.municipio.nombre,
            'bajas': bajas,
            'tropas_restantes': destino.tropas
        })


class PrepararAtaqueAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        origen_id = request.data.get('origen_id')
        destino_id = request.data.get('destino_id')

        try:
            partida = Partida.objects.get(id=partida_id)
            estado_origen = EstadoTablero.objects.get(partida=partida, municipio_id=origen_id)
            estado_destino = EstadoTablero.objects.get(partida=partida, municipio_id=destino_id)
        except (Partida.DoesNotExist, EstadoTablero.DoesNotExist):
            return Response({'error': 'Datos de combate no válidos'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        if partida.jugador_turno.reagrupamientos_turno > 0:
            return Response({'error': 'Ya iniciaste la fase de reagrupamiento; no podés atacar en este turno'}, status=status.HTTP_400_BAD_REQUEST)

        if estado_origen.jugador != partida.jugador_turno:
            return Response({'error': 'No es el turno de este jugador'}, status=status.HTTP_400_BAD_REQUEST)

        if estado_origen.jugador == estado_destino.jugador:
            return Response({'error': 'No podés atacar tus propios territorios'}, status=status.HTTP_400_BAD_REQUEST)

        if estado_origen.tropas <= 1:
            return Response({'error': 'Se necesitan al menos 2 tropas para atacar'}, status=status.HTTP_400_BAD_REQUEST)

        es_limitrofe = estado_origen.municipio.limites.filter(id=destino_id).exists()
        if not es_limitrofe:
            return Response({'error': 'Los territorios no son limítrofes'}, status=status.HTTP_400_BAD_REQUEST)

        preguntas = list(Pregunta.objects.all())
        pregunta = random.choice(preguntas) if preguntas else None
        pregunta_data = TriviaSerializer(pregunta).data if pregunta else None

        trivia_obligatoria = bool(pregunta_data and random.random() < 0.35)
        info_destino = obtener_info_bioma(estado_destino.municipio.provincia.nombre)

        return Response({
            'valido': True,
            'origen': estado_origen.municipio.nombre,
            'destino': estado_destino.municipio.nombre,
            'trivia_obligatoria': trivia_obligatoria,
            'info_terreno': info_destino,
            'sabotaje_activo': estado_origen.jugador.sabotaje_activo,
            'blindado_destino': estado_destino.blindado_turno,
            'trivia': pregunta_data
        })


class ResolverCombateAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        origen_id = request.data.get('origen_id')
        destino_id = request.data.get('destino_id')
        modalidad = request.data.get('modalidad', 'DADOS')
        opcion_id = request.data.get('opcion_id', None)

        try:
            partida = Partida.objects.get(id=partida_id)
            estado_origen = EstadoTablero.objects.get(partida=partida, municipio_id=origen_id)
            estado_destino = EstadoTablero.objects.get(partida=partida, municipio_id=destino_id)
        except (Partida.DoesNotExist, EstadoTablero.DoesNotExist):
            return Response({'error': 'Error en los datos de la partida'}, status=status.HTTP_404_NOT_FOUND)

        ok, err = validar_autorizacion_turno(request, partida)
        if not ok:
            return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

        if partida.jugador_turno.reagrupamientos_turno > 0:
            return Response({'error': 'No podés atacar después de haber reagrupado tropas'}, status=status.HTTP_400_BAD_REQUEST)
        if estado_origen.jugador != partida.jugador_turno:
            return Response({'error': 'El territorio atacante no pertenece al jugador en turno'}, status=status.HTTP_400_BAD_REQUEST)
        if estado_origen.jugador == estado_destino.jugador:
            return Response({'error': 'No podés atacar tus propios territorios'}, status=status.HTTP_400_BAD_REQUEST)
        if estado_origen.tropas <= 1:
            return Response({'error': 'Se necesitan al menos 2 tropas para atacar'}, status=status.HTTP_400_BAD_REQUEST)
        if not estado_origen.municipio.limites.filter(id=destino_id).exists():
            return Response({'error': 'Los territorios no son limítrofes'}, status=status.HTTP_400_BAD_REQUEST)

        bonus_ataque = 0
        bonus_defensa = 0
        trivia_correcta = None
        notas_terreno = []

        if modalidad in ('TRIVIA', 'TRIVIA_OBLIGATORIA') and opcion_id:
            try:
                opcion = OpcionRespuesta.objects.get(id=opcion_id)
                if opcion.es_correcta:
                    trivia_correcta = True
                    bonus_ataque += 2 if modalidad == 'TRIVIA_OBLIGATORIA' else 1
                else:
                    trivia_correcta = False
                    bonus_defensa += 1
            except OpcionRespuesta.DoesNotExist:
                trivia_correcta = False
                bonus_defensa += 1

        info_bioma = obtener_info_bioma(estado_destino.municipio.provincia.nombre)
        atacante = estado_origen.jugador

        if atacante.sabotaje_activo:
            notas_terreno.append("🕵️ Sabotaje activo: se anularon las ventajas defensivas del rival.")
            atacante.sabotaje_activo = False
            atacante.save()
        else:
            if 'Cordillera' in info_bioma['bioma'] or 'Patagonia' in info_bioma['bioma']:
                bonus_defensa += 1
                notas_terreno.append(f"{info_bioma['icono']} {info_bioma['bioma']}: +1 defensa territorial.")
            elif 'Llanura' in info_bioma['bioma'] and estado_destino.tropas < 3:
                bonus_defensa -= 1
                notas_terreno.append(f"{info_bioma['icono']} Llanura abierta (<3 tropas): -1 defensa territorial.")

            if estado_destino.blindado_turno:
                bonus_defensa += 2
                notas_terreno.append("🛡️ Fortificación activa: +2 defensa en este territorio.")

        dado_ataque = max(1, random.randint(1, 6) + bonus_ataque)
        dado_defensa = max(1, random.randint(1, 6) + bonus_defensa)

        empate_selva = ('Selva' in info_bioma['bioma'] and dado_ataque == dado_defensa)
        gano_tirada = (dado_ataque > dado_defensa) and not empate_selva

        conquistado = False
        victoria_final = False
        ganador_nombre = None

        if gano_tirada:
            estado_destino.tropas -= 1
            if estado_destino.tropas <= 0:
                estado_destino.jugador = estado_origen.jugador
                estado_destino.tropas = 1
                estado_destino.blindado_turno = False
                estado_origen.tropas -= 1
                conquistado = True
                partida.conquisto_en_turno = True
                partida.save()
        else:
            baja_atacante = 1
            if 'Cordillera' in info_bioma['bioma'] and estado_origen.tropas >= 3:
                baja_atacante = 2
                notas_terreno.append("🏔️ Desgaste cordillerano: el atacante perdió 1 tropa adicional.")
            if empate_selva:
                notas_terreno.append("🌿 Emboscada en selva: el empate favoreció al defensor.")
            estado_origen.tropas = max(1, estado_origen.tropas - baja_atacante)

        estado_origen.save()
        estado_destino.save()

        if conquistado:
            rivales_restantes = EstadoTablero.objects.filter(partida=partida).exclude(jugador=estado_origen.jugador).exists()
            if not rivales_restantes:
                partida.activa = False
                partida.ganador = estado_origen.jugador
                partida.save()
                victoria_final = True
                ganador_nombre = estado_origen.jugador.nombre

        return Response({
            'modalidad': modalidad,
            'trivia_correcta': trivia_correcta,
            'dado_ataque': dado_ataque,
            'dado_defensa': dado_defensa,
            'resultado': 'victoria' if gano_tirada else 'derrota',
            'notas_terreno': notas_terreno,
            'conquistado': conquistado,
            'victoria_final': victoria_final,
            'ganador': ganador_nombre,
            'origen_tropas': estado_origen.tropas,
            'destino_tropas': estado_destino.tropas
        })


class RendirseAPIView(APIView):
    def post(self, request):
        partida_id = request.data.get('partida_id')
        jugador_id = request.data.get('jugador_id')

        try:
            partida = Partida.objects.get(id=partida_id)
            jugador = Jugador.objects.get(id=jugador_id, partida=partida)
        except (Partida.DoesNotExist, Jugador.DoesNotExist):
            return Response({'error': 'Jugador o partida no encontrados'}, status=status.HTTP_404_NOT_FOUND)

        token = request.headers.get('X-Player-Token') or request.data.get('token')
        if not token or jugador.token != token:
            return Response({'error': 'Token inválido o ausente para rendir a este jugador'}, status=status.HTTP_403_FORBIDDEN)

        jugador.rendido = True
        jugador.tropas_disponibles = 0
        jugador.save()

        activos = list(partida.jugadores.filter(rendido=False).order_by('orden'))
        if activos:
            celdas_rendido = list(EstadoTablero.objects.filter(partida=partida, jugador=jugador))
            for idx, celda in enumerate(celdas_rendido):
                celda.jugador = activos[idx % len(activos)]
                celda.save()

        victoria_final = False
        ganador_nombre = None
        if len(activos) <= 1:
            partida.activa = False
            if activos:
                partida.ganador = activos[0]
                ganador_nombre = activos[0].nombre
            victoria_final = True
        elif partida.jugador_turno == jugador:
            siguiente = activos[0]
            siguiente.reagrupamientos_turno = 0
            siguiente.tropas_disponibles = calcular_refuerzos(partida, siguiente)
            siguiente.save()
            partida.jugador_turno = siguiente

        partida.save()

        return Response({
            'derrotado': True,
            'jugador_derrotado': jugador.nombre,
            'victoria_final': victoria_final,
            'ganador': ganador_nombre
        })


class PasarTurnoAPIView(APIView):
    def post(self, request, partida_id):
        try:
            partida = Partida.objects.get(id=partida_id)
            
            # Si el turno es por tiempo agotado, permitimos la ejecución directa sin exigir token estricto del cliente
            por_tiempo = request.data.get('por_tiempo', False)
            if not por_tiempo:
                ok, err = validar_autorizacion_turno(request, partida)
                if not ok:
                    return Response({'error': err}, status=status.HTTP_403_FORBIDDEN)

            jugadores = list(partida.jugadores.filter(rendido=False).order_by('orden'))
            if not jugadores:
                return Response({'error': 'Sin jugadores activos'}, status=status.HTTP_400_BAD_REQUEST)

            jugador_saliente = partida.jugador_turno
            carta_ganada = None
            evento_carta = None

            if jugador_saliente:
                jugador_saliente.tropas_disponibles = 0
                jugador_saliente.reagrupamientos_turno = 0
                jugador_saliente.save()
                if partida.conquisto_en_turno:
                    nueva_carta, evento_carta = otorgar_carta_nacional(partida, jugador_saliente, permitir_eventos=True)
                    if nueva_carta:
                        carta_ganada = CartaTerritorioSerializer(nueva_carta).data

            partida.conquisto_en_turno = False

            idx_actual = jugadores.index(jugador_saliente) if jugador_saliente in jugadores else 0
            siguiente_idx = (idx_actual + 1) % len(jugadores)
            siguiente_jugador = jugadores[siguiente_idx]
            siguiente_jugador.reagrupamientos_turno = 0

            EstadoTablero.objects.filter(partida=partida, jugador=siguiente_jugador).update(blindado_turno=False)

            avisos_turno = []
            if siguiente_jugador.perder_turno:
                siguiente_jugador.perder_turno = False
                siguiente_jugador.save()
                avisos_turno.append(f"⚠️ {siguiente_jugador.nombre} perdió este turno por una Carta Trampa.")
                siguiente_idx = (siguiente_idx + 1) % len(jugadores)
                siguiente_jugador = jugadores[siguiente_idx]
                siguiente_jugador.reagrupamientos_turno = 0

            if siguiente_jugador.bloqueo_refuerzos:
                siguiente_jugador.bloqueo_refuerzos = False
                siguiente_jugador.tropas_disponibles = 0
                siguiente_jugador.save()
                avisos_turno.append(f"🚧 {siguiente_jugador.nombre} tiene refuerzos congelados este turno por Bloqueo Aduanero.")
            else:
                refuerzos = calcular_refuerzos(partida, siguiente_jugador)
                siguiente_jugador.tropas_disponibles = refuerzos
                siguiente_jugador.save()

            partida.jugador_turno = siguiente_jugador
            partida.save()

            acciones_ia = list(avisos_turno)

            # Si el siguiente jugador es la IA, ejecuta su turno automáticamente
            if siguiente_jugador.es_ia:
                propios_ia = list(EstadoTablero.objects.filter(partida=partida, jugador=siguiente_jugador))
                refuerzos_ia = siguiente_jugador.tropas_disponibles
                if propios_ia and refuerzos_ia > 0:
                    objetivo_ref = random.choice(propios_ia)
                    objetivo_ref.tropas += refuerzos_ia
                    objetivo_ref.save()
                    siguiente_jugador.tropas_disponibles = 0
                    siguiente_jugador.save()
                    acciones_ia.append(f"🛡️ {siguiente_jugador.nombre} desplegó +{refuerzos_ia} tropas de refuerzo en {objetivo_ref.municipio.nombre}.")

                ia_conquisto = False
                for _ in range(2):
                    propios_atacantes = list(
                        EstadoTablero.objects.filter(partida=partida, jugador=siguiente_jugador, tropas__gte=2)
                    )
                    random.shuffle(propios_atacantes)
                    ataque_realizado = False

                    for origen in propios_atacantes:
                        vecinos_ids = origen.municipio.limites.values_list('id', flat=True)
                        enemigos_vecinos = list(
                            EstadoTablero.objects.filter(partida=partida, municipio_id__in=vecinos_ids)
                            .exclude(jugador=siguiente_jugador)
                        )
                        if enemigos_vecinos:
                            destino = random.choice(enemigos_vecinos)
                            dado_ia = random.randint(1, 6)
                            dado_def = random.randint(1, 6)

                            if dado_ia > dado_def:
                                destino.tropas -= 1
                                if destino.tropas <= 0:
                                    destino.jugador = siguiente_jugador
                                    destino.tropas = 1
                                    origen.tropas -= 1
                                    ia_conquisto = True
                                    acciones_ia.append(
                                        f"🔥 {siguiente_jugador.nombre} atacó desde {origen.municipio.nombre} y CONQUISTÓ {destino.municipio.nombre} ({dado_ia} vs {dado_def})."
                                    )
                                else:
                                    acciones_ia.append(
                                        f"⚔️ {siguiente_jugador.nombre} atacó {destino.municipio.nombre} desde {origen.municipio.nombre} y te bajó 1 tropa ({dado_ia} vs {dado_def})."
                                    )
                            else:
                                origen.tropas -= 1
                                acciones_ia.append(
                                    f"🛡️ {siguiente_jugador.nombre} intentó atacar {destino.municipio.nombre} desde {origen.municipio.nombre}, pero lo frenaste en seco ({dado_ia} vs {dado_def})."
                                )

                            origen.save()
                            destino.save()
                            ataque_realizado = True
                            break

                    if not ataque_realizado:
                        break

                if ia_conquisto:
                    otorgar_carta_nacional(partida, siguiente_jugador, permitir_eventos=False)

                if not EstadoTablero.objects.filter(partida=partida).exclude(jugador=siguiente_jugador).exists():
                    partida.activa = False
                    partida.ganador = siguiente_jugador
                    partida.save()
                else:
                    # Devuelve el turno al humano automáticamente tras el turno de la IA
                    siguiente_idx = (siguiente_idx + 1) % len(jugadores)
                    humano_siguiente = jugadores[siguiente_idx]
                    humano_siguiente.reagrupamientos_turno = 0
                    humano_siguiente.tropas_disponibles = calcular_refuerzos(partida, humano_siguiente)
                    humano_siguiente.save()
                    partida.jugador_turno = humano_siguiente
                    partida.save()

            return Response({
                'turno_saliente_nombre': jugador_saliente.nombre if jugador_saliente else '',
                'jugo_ia': any(j.es_ia for j in jugadores),
                'nuevo_turno': partida.jugador_turno.nombre,
                'nuevo_turno_id': partida.jugador_turno.id,
                'nuevo_turno_es_ia': partida.jugador_turno.es_ia,
                'color': partida.jugador_turno.color,
                'tropas_disponibles': partida.jugador_turno.tropas_disponibles,
                'carta_ganada': carta_ganada,
                'evento_carta': evento_carta,
                'acciones_ia': acciones_ia,
                'victoria_final': not partida.activa,
                'ganador': partida.ganador.nombre if partida.ganador else None
            })
        except Partida.DoesNotExist:
            return Response({'error': 'Partida no encontrada'}, status=status.HTTP_404_NOT_FOUND)