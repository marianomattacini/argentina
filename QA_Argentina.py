# -*- coding: utf-8 -*-
"""
QA_Argentina.py - Agente de pruebas automatico para el juego Argentina.

Uso (con el juego YA iniciado con Iniciar_Argentina.bat):
    & "C:\\Users\\<usuario>\\Desktop\\Argentina\\backend\\.venv\\Scripts\\python.exe" "C:\\Users\\<usuario>\\Desktop\\Argentina\\QA_Argentina.py"

Solo usa la libreria estandar. Prueba el backend por HTTP exactamente como lo
hace el navegador, y revisa que el frontend servido sea la version nueva.
Guarda el informe en qa_resultado.txt (junto a este archivo).
"""
import html
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

API = os.environ.get('QA_API', 'http://127.0.0.1:8000/api')
WEB = os.environ.get('QA_WEB', 'http://127.0.0.1:5500')
RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / 'backend'
FRONT = RAIZ / 'frontend' / 'frontend'

RESULTADOS = []      # (estado, nombre, detalle)
LINEAS = []          # todo lo impreso, para guardarlo en el informe


def out(texto=''):
    print(texto)
    LINEAS.append(texto)


def check(ok, nombre, detalle='', aviso=False, info=''):
    """detalle se muestra solo si falla; info se muestra solo si anda."""
    estado = 'OK' if ok else ('AVISO' if aviso else 'FALLA')
    texto = info if ok else detalle
    RESULTADOS.append((estado, nombre, texto))
    marca = {'OK': '[ OK  ]', 'AVISO': '[AVISO]', 'FALLA': '[FALLA]'}[estado]
    out(f'{marca} {nombre}' + (f'  ->  {texto}' if texto else ''))
    return ok


def titulo(texto):
    out('')
    out('=' * 70)
    out(texto)
    out('=' * 70)


# ---------------------------------------------------------------- HTTP
def http(metodo, url, datos=None, token=None, timeout=40):
    """Devuelve (status, json_o_None, texto_crudo, headers). status 0 = sin conexion."""
    cuerpo = None
    headers = {'Accept': 'application/json'}
    if datos is not None:
        cuerpo = json.dumps(datos).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    if token:
        headers['X-Player-Token'] = token
    req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            crudo = r.read().decode('utf-8', errors='replace')
            hdrs = dict(r.headers)
            status = r.status
    except urllib.error.HTTPError as e:
        crudo = e.read().decode('utf-8', errors='replace')
        hdrs = dict(e.headers)
        status = e.code
    except Exception as e:  # sin conexion, timeout, etc.
        return 0, None, f'{type(e).__name__}: {e}', {}
    try:
        data = json.loads(crudo)
    except Exception:
        data = None
    return status, data, crudo, hdrs


def api(metodo, ruta, datos=None, token=None):
    return http(metodo, API + ruta, datos, token)


def resumen_error(status, data, crudo):
    """Resume una respuesta de error: JSON del juego o pagina de error de Django."""
    if status == 0:
        return f'SIN CONEXION ({crudo})'
    if isinstance(data, dict) and data.get('error'):
        return f'HTTP {status}: {data["error"]}'
    titulo_m = re.search(r'<title>(.*?)</title>', crudo, re.S)
    valor_m = re.search(r'<pre class="exception_value">(.*?)</pre>', crudo, re.S)
    partes = [f'HTTP {status}']
    if titulo_m:
        partes.append(html.unescape(titulo_m.group(1)).strip().replace('\n', ' ')[:120])
    if valor_m:
        partes.append(html.unescape(valor_m.group(1)).strip().replace('\n', ' ')[:200])
    if len(partes) == 1:
        partes.append(crudo[:150].replace('\n', ' '))
    return ' | '.join(partes)


