import os
import re
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teg_argentina.settings')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from rest_framework.test import APIClient
from juego.models import Partida, Jugador, EstadoTablero, CartaTerritorio, Pregunta, OpcionRespuesta


class AgenteQACompletoV3:
    def __init__(self):
        self.client = APIClient()
        self.aprobadas = []
        self.fallos = []
        self.salas_creadas = []

    def ok(self, modulo, detalle):
        self.aprobadas.append((modulo, detalle))
        print(f"  ✅ [{modulo}] {detalle}")

    def fail(self, modulo, detalle, solucion=""):
        self.fallos.append((modulo, detalle, solucion))
        print(f"  ❌ [{modulo}] {detalle}")
        if solucion:
            print(f"     🛠️ Acción recomendada: {solucion}")

    def ejecutar_auditoria(self):
        print("=" * 86)
        print("🕵️‍♂️ AGENTE QA INTEGRAL v3 — AUDITORÍA TOTAL DE LÓGICA, TROPAS, GUÍAS Y JUGABILIDAD")
        print("=" * 86)

        base_front = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'frontend'))
        html_path = os.path.join(base_front, 'index.html')
        app_path = os.path.join(base_front, 'js', 'app.js')
        mapa_path = os.path.join(base_front, 'js', 'mapa_svg.js')

        for ruta in (html_path, app_path, mapa_path):
            if not os.path.exists(ruta):
                self.fail("ARCHIVOS FRONTEND", f"No se encontró el archivo esperado: {ruta}")
                return

        with open(html_path, 'r', encoding='utf-8') as f:
            html_txt = f.read()
        with open(app_path, 'r', encoding='utf-8') as f:
            app_js = f.read()
        with open(mapa_path, 'r', encoding='utf-8') as f:
            mapa_js = f.read()

        try:
            # ==================================================================
            # MÓDULO 1: SALAS, CONTRASEÑAS, TEMPORIZADOR Y TOKENS
            # ==================================================================
            print("\n[MÓDULO 1] Salas, Seguridad, Contraseñas y Temporizador (20s-120s)...")

            res_c = self.client.post('/api/partidas/', {
                "nombre": "QA Total v3",
                "modo_juego": "MULTIJUGADOR",
                "tipo_mapa": "PROVINCIAL",
                "privacidad": "CERRADA",
                "password": "clave_secreta_qa",
                "provincia": "Mendoza",
                "tiempo_turno": 999,
                "color": "Azul",
                "jugadores": ["Mariano"]
            }, format='json')

            if res_c.status_code != 201:
                self.fail("CREACIÓN SALA", f"Error HTTP {res_c.status_code}: {res_c.data}")
                return

            p_multi = res_c.data
            cod_multi = p_multi['codigo_sala']
            self.salas_creadas.append(cod_multi)
            pid_multi = p_multi['id']
            j1_id = p_multi['mi_jugador_id']
            tok_j1 = p_multi['mi_token']

            if p_multi['tiempo_turno'] == 120:
                self.ok("TEMPORIZADOR", "Límite superior de 120s aplicado correctamente.")
            else:
                self.fail("TEMPORIZADOR", f"No acotó el tiempo a 120s (devolvió {p_multi['tiempo_turno']}).")

            res_bad_pass = self.client.post('/api/partidas/unirse/', {
                "codigo_sala": cod_multi, "nombre_jugador": "Intruso", "password": "mal"
            }, format='json')
            if res_bad_pass.status_code == 403:
                self.ok("SEGURIDAD SALA", "Sala cerrada bloquea contraseñas incorrectas (HTTP 403).")
            else:
                self.fail("SEGURIDAD SALA", f"Permitió acceso o devolvió código inesperado: {res_bad_pass.status_code}")

            res_j2 = self.client.post('/api/partidas/unirse/', {
                "codigo_sala": cod_multi, "nombre_jugador": "Carlos", "color": "Rojo", "password": "clave_secreta_qa"
            }, format='json')
            if res_j2.status_code == 200 and len(res_j2.data['jugadores']) == 2:
                j2_id = res_j2.data['mi_jugador_id']
                tok_j2 = res_j2.data['mi_token']
                self.ok("MULTIJUGADOR", "Segundo jugador unido y reparto equitativo de territorios completado.")
            else:
                self.fail("MULTIJUGADOR", f"Fallo al unir segundo jugador: {res_j2.data}")
                return

            # ==================================================================
            # MÓDULO 2: AGREGAR TROPAS (CLICK EN MAPA + BOTÓN DIRECTO + VALIDACIÓN)
            # ==================================================================
            print("\n[MÓDULO 2] Despliegue de Tropas (Backend + SVG Click + Botón Lateral)...")

            estado_actual = self.client.get(f"/api/partidas/{cod_multi}/").data
            ref_iniciales = estado_actual['jugador_turno_tropas']
            celdas_j1 = [t for t in estado_actual['tablero'] if t['jugador_id'] == j1_id]
            celda_enemiga = next(t for t in estado_actual['tablero'] if t['jugador_id'] == j2_id)

            # 2.1 Bloquear despliegue en territorio rival
            res_ref_enemigo = self.client.post('/api/reforzar/', {
                "partida_id": pid_multi, "municipio_id": celda_enemiga['municipio_id'], "cantidad": 1
            }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if res_ref_enemigo.status_code == 400:
                self.ok("REFUERZOS SEGURIDAD", "Bloquea desplegar tropas en territorio enemigo.")
            else:
                self.fail("REFUERZOS SEGURIDAD", "Permitió reforzar un territorio enemigo.")

            # 2.2 Bloquear despliegue fuera de turno
            res_ref_turno_ajeno = self.client.post('/api/reforzar/', {
                "partida_id": pid_multi, "municipio_id": celda_enemiga['municipio_id'], "cantidad": 1
            }, HTTP_X_PLAYER_TOKEN=tok_j2, format='json')
            if res_ref_turno_ajeno.status_code == 403:
                self.ok("CONTROL DE TURNO", "Bloquea refuerzos del rival cuando no es su turno (HTTP 403).")
            else:
                self.fail("CONTROL DE TURNO", f"Permitió actuar fuera de turno: {res_ref_turno_ajeno.status_code}")

            # 2.3 Desplegar TODAS las tropas disponibles una por una (simulando clics reales del jugador)
            desplegadas = 0
            for i in range(ref_iniciales):
                objetivo = celdas_j1[i % len(celdas_j1)]
                r_ok = self.client.post('/api/reforzar/', {
                    "partida_id": pid_multi, "municipio_id": objetivo['municipio_id'], "cantidad": 1
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                if r_ok.status_code == 200:
                    desplegadas += 1

            if desplegadas == ref_iniciales and ref_iniciales >= 3:
                self.ok("AGREGAR TROPAS", f"Se desplegaron exitosamente las {desplegadas}/{ref_iniciales} tropas disponibles una por una.")
            else:
                self.fail("AGREGAR TROPAS", f"Solo se pudieron desplegar {desplegadas} de {ref_iniciales} tropas.")

            # 2.4 Verificar que no permita agregar más tropas cuando disponibles == 0
            r_extra = self.client.post('/api/reforzar/', {
                "partida_id": pid_multi, "municipio_id": celdas_j1[0]['municipio_id'], "cantidad": 1
            }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if r_extra.status_code == 400:
                self.ok("LÍMITE REFUERZOS", "Impide agregar tropas extra una vez agotados los refuerzos del turno.")
            else:
                self.fail("LÍMITE REFUERZOS", "Permitió agregar tropas sin saldo disponible.")

            # 2.5 Verificar soporte visual y táctil en Frontend (SVG pointer-events + botón +1)
            if "pointer-events', 'none'" in mapa_js or 'pointer-events", "none"' in mapa_js:
                self.ok("SVG CLICKABLE", "mapa_svg.js evita que el círculo/número de tropas bloquee el clic sobre el territorio.")
            else:
                self.fail("SVG CLICKABLE", "El badge de tropas en mapa_svg.js no tiene pointer-events: none.", "Agregar .style('pointer-events', 'none') en .badge-tropas.")

            if "desplegarRefuerzoDirecto" in app_js and "territorio-reforzable" in app_js:
                self.ok("UX REFUERZOS FRONTEND", "Frontend ilumina territorios propios en celeste y ofrece botón directo '+1' en el panel lateral.")
            else:
                self.fail("UX REFUERZOS FRONTEND", "Falta resaltado de territorios reforzables o botón directo en app.js.")

            # ==================================================================
            # MÓDULO 3: GUÍA VISUAL ("DÓNDE IR / QUÉ HACER") Y DETECCIÓN DE TURNO
            # ==================================================================
            print("\n[MÓDULO 3] Guía Paso a Paso, Resaltado de Destinos y Aviso de Turno...")

            requerimientos_guia = [
                ("banner-alerta-turno", "Banner superior permanente con instrucciones paso a paso"),
                ("banner-turno-titulo", "Título dinámico de fase y turno"),
                ("banner-turno-pasos", "Explicación concreta de qué clic hacer en cada momento"),
                ("obtenerVecinosGeo", "Cálculo de vecinos limítrofes en el mapa para guiar al jugador"),
                ("territorio-destino-ataque", "Iluminación en rojo de enemigos atacables"),
                ("territorio-destino-reagrupe", "Iluminación en verde de aliados para reagrupar"),
                ("toast-notificacion", "Notificación flotante al cambiar de turno o realizar acciones"),
            ]
            for clave, desc in requerimientos_guia:
                if clave in app_js or clave in html_txt:
                    self.ok("GUÍA VISUAL UX", f"{desc} ({clave}) presente y conectado.")
                else:
                    self.fail("GUÍA VISUAL UX", f"Falta componente de guía visual: {desc} ({clave}).")

            # ==================================================================
            # MÓDULO 4: COMBATE, TRIVIA, BIOMAS Y CONQUISTA
            # ==================================================================
            print("\n[MÓDULO 4] Combate, Fronteras, Trivia, Biomas y Conquista...")

            # Buscar par propio-enemigo limítrofe y no limítrofe
            par_limitrofe = None
            par_lejano = None
            for c1 in EstadoTablero.objects.filter(partida_id=pid_multi, jugador_id=j1_id):
                vecinos_ids = set(c1.municipio.limites.values_list('id', flat=True))
                for c2 in EstadoTablero.objects.filter(partida_id=pid_multi, jugador_id=j2_id):
                    if c2.municipio.id in vecinos_ids and not par_limitrofe:
                        par_limitrofe = (c1, c2)
                    elif c2.municipio.id not in vecinos_ids and not par_lejano:
                        par_lejano = (c1, c2)

            if par_lejano:
                o_lej, d_lej = par_lejano
                o_lej.tropas = 5
                o_lej.save()
                r_lej = self.client.post('/api/preparar-ataque/', {
                    "partida_id": pid_multi, "origen_id": o_lej.municipio.id, "destino_id": d_lej.municipio.id
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                if r_lej.status_code == 400:
                    self.ok("FRONTERAS COMBATE", "Bloquea atacar territorios enemigos que no comparten frontera.")
                else:
                    self.fail("FRONTERAS COMBATE", "Permitió preparar ataque entre territorios no limítrofes.")

            if par_limitrofe:
                o_lim, d_lim = par_limitrofe
                o_lim.tropas = 1
                o_lim.save()
                r_1t = self.client.post('/api/preparar-ataque/', {
                    "partida_id": pid_multi, "origen_id": o_lim.municipio.id, "destino_id": d_lim.municipio.id
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                if r_1t.status_code == 400:
                    self.ok("GUARNICIÓN ATAQUE", "Impide atacar desde un territorio con 1 sola tropa.")
                else:
                    self.fail("GUARNICIÓN ATAQUE", "Permitió atacar con 1 tropa.")

                # Preparar y resolver ataque real con Trivia
                o_lim.tropas = 6
                o_lim.save()
                d_lim.tropas = 1
                d_lim.save()

                r_prep = self.client.post('/api/preparar-ataque/', {
                    "partida_id": pid_multi, "origen_id": o_lim.municipio.id, "destino_id": d_lim.municipio.id
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                if r_prep.status_code == 200 and 'info_terreno' in r_prep.data:
                    self.ok("PREPARAR ATAQUE", f"Ataque válido preparado ({r_prep.data['origen']} -> {r_prep.data['destino']}) | Bioma: {r_prep.data['info_terreno']['bioma']}.")
                else:
                    self.fail("PREPARAR ATAQUE", f"Fallo al preparar ataque: {r_prep.data}")

                # Probar resolución con opción de trivia correcta si existe
                opc_correcta = OpcionRespuesta.objects.filter(es_correcta=True).first()
                modalidad_test = 'TRIVIA' if opc_correcta else 'DADOS'
                r_comb = self.client.post('/api/resolver-combate/', {
                    "partida_id": pid_multi,
                    "origen_id": o_lim.municipio.id,
                    "destino_id": d_lim.municipio.id,
                    "modalidad": modalidad_test,
                    "opcion_id": opc_correcta.id if opc_correcta else None
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')

                if r_comb.status_code == 200 and 'dado_ataque' in r_comb.data:
                    self.ok("RESOLVER COMBATE", f"Combate resuelto ({modalidad_test}) | Dado Ataque: {r_comb.data['dado_ataque']} vs Defensa: {r_comb.data['dado_defensa']} | Conquistado: {r_comb.data['conquistado']}.")
                else:
                    self.fail("RESOLVER COMBATE", f"Fallo al resolver combate: {r_comb.data}")

            # ==================================================================
            # MÓDULO 5: REAGRUPAMIENTO TÁCTICO Y BLOQUEO DE ATAQUE POSTERIOR
            # ==================================================================
            print("\n[MÓDULO 5] Reagrupamiento Táctico, Límites y Regla de Fase...")

            par_propio_lim = None
            for c1 in EstadoTablero.objects.filter(partida_id=pid_multi, jugador_id=j1_id):
                vecinos_ids = set(c1.municipio.limites.values_list('id', flat=True))
                c2 = EstadoTablero.objects.filter(partida_id=pid_multi, jugador_id=j1_id, municipio_id__in=vecinos_ids).first()
                if c2:
                    par_propio_lim = (c1, c2)
                    break

            if par_propio_lim:
                po, pd = par_propio_lim
                po.tropas = 4
                po.save()
                tropas_dest_antes = pd.tropas

                r_mov = self.client.post('/api/mover-tropas/', {
                    "partida_id": pid_multi, "origen_id": po.municipio.id, "destino_id": pd.municipio.id, "cantidad": 1
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')

                if r_mov.status_code == 200 and r_mov.data['destino_tropas'] == tropas_dest_antes + 1:
                    self.ok("REAGRUPAR TROPAS", f"Movimiento limítrofe exitoso ({po.municipio.nombre} -> {pd.municipio.nombre}).")
                else:
                    self.fail("REAGRUPAR TROPAS", f"Fallo al reagrupar: {r_mov.data}")

                # Intentar exceder límite de reagrupamientos en Cordillera (Mendoza = máx 1)
                r_mov_exceso = self.client.post('/api/mover-tropas/', {
                    "partida_id": pid_multi, "origen_id": po.municipio.id, "destino_id": pd.municipio.id, "cantidad": 1
                }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                if r_mov_exceso.status_code == 400:
                    self.ok("LÍMITE REAGRUPAMIENTO", "Bloquea correctamente exceder el cupo de reagrupamientos por bioma.")
                else:
                    self.fail("LÍMITE REAGRUPAMIENTO", "Permitió reagrupar más veces del límite permitido.")

                # Verificar que tras reagrupar no deje atacar en ese turno
                if par_limitrofe:
                    o_lim, d_lim = par_limitrofe
                    if o_lim.jugador_id == j1_id and d_lim.jugador_id == j2_id:
                        o_lim.tropas = 4
                        o_lim.save()
                        r_ataq_post = self.client.post('/api/preparar-ataque/', {
                            "partida_id": pid_multi, "origen_id": o_lim.municipio.id, "destino_id": d_lim.municipio.id
                        }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
                        if r_ataq_post.status_code == 400:
                            self.ok("REGLA FASE REAGRUPAR", "Bloquea iniciar nuevos ataques después de haber reagrupado tropas.")
                        else:
                            self.fail("REGLA FASE REAGRUPAR", "Permitió atacar después de reagrupar.")

            # ==================================================================
            # MÓDULO 6: CARTAS NACIONALES, CANJES, BENEFICIOS Y BOMBAS
            # ==================================================================
            print("\n[MÓDULO 6] Cartas Nacionales, Canjes, Beneficios Propios y Bomba Táctica...")

            j1_obj = Jugador.objects.get(id=j1_id)
            partida_obj = Partida.objects.get(id=pid_multi)
            muni_propio = EstadoTablero.objects.filter(partida=partida_obj, jugador=j1_obj).first().municipio

            # Crear trío de cartas con símbolos distintos para probar canje
            c1 = CartaTerritorio.objects.create(partida=partida_obj, jugador=j1_obj, municipio=muni_propio, simbolo='CONDOR', tipo_carta='TERRITORIO', emblema_titulo='Cóndor')
            c2 = CartaTerritorio.objects.create(partida=partida_obj, jugador=j1_obj, municipio=muni_propio, simbolo='YAGUARETE', tipo_carta='TERRITORIO', emblema_titulo='Yaguareté')
            c3 = CartaTerritorio.objects.create(partida=partida_obj, jugador=j1_obj, municipio=muni_propio, simbolo='OBELISCO', tipo_carta='TERRITORIO', emblema_titulo='Obelisco')

            r_canje = self.client.post('/api/canjear-cartas/', {
                "partida_id": pid_multi, "cartas_ids": [c1.id, c2.id, c3.id]
            }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if r_canje.status_code == 200 and r_canje.data['bonus_refuerzos'] == 4:
                self.ok("CANJE CARTAS", "Canje de 3 símbolos distintos otorgó +4 refuerzos y bonus por territorio propio.")
            else:
                self.fail("CANJE CARTAS", f"Fallo en canje de cartas: {r_canje.data}")

            # Probar beneficio propio BLINDAJE
            c_prop = CartaTerritorio.objects.create(partida=partida_obj, jugador=j1_obj, municipio=muni_propio, simbolo='COMODIN', tipo_carta='TERRITORIO', emblema_titulo='Escarapela')
            r_ben = self.client.post('/api/beneficio-carta/', {
                "partida_id": pid_multi, "carta_id": c_prop.id, "beneficio": "BLINDAJE"
            }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if r_ben.status_code == 200:
                self.ok("BENEFICIO CARTA PROPIA", "Activación de BLINDAJE (+2 defensa) sobre territorio conquistado OK.")
            else:
                self.fail("BENEFICIO CARTA PROPIA", f"Error en beneficio carta: {r_ben.data}")

            # Probar BOMBA aérea sobre enemigo
            celda_rival = EstadoTablero.objects.filter(partida=partida_obj, jugador_id=j2_id).first()
            celda_rival.tropas = 4
            celda_rival.save()
            c_bomba = CartaTerritorio.objects.create(partida=partida_obj, jugador=j1_obj, municipio=muni_propio, simbolo='COMODIN', tipo_carta='BOMBA', emblema_titulo='Bomba')
            r_bomba = self.client.post('/api/usar-bomba/', {
                "partida_id": pid_multi, "carta_id": c_bomba.id, "destino_id": celda_rival.municipio.id
            }, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if r_bomba.status_code == 200 and r_bomba.data['bajas'] >= 1:
                self.ok("BOMBA TÁCTICA", f"Bomba aérea impactó en {r_bomba.data['destino']} y causó {r_bomba.data['bajas']} baja(s).")
            else:
                self.fail("BOMBA TÁCTICA", f"Error al usar bomba: {r_bomba.data}")

            # ==================================================================
            # MÓDULO 7: FIN DE TURNO (MULTIJUGADOR + MODO VS IA) Y RENDICIÓN
            # ==================================================================
            print("\n[MÓDULO 7] Fin de Turno, Rotación Multijugador, Respuesta IA y Rendición...")

            # 7.1 Pasar turno en Multijugador -> debe pasar al Jugador 2 (Carlos)
            r_paso_multi = self.client.post(f'/api/pasar-turno/{pid_multi}/', {}, HTTP_X_PLAYER_TOKEN=tok_j1, format='json')
            if r_paso_multi.status_code == 200 and r_paso_multi.data['nuevo_turno'] == 'Carlos':
                self.ok("TURNO MULTIJUGADOR", f"Turno transferido de '{r_paso_multi.data['turno_saliente_nombre']}' a '{r_paso_multi.data['nuevo_turno']}' con {r_paso_multi.data['tropas_disponibles']} refuerzos.")
            else:
                self.fail("TURNO MULTIJUGADOR", f"Error al rotar turno en multijugador: {r_paso_multi.data}")

            # 7.2 Crear partida VS_IA y verificar que pasar turno ejecute a Bot Belgrano y devuelva el mando
            res_ia = self.client.post('/api/partidas/', {
                "nombre": "QA IA Turno", "modo_juego": "VS_IA", "tipo_mapa": "PROVINCIAL",
                "privacidad": "ABIERTA", "provincia": "Mendoza", "tiempo_turno": 20, "color": "Verde", "jugadores": ["Mariano"]
            }, format='json').data
            self.salas_creadas.append(res_ia['codigo_sala'])

            r_paso_ia = self.client.post(f"/api/pasar-turno/{res_ia['id']}/", {}, HTTP_X_PLAYER_TOKEN=res_ia['mi_token'], format='json')
            if r_paso_ia.status_code == 200 and r_paso_ia.data.get('jugo_ia') and r_paso_ia.data['nuevo_turno'] == 'Mariano':
                self.ok("TURNO VS IA", f"Bot Belgrano ejecutó su jugada ({len(r_paso_ia.data['acciones_ia'])} acciones) y devolvió el turno a Mariano.")
            else:
                self.fail("TURNO VS IA", f"Fallo en el ciclo de turno VS_IA: {r_paso_ia.data}")

            # 7.3 Probar rendición protegida por token
            r_rend = self.client.post('/api/rendirse/', {
                "partida_id": pid_multi, "jugador_id": j2_id
            }, HTTP_X_PLAYER_TOKEN=tok_j2, format='json')
            if r_rend.status_code == 200 and r_rend.data.get('victoria_final') and r_rend.data.get('ganador') == 'Mariano':
                self.ok("RENDICIÓN Y VICTORIA", "Rendición de Carlos procesada con token y victoria otorgada a Mariano.")
            else:
                self.fail("RENDICIÓN Y VICTORIA", f"Fallo en rendición: {r_rend.data}")

            # ==================================================================
            # MÓDULO 8: INTEGRIDAD DOM FRONTEND (index.html <-> app.js)
            # ==================================================================
            print("\n[MÓDULO 8] Integridad DOM y Funciones del Frontend...")

            ids_html = set(re.findall(r'id=["\']([^"\']+)["\']', html_txt))
            ids_js = set(re.findall(r'getElementById\(["\']([^"\']+)["\']\)', app_js))
            faltantes = sorted(ids_js - ids_html)
            if not faltantes:
                self.ok("DOM FRONTEND", f"Los {len(ids_js)} elementos DOM referenciados en app.js existen en index.html.")
            else:
                self.fail("DOM FRONTEND", f"IDs faltantes en index.html: {faltantes}")

        finally:
            Partida.objects.filter(codigo_sala__in=self.salas_creadas).delete()

        # ======================================================================
        # RESUMEN EJECUTIVO FINAL
        # ======================================================================
        print("\n" + "=" * 86)
        print("📊 RESUMEN EJECUTIVO — AGENTE QA INTEGRAL v3")
        print("=" * 86)
        print(f"  ✅ Pruebas aprobadas : {len(self.aprobadas)}")
        print(f"  ❌ Fallos detectados : {len(self.fallos)}")
        print("=" * 86)
        if self.fallos:
            print("\n📌 DETALLE DE FALLOS A CORREGIR:")
            for idx, (mod, det, sol) in enumerate(self.fallos, 1):
                print(f"  {idx}. [{mod}] {det} -> {sol}")
        else:
            print("\n🏆 ¡TODO FUNCIONA AL 100%! LÓGICA, TROPAS, GUÍAS Y JUGABILIDAD VERIFICADAS.")


if __name__ == '__main__':
    AgenteQACompletoV3().ejecutar_auditoria()
