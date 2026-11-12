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
from juego.models import Partida


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
        js_app_path = os.path.join(base_front, 'js', 'app.js')
        js_mapa_path = os.path.join(base_front, 'js', 'mapa_svg.js')

        with open(js_app_path, 'r', encoding='utf-8') as f:
            app_js = f.read()
        with open(js_mapa_path, 'r', encoding='utf-8') as f:
            mapa_js = f.read()

        try:
            print("\n[1] AUDITORÍA PROFUNDA: CLICK EN TERRITORIO Y DESPLIEGUE DE REFUERZOS")
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

            propia = next((t for t in p_data['tablero'] if t['jugador_id'] == j1_id), None)
            if not propia:
                self.fail_test("CONTRATO TABLERO", "El tablero devuelto no asignó territorios al jugador creador.")
            else:
                self.pass_test("CONTRATO TABLERO", f"Territorio propio detectado: {propia['municipio_nombre']} (municipio_id={propia['municipio_id']}, tropas={propia['tropas']}).")

            bloque_reforzar = re.search(r"fetch\(`\$\{API_URL\}/reforzar/`[\s\S]{0,450}?\}\)", app_js)
            if bloque_reforzar and "municipio_id" in bloque_reforzar.group(0):
                self.pass_test("API REFORZAR JS", "app.js envía 'municipio_id' correctamente a /api/reforzar/.")
            else:
                self.fail_test("API REFORZAR JS", "app.js no está enviando 'municipio_id'.")

            if "pointer-events" not in mapa_js:
                self.fail_test(
                    "SVG CLICK TARGET",
                    "En mapa_svg.js, los elementos internos (<circle> y <text> de tropas) no tienen 'pointer-events: none' explícito.",
                    "Si el usuario hace clic justo sobre el número de tropas o en bordes con solapamiento, puede fallar el disparo.",
                    "Agregar .style('pointer-events', 'none') al grupo .badge-tropas y registrar el click en <path> y <g>."
                )
            else:
                self.pass_test("SVG CLICK TARGET", "mapa_svg.js gestiona pointer-events en el badge de tropas.")

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

            res_get = self.client.get(f"/api/partidas/{p_data['codigo_sala']}/").data
            if res_get['jugador_turno_tropas'] == tropas_disp_antes - 1:
                self.pass_test("SINCRONÍA REFUERZOS", "GET /api/partidas/<codigo>/ refleja inmediatamente la resta de refuerzos disponibles.")
            else:
                self.fail_test("SINCRONÍA REFUERZOS", "GET /api/partidas/ no actualizó jugador_turno_tropas.")

            if "partidaIniciada" in app_js:
                self.fail_test(
                    "FLUJO INICIO / CLICK BLOQUEADO",
                    "Si el usuario no pulsa '🚀 Iniciar Batalla' o los territorios propios no tienen resaltado/botón directo, parece que hacer clic no agrega tropas.",
                    "Mientras partidaIniciada == false, los clics al mapa no refuerzan, y en fase de refuerzos falta contorno celeste y botón '+1' en el panel lateral.",
                    "Iluminar en celeste brillante todos los territorios propios cuando jugador_turno_tropas > 0 y agregar botón '+1 Tropa' directo en el panel izquierdo."
                )

            print("\n[2] AUDITORÍA PROFUNDA: FIN DE TIEMPO Y QUIÉN TIENE EL TURNO")
            res_pasar_ia = self.client.post(f'/api/pasar-turno/{partida_id}/', {}, HTTP_X_PLAYER_TOKEN=token_j1, format='json')
            if res_pasar_ia.status_code == 200:
                d_ia = res_pasar_ia.data
                self.pass_test("BACKEND TURNO VS_IA", f"En VS_IA, el backend ejecuta el turno de Bot Belgrano automáticamente ({len(d_ia['acciones_ia'])} acciones) y devuelve el turno a '{d_ia['nuevo_turno']}'.")

            if "turno_anterior_nombre" not in res_pasar_ia.data:
                self.fail_test(
                    "REPORTE DE TURNO AL VENCER RELOJ",
                    "Al vencer el reloj en VS_IA, el backend ejecuta humano -> IA -> humano en el mismo request y app.js no anuncia quién jugó ni de quién es el turno actual.",
                    "app.js solo dice 'El mando pasó automáticamente' sin diferenciar modo VS_IA vs Multijugador.",
                    "Mostrar cartel explícito: quién perdió el turno por tiempo, qué hizo la IA (o qué jugador humano sigue) y de quién es el turno actual."
                )

            if "jugadores.find(j => j.id === partidaActual.jugador_turno_id)" not in app_js:
                self.fail_test(
                    "IDENTIFICACIÓN TIPO DE JUGADOR EN TURNO",
                    "app.js no consulta el flag 'es_ia' del jugador en turno.",
                    "actualizarHeader() solo muestra el nombre sin indicar si es Bot IA o jugador remoto.",
                    "Detectar jugadorActivo.es_ia para mostrar '🤖 TURNO DE LA IA' o '👤 TURNO DEL RIVAL'."
                )

            print("\n[3] AUDITORÍA PROFUNDA: VISUALIZACIÓN Y ESTADO DE REAGRUPAMIENTO")
            if "reagrupamientos_turno" not in json.dumps(res_get):
                self.fail_test(
                    "DATOS DE REAGRUPAMIENTO EN API",
                    "PartidaSerializer no envía 'reagrupamientos_turno' ni 'limite_reagrupamientos'.",
                    "El frontend no sabe cuántos movimientos le quedan al jugador.",
                    "Incluir 'reagrupamientos_turno' en el serializer y mostrar contador visual en el botón y banner."
                )
            else:
                self.pass_test("DATOS DE REAGRUPAMIENTO EN API", "El estado de partida incluye los reagrupamientos usados.")

            if "btnReagrupar.style.background" not in app_js:
                self.fail_test(
                    "FEEDBACK VISUAL BOTÓN REAGRUPAR",
                    "El botón '🔄 Reagrupar' no cambia de color ni muestra contador de movimientos disponibles cuando está activo.",
                    "Visualmente parece un botón secundario apagado y no muestra el recorrido Origen -> Destino.",
                    "Estilizar el botón activo en verde esmeralda y mostrar indicador 'Origen ➔ Destino'."
                )
        finally:
            Partida.objects.filter(codigo_sala__in=self.salas_limpiar).delete()

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