# ---------------------------------------------------------------- A. Entorno
def prueba_entorno():
    titulo('A. ENTORNO Y ARCHIVOS')
    out(f'Python: {platform.python_version()} ({sys.executable})')
    out(f'Sistema: {platform.platform()}')
    out(f'Carpeta del proyecto: {RAIZ}')
    check(sys.version_info >= (3, 12), 'Python 3.12 o superior', 'Django 6 necesita 3.12+', aviso=True, info=platform.python_version())
    check((BACKEND / 'manage.py').exists(), 'backend/manage.py existe')
    check((FRONT / 'index.html').exists(), 'frontend/frontend/index.html existe')

    settings = BACKEND / 'teg_argentina' / 'settings.py'
    txt = settings.read_text(encoding='utf-8', errors='replace') if settings.exists() else ''
    check("'transaction_mode'" in txt and "'timeout'" in txt,
          'settings.py tiene el arreglo de "database is locked"',
          'falta: reemplazar backend/teg_argentina/settings.py por la version nueva')

    views = BACKEND / 'juego' / 'views.py'
    vtxt = views.read_text(encoding='utf-8', errors='replace') if views.exists() else ''
    check('emblema_para_municipio' in vtxt and (BACKEND / 'juego' / 'emblemas.py').exists(),
          'views.py y emblemas.py son la version con emblemas por municipio')

    appjs = FRONT / 'js' / 'app.js'
    atxt = appjs.read_text(encoding='utf-8-sig', errors='replace') if appjs.exists() else ''
    check('BLOQUE AGREGADO' in atxt, 'app.js (disco) tiene las funciones que faltaban (reagrupar, rendirse, cartas...)')
    check('No se pudo iniciar la partida (' in atxt,
          'app.js (disco) es la ULTIMA version (muestra el motivo real del error)',
          'si falla: reemplazar frontend/frontend/js/app.js por el ultimo entregado')
    css = FRONT / 'css' / 'styles.css'
    ctxt = css.read_text(encoding='utf-8-sig', errors='replace') if css.exists() else ''
    check('territorio-destino-ataque' in ctxt, 'styles.css tiene los resaltados del mapa')
    return atxt


# ---------------------------------------------------------------- B. Servidores
def pids_en_puerto(puerto):
    if platform.system() != 'Windows':
        return None
    try:
        salida = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None
    pids = set()
    for linea in salida.splitlines():
        if f':{puerto} ' in linea and 'LISTENING' in linea.upper():
            pids.add(linea.split()[-1])
    return pids


