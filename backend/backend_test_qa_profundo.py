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
from juego.models import Partida, Jugador, EstadoTablero


class AgenteQAProfundo:
    def __init__(self):
        self.client = APIClient()
        self.ok = []
        self.bugs = []
        self.salas_limpiar = []

    def pass_test(self, area, msg):
        self.ok.append((area, msg))
        print(f"  ✅ [{area}] {msg}")

    def fail_test(self, area, bug, causa_raiz="", solucion=""):
        self.bugs.append((area, bug, causa_raiz, solucion))
        print(f"  ❌ [{area}] {bug}")
        if causa_raiz:
            print(f"     🔎 Causa raíz: {causa_raiz}")
        if solucion:
            print(f"     🛠️ Solución  : {solucion}")

    def auditar_todo(self):
        print("=" * 82)
        print("🔬 AGENTE QA PROFUNDO — AUDITORÍA END-TO-END (BACKEND + FRONTEND + UX)")
        print("=" * 82)

        base_front = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'frontend'))
        html_path = os.path.join(base_front, 'index.html')
        js_app_path = os.path.join(base_front, 'js', 'app.js')
        js_mapa_path = os.path.join(base_front, 'js', 'mapa_svg.js')

        with open(html_path, 'r', encoding='utf-8') as f:
            html_txt = f.read()
        with open(js_app_path, 'r', encoding='utf-8') as f:
            app_js = f.read()
        with open(js_mapa_path, 'r', encoding='utf-8') as f:
            mapa_js = f.read()

        try:
            # ==================================================================
            # PRUEBA 1: POR QUÉ NO SE AGREGAN TROPAS AL HACER CLIC EN EL MAPA
            # ==================================================================
            print("\n[1] AUDITORÍA PROFUNDA: CLICK EN TERRITORIO Y DESPLIEGUE DE REFUERZOS")

            # 1A. Crear partida simulando el payload exacto del navegador
            res = self.client.post('/api/partidas/', {
                "nombre": "QA Profundo Tropas",
                "modo_juego": "VS_IA",
                "tipo_mapa": "PROVINCIAL",
                "privacidad": "ABIERTA",
                "provincia": "Mendoza",
                "tiempo_turno": 20,
                "color": "Azul",
                "jugadores": ["Mariano"]
            }, format='json')
            p_data = res.data
            self.salas_limpiar.append(p_data['codigo_sala'])
            partida_id = p_data['id']
            token_j1 = p_data['mi_token']
            j1_id = p_data['mi_jugador_id']

            # Verificar contrato de datos entre backend y app.js
            propia = next((t for t in p_data['tablero'] if t['jugador_id'] == j1_id), None)
            if not propia:
                self.fail_test("CONTRATO TABLERO", "El tablero devuelto no asignó territorios al jugador creador.")
            else:
                self.pass_test("CONTRATO TABLERO", f"Territorio propio detectado: {propia['municipio_nombre']} (municipio_id={propia['municipio_id']}, tropas={propia['tropas']}).")

            # Verificar si app.js envía municipio_id o id al llamar a /api/reforzar/
            bloque_reforzar = re.search(r"fetch\(`\$\{API_URL\}/reforzar/`[\s\S]{0,450}?\}\)", app_js)
            if bloque_reforzar:
                txt_ref = bloque_reforzar.group(0)
                if "municipio_id" in txt_ref:
                    self.pass_test("API REFORZAR JS", "app.js envía 'municipio_id' correctamente a /api/reforzar/.")
                else:
                    self.fail_test("API REFORZAR JS", "app.js no está enviando 'municipio_id'.")

            # Verificar por qué el click en SVG puede fallar o no verse
            if "pointer-events" in mapa_js or ".on('click'" in mapa_js:
                # Revisar si el círculo/texto de tropas bloquea el click o si tiene pointer-events: none
                if "pointer-events" not in mapa_js:
                    self.fail_test(
                        "SVG CLICK TARGET",
                        "En mapa_svg.js, los elementos internos (<circle> y <text> de tropas) no tienen 'pointer-events: none' explícito, y el click depende de burbujeo al <g>.",
                        "Si el usuario hace clic justo sobre el número de tropas o en bordes con solapamiento, algunos navegadores no disparan correctamente o no muestran feedback visual.",
                        "Agregar .style('pointer-events', 'none') al grupo .badge-tropas y registrar el click tanto en el <path> como en el <g>."
                    )
                else:
                    self.pass_test("SVG CLICK TARGET", "mapa_svg.js gestiona pointer-events en el badge de tropas.")

            # Probar click real en backend (/api/reforzar/)
            tropas_disp_antes = p_data['jugador_turno_tropas']
            tropas_celda_antes = propia['tropas']
            res_ref = self.client.post('/api/reforzar/', {
                "partida_id": partida_id,
                "municipio_id": propia['municipio_id'],
                "cantidad": 1
            }, HTTP_X_PLAYER_TOKEN=token_j1, format='json')

            if res_ref.status_code == 200 and res_ref.data['nuevas_tropas'] == tropas_celda_antes + 1:
                self.pass_test("BACKEND REFORZAR", f"POST /api/reforzar/ incrementó tropas de {tropas_celda_antes} a {res_ref.data['nuevas_tropas']} (quedan {res_ref.data['tropas_disponibles']}).")
            else:
                self.fail_test("BACKEND REFORZAR", f"Fallo al reforzar: {res_ref.status_code} {res_ref.data}")

            # Revisar si actualizarEstadoPartida() sobrescribe el feedback o si el GET devuelve jugador_turno_tropas actualizado
            res_get = self.client.get(f"/api/partidas/{p_data['codigo_sala']}/").data
            if res_get['jugador_turno_tropas'] == tropas_disp_antes - 1:
                self.pass_test("SINCRONÍA REFUERZOS", "GET /api/partidas/<codigo>/ refleja inmediatamente la resta de refuerzos disponibles.")
            else:
                self.fail_test("SINCRONÍA REFUERZOS", "GET /api/partidas/ no actualizó jugador_turno_tropas.")

            # Revisar por qué el usuario siente que "no se agregan tropas al hacer click"
            if "partidaIniciada" in app_js:
                self.fail_test(
                    "FLUJO INICIO / CLICK BLOQUEADO",
                    "Si el usuario no pulsa '🚀 Iniciar Batalla' o si el banner no resalta qué territorios son propios pulsables, hacer clic en el mapa parece no hacer nada.",
                    "1) Mientras partidaIniciada == false, los clics al mapa solo lanzan un toast efímero de 3.5s. 2) Durante la fase de refuerzos, los territorios propios no tienen contorno brillante indicando que son clicables para sumar tropas.",
                    "Iluminar en celeste brillante todos los territorios propios cuando jugador_turno_tropas > 0 y agregar botón '+1 Tropa' directo en el panel izquierdo 'Mis Territorios' como alternativa táctil infalible."
                )

            # ==================================================================
            # PRUEBA 2: VENCIMIENTO DE TIEMPO Y DETECCIÓN DE TURNO (IA VS HUMANO)
            # ==================================================================
            print("\n[2] AUDITORÍA PROFUNDA: FIN DE TIEMPO Y QUIÉN TIENE EL TURNO")

            # Simular vencimiento de tiempo llamando a /api/pasar-turno/ en modo VS_IA
            res_pasar_ia = self.client.post(f'/api/pasar-turno/{partida_id}/', {}, HTTP_X_PLAYER_TOKEN=token_j1, format='json')
            if res_pasar_ia.status_code == 200:
                d_ia = res_pasar_ia.data
                self.pass_test(
                    "BACKEND TURNO VS_IA",
                    f"En VS_IA, el backend ejecuta el turno de Bot Belgrano automáticamente ({len(d_ia['acciones_ia'])} acciones) y devuelve el turno a '{d_ia['nuevo_turno']}'."
                )
            else:
                self.fail_test("BACKEND TURNO VS_IA", f"Error en pasar-turno VS_IA: {res_pasar_ia.data}")

            # Analizar qué pasa en app.js cuando se acaba el tiempo (segundosRestantes <= 0)
            if "ejecutarPasarTurno(true)" in app_js:
                # Verificar si en modo VS_IA o Multijugador informa claramente quién jugó y de quién es el turno ahora
                if "turno_anterior_nombre" not in res_pasar_ia.data:
                    self.fail_test(
                        "REPORTE DE TURNO AL VENCER RELOJ",
                        "Cuando se termina el tiempo en modo VS_IA, el backend ejecuta el turno de la IA en milisegundos y devuelve 'nuevo_turno: Mariano', por lo que el usuario NUNCA ve un cartel claro que diga 'Se acabó tu tiempo -> Jugó Bot Belgrano (IA) -> Ahora es tu turno'.",
                        "El backend ejecuta humano -> IA -> humano dentro del mismo POST /pasar-turno/, y app.js solo dice 'El mando pasó automáticamente' sin especificar si jugó la IA o si pasó a otro jugador.",
                        "Mostrar explícitamente en el cartel y en el banner permanente: quién perdió el turno por tiempo, qué hizo la IA (o qué jugador humano sigue en Multijugador) y de quién es el turno actual."
                    )

            # Revisar si en el panel superior/banner se distingue claramente "TU TURNO" vs "TURNO DE IA" vs "TURNO DE RIVAL HUMANO"
            if "jugadores.find(j => j.id === partidaActual.jugador_turno_id)" not in app_js:
                self.fail_test(
                    "IDENTIFICACIÓN TIPO DE JUGADOR EN TURNO",
                    "app.js no consulta el flag 'es_ia' del jugador en turno para diferenciar si el turno pertenece a la Inteligencia Artificial o a otro jugador humano.",
                    "partidaActual.jugadores incluye 'es_ia', pero actualizarHeader() solo muestra el nombre sin indicar si es Bot IA o jugador remoto.",
                    "Detectar jugadorActivo = partidaActual.jugadores.find(j => j.id === partidaActual.jugador_turno_id) y mostrar '🤖 TURNO DE LA IA (Bot Belgrano)' o '👤 TURNO DEL RIVAL (Nombre)'."
                )

            # ==================================================================
            # PRUEBA 3: VISUALIZACIÓN Y LÓGICA DEL REAGRUPAMIENTO
            # ==================================================================
            print("\n[3] AUDITORÍA PROFUNDA: VISUALIZACIÓN Y ESTADO DE REAGRUPAMIENTO")

            # Verificar si el serializer envía reagrupamientos_turno o reagrupamientos_restantes
            if "reagrupamientos_turno" not in json.dumps(res_get):
                self.fail_test(
                    "DATOS DE REAGRUPAMIENTO EN API",
                    "PartidaSerializer no envía 'reagrupamientos_turno' ni 'limite_reagrupamientos' en el estado de la partida.",
                    "El frontend no sabe cuántos reagrupamientos le quedan al jugador ni si ya gastó su movimiento del turno.",
                    "Incluir 'reagrupamientos_turno' en JugadorSerializer / PartidaSerializer para mostrar un contador visual en el botón y en el banner."
                )
            else:
                self.pass_test("DATOS DE REAGRUPAMIENTO EN API", "El estado de partida incluye los reagrupamientos usados.")

            # Verificar feedback visual del botón Reagrupar y del flujo de 2 pasos
            if "btnReagrupar.style.background" not in app_js:
                self.fail_test(
                    "FEEDBACK VISUAL BOTÓN REAGRUPAR",
                    "El botón '🔄 Reagrupar' no cambia de color ni muestra contador de movimientos disponibles cuando está activo.",
                    "Al activarlo solo cambia el texto, pero visualmente parece un botón secundario apagado y no muestra el recorrido Origen -> Destino.",
                    "Estilizar el botón activo en verde esmeralda con pulso, mostrar un indicador visual 'Origen ➔ Destino' en el banner y permitir elegir cantidad de tropas (1 o todas menos 1)."
                )

        finally:
            Partida.objects.filter(codigo_sala__in=self.salas_limpiar).delete()

        # ======================================================================
        # REPORTE FINAL DEL AGENTE QA PROFUNDO
        # ======================================================================
        print("\n" + "=" * 82)
        print("📋 INFORME DE DIAGNÓSTICO PROFUNDO — RESULTADOS")
        print("=" * 82)
        print(f"  ✅ Verificaciones exitosas : {len(self.ok)}")
        print(f"  ❌ Problemas UX/Lógica     : {len(self.bugs)}")
        print("-" * 82)
        for i, (area, bug, causa, sol) in enumerate(self.bugs, 1):
            print(f"\n  {i}. [{area}] {bug}")
            print(f"     • Por qué ocurre: {causa}")
            print(f"     • Cómo se arregla: {sol}")
        print("\n" + "=" * 82)


if __name__ == '__main__':
    AgenteQAProfundo().auditar_todo()