def prueba_servidores(atxt):
    titulo('B. SERVIDORES Y FRONTEND SERVIDO')
    st, data, crudo, _ = api('GET', '/partidas/ZZZZZZ/')
    check(st == 404 and isinstance(data, dict), 'Backend responde en 127.0.0.1:8000', resumen_error(st, data, crudo) if st != 404 else '')
    if st == 0:
        out('   >> El backend NO esta corriendo. Ejecuta Iniciar_Argentina.bat y volve a correr este QA.')

    for puerto, nombre in ((8000, 'backend'), (5500, 'frontend')):
        pids = pids_en_puerto(puerto)
        if pids is None:
            continue
        check(len(pids) == 1, f'Un solo proceso escuchando el puerto {puerto} ({nombre})',
              ('no hay nada escuchando' if not pids else f'PIDs: {", ".join(sorted(pids))}  <- servidores duplicados: ejecuta Detener_Argentina.bat'),
              info=f'PID {", ".join(sorted(pids))}')

    st, _, crudo, hdrs = http('GET', WEB + '/index.html')
    check(st == 200, 'Frontend responde en 127.0.0.1:5500', f'HTTP {st}' if st != 200 else '')
    if st == 200:
        recursos = re.findall(r'(?:src|href)="([^"#]+\.(?:js|css))"', crudo)
        for rec in recursos:
            if rec.startswith('http'):
                continue
            s2, _, _, _ = http('GET', f'{WEB}/{rec}')
            check(s2 == 200, f'Se sirve {rec}', f'HTTP {s2}' if s2 != 200 else '')
        s3, _, js_servido, h3 = http('GET', WEB + '/js/app.js')
        if s3 == 200:
            check('No se pudo iniciar la partida (' in js_servido,
                  'El app.js que SIRVE el servidor es la ultima version',
                  'el servidor sirve una version vieja')
            cache = {k.lower(): v for k, v in h3.items()}.get('cache-control', '')
            check('no-store' in cache or 'no-cache' in cache,
                  'El frontend se sirve sin cache (el navegador no usa versiones viejas)',
                  'sin Cache-Control: si cambias archivos, apreta Ctrl+F5 en la ventana del juego', aviso=True)
        for cdn in ('https://d3js.org/d3.v7.min.js',):
            s4, _, _, _ = http('GET', cdn, timeout=15)
            check(s4 == 200, f'Hay internet para cargar {cdn}', f'HTTP {s4}: sin esa libreria el mapa no se dibuja' if s4 != 200 else '')
    # Preflight CORS: lo que hace el navegador antes de cada POST con el token del jugador
    try:
        rq = urllib.request.Request(API + '/partidas/1/iniciar/', method='OPTIONS', headers={
            'Origin': WEB, 'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'content-type,x-player-token'})
        with urllib.request.urlopen(rq, timeout=10) as r:
            permitido = (r.headers.get('Access-Control-Allow-Headers') or '').lower()
    except urllib.error.HTTPError as e:
        permitido = (e.headers.get('Access-Control-Allow-Headers') or '').lower()
    except Exception:
        permitido = ''
    check('x-player-token' in permitido,
          'CORS: el navegador puede enviar la cabecera X-Player-Token',
          'el backend no la permite: el navegador bloquea Iniciar Batalla. Reemplaza backend/teg_argentina/settings.py')


# ---------------------------------------------------------------- C. Flujo completo
class Poller(threading.Thread):
    """Simula el refresco del navegador (consulta el estado cada 0.3 s)."""
    def __init__(self, codigo):
        super().__init__(daemon=True)
        self.codigo = codigo
        self.parar = threading.Event()
        self.errores = []

    def run(self):
        while not self.parar.is_set():
            st, data, crudo, _ = api('GET', f'/partidas/{self.codigo}/')
            if st != 200:
                self.errores.append(resumen_error(st, data, crudo))
            time.sleep(0.3)


def crear_partida(nombre='QA_Argentina', modo='VS_IA', tipo='PROVINCIAL', **extra):
    cuerpo = {'nombre': nombre, 'modo_juego': modo, 'tipo_mapa': tipo, 'provincia': 'Mendoza',
              'jugadores': ['QA Tester'], 'color': 'Azul', 'tiempo_turno': 0}
    cuerpo.update(extra)
    return api('POST', '/partidas/', cuerpo)


def estado(codigo):
    st, data, crudo, _ = api('GET', f'/partidas/{codigo}/')
    return data if st == 200 else None


def prueba_flujo():
    titulo('C. FLUJO COMPLETO DE UNA PARTIDA (vs IA, mapa de Mendoza)')
    st, d, crudo, _ = crear_partida()
    if not check(st == 201 and d, 'Crear partida', resumen_error(st, d, crudo) if st != 201 else ''):
        return
    pid, tok, yo, cod = d['id'], d['mi_token'], d['mi_jugador_id'], d['codigo_sala']
    check(len(d['tablero']) >= 18, 'El tablero tiene los territorios de Mendoza', 'faltan territorios', info=f'{len(d["tablero"])} territorios')
    check(len(d['jugadores']) == 2, 'Hay 2 jugadores (vos + IA)', f'hay {len(d["jugadores"])}')
    check(d.get('iniciada') is False, 'La partida nace "sin iniciar"')

    genericos = {'Cóndor Andino', 'Yaguareté Misionero', 'Obelisco Porteño'}
    cartas = d.get('cartas', [])
    check(cartas and all(c['emblema_titulo'] not in genericos for c in cartas),
          'Las tarjetas traen emblema propio del municipio',
          'siguen saliendo emblemas genericos: reemplazar views.py y emblemas.py',
          info='; '.join(f'{c["municipio_nombre"]}={c["emblema_titulo"]}' for c in cartas))

    poller = Poller(cod)
    poller.start()
    st, d2, crudo, _ = api('POST', f'/partidas/{pid}/iniciar/', {}, tok)
    ok_ini = check(st == 200 and d2 and d2.get('iniciada') is True, 'INICIAR BATALLA (con refresco simultaneo del navegador)',
                   resumen_error(st, d2, crudo) if st != 200 else '')
    if not ok_ini:
        poller.parar.set()
        out('   >> Este es el error que ves en pantalla. El texto de arriba es la causa real.')
        return
    st, d3, crudo, _ = api('POST', f'/partidas/{pid}/iniciar/', {}, tok)
    check(st == 200, 'Iniciar dos veces no rompe (idempotente)', resumen_error(st, d3, crudo) if st != 200 else '')

    e = estado(cod)
    tropas = e['jugador_turno_tropas']
    check(e['jugador_turno_id'] == yo and tropas > 0, 'Empezas vos, con refuerzos para desplegar', 'no arrancas vos o no hay refuerzos', info=f'refuerzos={tropas}')

    propios = [t for t in e['tablero'] if t['jugador_id'] == yo]
    fallos = []
    for _ in range(tropas):
        st, r, crudo, _ = api('POST', '/reforzar/', {'partida_id': pid, 'municipio_id': propios[0]['municipio_id'], 'cantidad': 1}, tok)
        if st != 200:
            fallos.append(resumen_error(st, r, crudo))
            break
    check(not fallos, f'Reforzar {tropas} veces', fallos[0] if fallos else '')

    e = estado(cod)
    check(e['jugador_turno_tropas'] == 0, 'Sin refuerzos pendientes tras desplegar')

    # Atacar
    e = estado(cod)
    propios = [t for t in e['tablero'] if t['jugador_id'] == yo and t['tropas'] >= 2]
    enemigos = [t for t in e['tablero'] if t['jugador_id'] != yo]
    if propios and enemigos:
        o, dd = propios[0]['municipio_id'], enemigos[0]['municipio_id']
        st, r, crudo, _ = api('POST', '/preparar-ataque/', {'partida_id': pid, 'origen_id': o, 'destino_id': dd}, tok)
        check(st == 200, 'Preparar ataque', resumen_error(st, r, crudo) if st != 200 else '')
        st, r, crudo, _ = api('POST', '/resolver-combate/', {'partida_id': pid, 'origen_id': o, 'destino_id': dd,
                                                              'modalidad': 'DADOS', 'opcion_id': None}, tok)
        check(st == 200 and 'resultado' in (r or {}), 'Resolver combate por dados',
              resumen_error(st, r, crudo) if st != 200 else '', info=f'{(r or {}).get("resultado")} ({(r or {}).get("dado_ataque")} vs {(r or {}).get("dado_defensa")})')
    else:
        check(False, 'Atacar', 'no hay territorio propio con 2+ tropas', aviso=True)

    # Reagrupar entre dos territorios propios (despues de atacar)
    e = estado(cod)
    propios = [t for t in e['tablero'] if t['jugador_id'] == yo]
    fuertes = sorted(propios, key=lambda t: -t['tropas'])
    if len(fuertes) >= 2:
        st, r, crudo, _ = api('POST', '/mover-tropas/', {'partida_id': pid, 'origen_id': fuertes[0]['municipio_id'],
                                                         'destino_id': fuertes[1]['municipio_id'], 'cantidad': 1}, tok)
        check(st == 200, 'Reagrupar (mover 1 tropa entre territorios propios)', resumen_error(st, r, crudo) if st != 200 else '', info=(r or {}).get('mensaje', ''))

    # Pasar turno (juega la IA)
    st, r, crudo, _ = api('POST', f'/pasar-turno/{pid}/', {}, tok)
    check(st == 200, 'Pasar turno (juega la IA)', resumen_error(st, r, crudo) if st != 200 else '', info=f'{len((r or {}).get("acciones_ia", []))} acciones de la IA')
    e = estado(cod)
    check(e and e['jugador_turno_id'] == yo and e['jugador_turno_tropas'] > 0, 'Vuelve tu turno con refuerzos nuevos',
          f'turno de {e["jugador_turno_nombre"]}, refuerzos={e["jugador_turno_tropas"]}' if e else 'sin estado',
          info=f'refuerzos={e["jugador_turno_tropas"]}' if e else '')

    # Rendirse
    st, r, crudo, _ = api('POST', '/rendirse/', {'partida_id': pid, 'jugador_id': yo}, tok)
    check(st == 200, 'Rendirse', resumen_error(st, r, crudo) if st != 200 else '')
    e = estado(cod)
    check(e and e['activa'] is False and e.get('ganador_nombre'), 'La partida termina y hay ganador', 'la partida no termino', info=f'ganador={e.get("ganador_nombre")}' if e else '')

    poller.parar.set()
    poller.join(timeout=3)
    check(not poller.errores, 'El refresco constante del navegador nunca fallo durante el flujo',
          f'{len(poller.errores)} errores, ej: {poller.errores[0]}' if poller.errores else '')


# ---------------------------------------------------------------- D. Concurrencia
def una_partida_concurrente(i):
    st, d, crudo, _ = crear_partida(nombre=f'QA_Argentina_C{i}')
    if st != 201:
        return f'crear: {resumen_error(st, d, crudo)}'
    pid, tok, cod = d['id'], d['mi_token'], d['codigo_sala']
    poller = Poller(cod)
    poller.start()
    time.sleep(0.2)
    st, d2, crudo, _ = api('POST', f'/partidas/{pid}/iniciar/', {}, tok)
    poller.parar.set()
    poller.join(timeout=3)
    if st != 200:
        return f'iniciar: {resumen_error(st, d2, crudo)}'
    if poller.errores:
        return f'refresco: {poller.errores[0]}'
    return None


def prueba_concurrencia(n=8):
    titulo(f'D. {n} PARTIDAS A LA VEZ (reproduce el error "database is locked")')
    with ThreadPoolExecutor(max_workers=n) as ex:
        resultados = list(ex.map(una_partida_concurrente, range(n)))
    fallas = [r for r in resultados if r]
    check(not fallas, f'{n - len(fallas)} de {n} partidas simultaneas se crearon e iniciaron bien',
          ' // '.join(sorted(set(fallas)))[:400] if fallas else '', info='')


# ---------------------------------------------------------------- E. Multijugador
def prueba_multijugador():
    titulo('E. SALA MULTIJUGADOR CON CONTRASENA')
    st, d, crudo, _ = crear_partida(nombre='QA_Argentina_M', modo='MULTIJUGADOR', privacidad='CERRADA', password='clave123', tiempo_turno=0)
    if not check(st == 201, 'Crear sala CERRADA con contrasena', resumen_error(st, d, crudo) if st != 201 else ''):
        return
    pid, tok, cod = d['id'], d['mi_token'], d['codigo_sala']
    st, r, crudo, _ = api('POST', '/partidas/unirse/', {'codigo_sala': cod, 'nombre_jugador': 'Invitado', 'password': 'mala'})
    check(st == 403, 'Contrasena incorrecta es rechazada', f'HTTP {st}')
    st, r, crudo, _ = api('POST', '/partidas/unirse/', {'codigo_sala': cod, 'nombre_jugador': 'Invitado', 'password': 'clave123'})
    check(st in (200, 201), 'Unirse con la contrasena correcta', resumen_error(st, r, crudo) if st not in (200, 201) else '')
    tok2 = (r or {}).get('mi_token')
    if tok2:
        st, r2, crudo, _ = api('POST', f'/partidas/{pid}/iniciar/', {}, tok2)
        check(st == 403, 'Solo el creador puede iniciar la batalla', f'HTTP {st}')
    st, r3, crudo, _ = api('POST', f'/partidas/{pid}/iniciar/', {}, tok)
    check(st == 200, 'El creador inicia la batalla', resumen_error(st, r3, crudo) if st != 200 else '')


# ---------------------------------------------------------------- F. Log
def revisar_log():
    titulo('F. LOG DEL BACKEND (backend/servidor.log)')
    log = BACKEND / 'servidor.log'
    if not log.exists():
        out('No existe servidor.log (se crea al abrir con la ultima version de Iniciar_Argentina.bat).')
        return
    lineas = log.read_text(encoding='utf-8', errors='replace').splitlines()
    malos = [l for l in lineas if re.search(r'Traceback|Error|locked|" 500 ', l)]
    check(not malos, 'servidor.log sin errores 500 ni excepciones',
          f'{len(malos)} lineas con errores' if malos else '')
    if malos:
        out('--- ultimas lineas relevantes del log ---')
        for l in malos[-15:]:
            out('   ' + l[:200])


# ---------------------------------------------------------------- limpieza
def limpiar():
    """Borra las partidas de prueba (QA_*) si se puede usar Django."""
    try:
        sys.path.insert(0, str(BACKEND))
        os.chdir(BACKEND)
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teg_argentina.settings')
        import django
        django.setup()
        from juego.models import Partida
        n, _ = Partida.objects.filter(nombre__startswith='QA_Argentina').delete()
        out(f'\nLimpieza: se borraron las partidas de prueba ({n} registros).')
    except Exception as e:
        out(f'\nLimpieza omitida ({type(e).__name__}: {e}). Las partidas "QA_Argentina*" quedan en la base; no molestan.')


# ---------------------------------------------------------------- servidores propios
PROCESOS = []


def arrancar_servidores():
    """Si el juego no esta abierto, levanta backend y frontend solo para esta prueba."""
    out('\nEl juego no esta corriendo: levanto backend y frontend solo para la prueba...')
    try:
        log = open(BACKEND / 'servidor.log', 'w', encoding='utf-8')
        PROCESOS.append(subprocess.Popen(
            [sys.executable, str(BACKEND / 'manage.py'), 'runserver', '127.0.0.1:8000', '--noreload'],
            cwd=str(BACKEND), stdout=log, stderr=subprocess.STDOUT))
        srv = RAIZ / 'servidor_frontend.py'
        cmd = [sys.executable, str(srv), '5500', str(FRONT)] if srv.exists() else \
            [sys.executable, '-m', 'http.server', '5500', '--bind', '127.0.0.1', '--directory', str(FRONT)]
        PROCESOS.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    except Exception as e:
        out(f'No pude levantar los servidores: {type(e).__name__}: {e}')
        return
    for _ in range(60):
        st, _, _, _ = api('GET', '/partidas/ZZZZZZ/')
        if st != 0:
            return
        time.sleep(0.5)
    out('El backend no arranco en 30 segundos (mira backend/servidor.log).')


def detener_servidores():
    for p in PROCESOS:
        try:
            p.terminate()
        except Exception:
            pass


# ---------------------------------------------------------------- main
def main():
    out('QA ARGENTINA - ' + time.strftime('%Y-%m-%d %H:%M:%S'))
    atxt = prueba_entorno()
    st0, _, _, _ = api('GET', '/partidas/ZZZZZZ/')
    if st0 == 0:
        arrancar_servidores()
    prueba_servidores(atxt)
    st, _, _, _ = api('GET', '/partidas/ZZZZZZ/')
    if st == 0:
        out('\nSe corta aca: sin backend no se puede probar el resto.')
    else:
        for prueba in (prueba_flujo, prueba_concurrencia, prueba_multijugador):
            try:
                prueba()
            except Exception as e:
                check(False, f'{prueba.__name__} se interrumpio', f'{type(e).__name__}: {e}')
        revisar_log()
        limpiar()

    titulo('RESUMEN')
    ok = sum(1 for r in RESULTADOS if r[0] == 'OK')
    avisos = [r for r in RESULTADOS if r[0] == 'AVISO']
    fallas = [r for r in RESULTADOS if r[0] == 'FALLA']
    out(f'OK: {ok}   AVISOS: {len(avisos)}   FALLAS: {len(fallas)}')
    for r in fallas:
        out(f'  FALLA: {r[1]}  ->  {r[2]}')
    for r in avisos:
        out(f'  AVISO: {r[1]}  ->  {r[2]}')
    if not fallas:
        out('Todo funciona. Si el juego sigue fallando en pantalla, es cache del navegador: cerra la ventana y abri de nuevo.')
    try:
        (RAIZ / 'qa_resultado.txt').write_text('\n'.join(LINEAS), encoding='utf-8')
        out(f'\nInforme guardado en: {RAIZ / "qa_resultado.txt"}')
    except Exception:
        pass
    detener_servidores()


if __name__ == '__main__':
    main()
