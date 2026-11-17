const API_URL = 'http://127.0.0.1:8000/api';

let partidaActual = null;
let partidaIniciada = false;
let pasandoTurnoEnCurso = false;
let miJugadorId = null;
let miToken = null;
let intervaloPolling = null;
let intervaloRelojTurno = null;
let segundosRestantes = 20;
let municipioOrigenId = null;
let municipioDestinoId = null;
let modoReagrupar = false;
let bombaActivaId = null;
let mapaSVG = null;

const CHISTES_VICTORIA = [
    "¡Tremenda paliza! Les diste más vueltas que calesita de barrio.",
    "¡Qué baile, papá! Ni con el VAR te la podían empatar.",
    "¡A cobrar! Quedaron mirando el mapa como quien mira un recibo de luz.",
    "¡Imparable! Estás más afilado que cuchillo de asador un domingo.",
    "¡Adentro! Eso fue más rápido que mandado de suegra.",
    "¡Golazo al ángulo! Mandaste esas tropas a juntar figuritas."
];

const CHISTES_CONQUISTA = [
    "¡TERRITORIO CONQUISTADO! Ya podés ir prendiendo el fuego para el asado de festejo.",
    "¡BANDERA PLANTADA! Desalojo exprés, ni tiempo de juntar el mate les diste.",
    "¡ADENTRO! Este territorio ahora tiene nuevo dueño y paga impuestos en empanadas."
];

const CHISTES_DERROTA = [
    "¡Te sacaron paseando! Tiraste los dados con los ojos cerrados, hermano.",
    "¡Afuera! Te rebotaron más rápido que cheque sin fondos.",
    "¡Qué pecheada histórica! Esos dados tenían menos fuerza que un té de tilo.",
    "¡Alpiste, perdiste! Te defendieron con una ojota y te ganaron igual.",
    "¡Mamita querida! Con esa puntería no le pegás ni al arcoíris.",
    "¡Te hicieron precio! Por suerte no apostaste el fernet del sábado."
];

const MENSAJES_CARGA_TACTICA = [
    "⚠️ RECORDÁ ESTO ANTES DE MOVER UNA TROPA: Así como en cada provincia podés encontrar refuerzos, armamento y ventajas geográficas... también te esperan emboscadas, cartas trampa y climas hostiles.",
    "☠️ ZONA DE RIESGO EXTREMO: El mazo esconde tanto bombas aéreas como cartas trampa que te hacen perder el turno o congelan tus ejércitos.",
    "⚠️ ADVERTENCIA DE CAMPAÑA: Cada región tiene sus propias leyes de terreno. La Cordillera y la Patagonia castigan al atacante imprudente."
];

function obtenerFraseAleatoria(lista) {
    return lista[Math.floor(Math.random() * lista.length)];
}

function headersConAuth() {
    return {
        'Content-Type': 'application/json',
        ...(miToken ? { 'X-Player-Token': miToken } : {})
    };
}

function esMiTurnoActual() {
    return Boolean(miJugadorId && partidaActual && partidaActual.jugador_turno_id != null &&
        Number(partidaActual.jugador_turno_id) === Number(miJugadorId));
}

function esCreadorDePartida() {
    const jugadorPropio = (partidaActual?.jugadores || []).find(j => Number(j.id) === Number(miJugadorId));
    return Boolean(jugadorPropio && Number(jugadorPropio.orden) === 0);
}

function mostrarToast(mensaje, tipo = 'info') {
    const toast = document.getElementById('toast-notificacion');
    if (!toast) return;
    const estilos = {
        turno: 'background: #064e3b; color: #a7f3d0; border: 2px solid #10b981;',
        espera: 'background: #1e293b; color: #fde68a; border: 2px solid #f59e0b;',
        alerta: 'background: #7f1d1d; color: #fecaca; border: 2px solid #ef4444;',
        info: 'background: #0f172a; color: #bae6fd; border: 2px solid #38bdf8;'
    };
    toast.setAttribute('style', estilos[tipo] || estilos.info);
    toast.innerHTML = mensaje;
    toast.classList.remove('hidden');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.add('hidden'), 3800);
}

function obtenerVecinosGeo(municipioNombre) {
    if (!partidaActual) return [];
    const esNacional = partidaActual.tipo_mapa === 'NACIONAL';
    const features = esNacional
        ? (typeof GEOJSON_NACIONAL !== 'undefined' ? GEOJSON_NACIONAL.features : [])
        : (typeof GEOJSON_DEPARTAMENTOS !== 'undefined' ? (GEOJSON_DEPARTAMENTOS[partidaActual.provincia_seleccionada] || []) : []);

    const fOrigen = features.find(f => (f.properties?.nombre || '').toLowerCase().trim() === municipioNombre.toLowerCase().trim());
    if (!fOrigen) return [];

    const coordsOrigen = JSON.stringify(fOrigen.geometry.coordinates).match(/-?\d+\.\d+/g) || [];
    const puntosOrigen = new Set();
    for (let i = 0; i < coordsOrigen.length - 1; i += 2) {
        puntosOrigen.add(`${Number(coordsOrigen[i]).toFixed(2)},${Number(coordsOrigen[i + 1]).toFixed(2)}`);
    }

    const vecinosNombres = new Set();
    features.forEach(f => {
        const nom = (f.properties?.nombre || '').trim();
        if (!nom || nom.toLowerCase() === municipioNombre.toLowerCase().trim()) return;
        const coords = JSON.stringify(f.geometry.coordinates).match(/-?\d+\.\d+/g) || [];
        for (let i = 0; i < coords.length - 1; i += 2) {
            const key = `${Number(coords[i]).toFixed(2)},${Number(coords[i + 1]).toFixed(2)}`;
            if (puntosOrigen.has(key)) {
                vecinosNombres.add(nom.toLowerCase());
                break;
            }
        }
    });

    return partidaActual.tablero.filter(t => vecinosNombres.has(t.municipio_nombre.toLowerCase().trim()));
}

function mostrarPantallaCarga10Seg(callback) {
    const modalCarga = document.getElementById('modal-carga-tactica');
    const txtCarga = document.getElementById('mensaje-carga-tactica');
    const barra = document.getElementById('barra-carga-tactica');
    const contadorTxt = document.getElementById('contador-carga-tactica');

    if (txtCarga) txtCarga.innerText = obtenerFraseAleatoria(MENSAJES_CARGA_TACTICA);
    if (barra) barra.style.width = '100%';
    if (contadorTxt) contadorTxt.innerText = 'Desplegando tropas en 10s...';
    if (modalCarga) modalCarga.classList.remove('hidden');

    let restantes = 10;
    const timerCarga = setInterval(() => {
        restantes -= 1;
        if (barra) barra.style.width = `${Math.max(0, restantes * 10)}%`;
        if (contadorTxt) contadorTxt.innerText = `Desplegando tropas en ${Math.max(0, restantes)}s...`;
        if (restantes <= 0) {
            clearInterval(timerCarga);
            if (modalCarga) modalCarga.classList.add('hidden');
            if (callback) callback();
        }
    }, 1000);
}

function iniciarRelojTurno() {
    if (intervaloRelojTurno) clearInterval(intervaloRelojTurno);
    const relojEl = document.getElementById('reloj-turno');
    if (!partidaActual || !partidaActual.activa || !partidaIniciada) {
        if (relojEl) relojEl.classList.add('hidden');
        return;
    }

    segundosRestantes = Math.max(0, Number(partidaActual.segundos_restantes ?? partidaActual.tiempo_turno ?? 20));
    if (relojEl) {
        relojEl.classList.remove('hidden');
        relojEl.style.color = '#facc15';
        relojEl.innerText = `⏱️ ${segundosRestantes}s`;
    }

    intervaloRelojTurno = setInterval(() => {
        if (!partidaActual || !partidaActual.activa || !partidaIniciada) {
            clearInterval(intervaloRelojTurno);
            intervaloRelojTurno = null;
            return;
        }
        segundosRestantes = Math.max(0, segundosRestantes - 1);
        if (relojEl) {
            relojEl.innerText = `⏱️ ${segundosRestantes}s`;
            relojEl.style.color = segundosRestantes <= 5 ? '#f38ba8' : '#facc15';
        }
        if (segundosRestantes <= 0 && !pasandoTurnoEnCurso) {
            clearInterval(intervaloRelojTurno);
            intervaloRelojTurno = null;
            mostrarToast('⏰ Tiempo agotado. El servidor está validando el cambio de turno...', 'alerta');
            ejecutarPasarTurno(true);
        }
    }, 1000);
}

function iniciarPollingMultijugador() {
    if (intervaloPolling) clearInterval(intervaloPolling);
    intervaloPolling = setInterval(() => {
        if (!partidaActual || !partidaActual.activa) return;
        actualizarEstadoPartida(false);
    }, 3000);
}

window.addEventListener('beforeunload', (e) => {
    if (partidaActual && partidaActual.activa && partidaIniciada) {
        e.preventDefault();
        e.returnValue = '';
    }
});

function poblarProvincias() {
    const selectProv = document.getElementById('crear-provincia');
    if (!selectProv || selectProv.options.length > 0) return;
    const listaProvincias = (typeof GEOJSON_DEPARTAMENTOS !== 'undefined') ? Object.keys(GEOJSON_DEPARTAMENTOS).sort() : ["Mendoza", "Buenos Aires", "Córdoba"];
    listaProvincias.forEach(prov => {
        const opt = document.createElement('option');
        opt.value = prov;
        opt.textContent = prov;
        if (prov === 'Mendoza') opt.selected = true;
        selectProv.appendChild(opt);
    });
}

function sincronizarVisibilidadMapa() {
    const tipoMapa = document.getElementById('crear-tipo-mapa').value;
    const grupoProv = document.getElementById('grupo-provincia');
    if (tipoMapa === 'PROVINCIAL') grupoProv.classList.remove('hidden');
    else grupoProv.classList.add('hidden');
}

window.addEventListener('DOMContentLoaded', () => {
    poblarProvincias();
    sincronizarVisibilidadMapa();
});

document.getElementById('btn-nueva-partida').addEventListener('click', () => {
    if (partidaActual && partidaActual.activa) {
        mostrarToast("Ya tenés una sala activa.", "alerta");
        return;
    }
    poblarProvincias();
    sincronizarVisibilidadMapa();
    abrirModal('modal-crear-partida');
});

document.getElementById('btn-unirse-partida').addEventListener('click', () => {
    if (partidaActual && partidaActual.activa) {
        mostrarToast("Ya estás dentro de una sala activa.", "alerta");
        return;
    }
    abrirModal('modal-unirse-partida');
});

document.getElementById('form-crear-partida').addEventListener('submit', async (e) => {
    e.preventDefault();
    const nombre = document.getElementById('crear-nombre').value;
    const modo_juego = document.getElementById('crear-modo').value;
    const tipo_mapa = document.getElementById('crear-tipo-mapa').value;
    const provincia = document.getElementById('crear-provincia').value;
    const tiempo_turno = parseInt(document.getElementById('crear-tiempo-turno').value || '20', 10);
    const privacidad = document.getElementById('crear-privacidad').value;
    const password = document.getElementById('crear-password').value;
    const jugador = document.getElementById('crear-jugador').value;
    const color = document.getElementById('crear-color').value;

    let departamentos_provincia = [];
    if (tipo_mapa === 'PROVINCIAL' && typeof GEOJSON_DEPARTAMENTOS !== 'undefined' && GEOJSON_DEPARTAMENTOS[provincia]) {
        departamentos_provincia = GEOJSON_DEPARTAMENTOS[provincia].map(f => f.properties.nombre);
    }

    try {
        const res = await fetch(`${API_URL}/partidas/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nombre, modo_juego, tipo_mapa, privacidad, password,
                provincia, tiempo_turno, departamentos_provincia, color,
                jugadores: [jugador]
            })
        });
        const data = await res.json();
        if (!res.ok) { alert(data.error); return; }

        partidaActual = data;
        partidaIniciada = false;
        miJugadorId = data.mi_jugador_id || null;
        miToken = data.mi_token || null;

        cerrarModal('modal-crear-partida');
        actualizarHeader();
        renderizarTablero(partidaActual.tablero);
        renderizarPanelesLaterales();
        iniciarPollingMultijugador();

        if (modo_juego === 'VS_IA') {
            mostrarPantallaCarga10Seg(() => iniciarPartidaEnServidor());
        } else {
            mostrarSalaCreada();
        }
    } catch (err) { console.error('Error al crear:', err); }
});

const btnIniciarBatalla = document.getElementById('btn-iniciar-batalla');
async function iniciarPartidaEnServidor() {
    if (!partidaActual || !partidaActual.activa || partidaIniciada) return;
    try {
        const res = await fetch(`${API_URL}/partidas/${partidaActual.id}/iniciar/`, {
            method: 'POST', headers: headersConAuth(), body: JSON.stringify({})
        });
        const data = await res.json();
        if (!res.ok) {
            mostrarToast(data.error || 'No se pudo iniciar la partida.', 'alerta');
            await actualizarEstadoPartida(false);
            return;
        }
        partidaActual = data;
        partidaIniciada = Boolean(data.iniciada);
        actualizarHeader();
        renderizarTablero(partidaActual.tablero);
        renderizarPanelesLaterales();
        actualizarResaltadosMapa();
        iniciarRelojTurno();
    } catch (err) {
        console.error('Error al iniciar partida:', err);
        mostrarToast(`No se pudo iniciar la partida (${err && err.message ? err.message : 'sin conexión'}). Revisá backend\\servidor.log.`, 'alerta');
    }
}

if (btnIniciarBatalla) {
    btnIniciarBatalla.addEventListener('click', () => {
        if (!partidaActual || !partidaActual.activa || partidaIniciada) return;
        btnIniciarBatalla.disabled = true;
        mostrarPantallaCarga10Seg(async () => {
            await iniciarPartidaEnServidor();
            btnIniciarBatalla.disabled = false;
        });
    });
}

document.getElementById('form-unirse-partida').addEventListener('submit', async (e) => {
    e.preventDefault();
    const codigo_sala = document.getElementById('unirse-codigo').value.trim().toUpperCase();
    const nombre_jugador = document.getElementById('unirse-jugador').value.trim();
    const color = document.getElementById('unirse-color').value;
    const password = document.getElementById('unirse-password').value;

    try {
        const res = await fetch(`${API_URL}/partidas/unirse/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ codigo_sala, nombre_jugador, color, password })
        });
        const data = await res.json();
        if (!res.ok) { alert(data.error); return; }

        partidaActual = data;
        partidaIniciada = Boolean(data.iniciada);
        miJugadorId = data.mi_jugador_id || null;
        miToken = data.mi_token || null;

        cerrarModal('modal-unirse-partida');
        actualizarHeader();
        renderizarTablero(partidaActual.tablero);
        renderizarPanelesLaterales();
        if (partidaIniciada) iniciarRelojTurno();
        iniciarPollingMultijugador();
    } catch (err) { console.error('Error al unirse:', err); }
});

async function ejecutarPasarTurno(porTiempoAgotado = false) {
    if (!partidaActual || !partidaIniciada || pasandoTurnoEnCurso) return;
    pasandoTurnoEnCurso = true;

    try {
        const res = await fetch(`${API_URL}/pasar-turno/${partidaActual.id}/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({ por_tiempo: porTiempoAgotado })
        });
        const data = await res.json();
        
        if (!res.ok) {
            if (!porTiempoAgotado) mostrarToast(data.error || 'No se pudo pasar turno', 'alerta');
            pasandoTurnoEnCurso = false;
            await actualizarEstadoPartida(true);
            return;
        }

        if (data.acciones_ia && data.acciones_ia.length > 0) {
            mostrarToast(data.acciones_ia[data.acciones_ia.length - 1], 'espera');
        }
        anunciarResultadoTurno(data);

        municipioOrigenId = null;
        municipioDestinoId = null;
        modoReagrupar = false;
        bombaActivaId = null;

        await actualizarEstadoPartida(true);
    } catch (err) {
        console.error('Error al pasar turno:', err);
        await actualizarEstadoPartida(true);
    } finally {
        pasandoTurnoEnCurso = false;
    }
}

document.getElementById('btn-pasar-turno').addEventListener('click', () => ejecutarPasarTurno(false));

function abrirModal(id) { document.getElementById(id).classList.remove('hidden'); }
function cerrarModal(id) { document.getElementById(id).classList.add('hidden'); }

function mostrarModalResultado(titulo, detalleHTML, chiste) {
    document.getElementById('resultado-titulo').innerText = titulo;
    document.getElementById('resultado-dados').innerHTML = detalleHTML;
    document.getElementById('resultado-chiste').innerText = `"${chiste}"`;
    abrirModal('modal-resultado');
}

function actualizarResaltadosMapa() {
    if (!mapaSVG || !partidaActual) return;
    mapaSVG.limpiarResaltados();

    const turnoActualId = partidaActual.jugador_turno_id;
    const esMiTurno = esMiTurnoActual();
    
    if (!esMiTurno || !partidaIniciada) return;

    const miId = miJugadorId;

    if (!modoReagrupar && !bombaActivaId && partidaActual.jugador_turno_tropas > 0) {
        const propiosIds = partidaActual.tablero
            .filter(t => Number(t.jugador_id) === Number(miId))
            .map(t => t.municipio_id);
        if (typeof mapaSVG.resaltarReforzables === 'function') {
            mapaSVG.resaltarReforzables(propiosIds);
        } else if (typeof mapaSVG.resaltarDestinos === 'function') {
            mapaSVG.resaltarDestinos(propiosIds, 'territorio-reforzable');
        }
        return;
    }

    if (modoReagrupar && !municipioOrigenId) {
        const aptosOrigen = partidaActual.tablero
            .filter(t => (Number(t.jugador_id) === Number(miId)) && t.tropas >= 2)
            .map(t => t.municipio_id);
        mapaSVG.resaltarDestinos(aptosOrigen, 'territorio-destino-reagrupe');
        return;
    }

    if (!municipioOrigenId) return;

    if (typeof mapaSVG.resaltarOrigen === 'function') {
        mapaSVG.resaltarOrigen(municipioOrigenId);
    }
    const celdaOrigen = partidaActual.tablero.find(t => t.municipio_id === municipioOrigenId);
    if (!celdaOrigen) return;

    const vecinos = obtenerVecinosGeo(celdaOrigen.municipio_nombre);
    if (modoReagrupar) {
        const destinosPropios = vecinos.filter(v => Number(v.jugador_id) === Number(miId)).map(v => v.municipio_id);
        mapaSVG.resaltarDestinos(destinosPropios, 'territorio-destino-reagrupe');
    } else {
        const destinosEnemigos = vecinos.filter(v => Number(v.jugador_id) !== Number(miId)).map(v => v.municipio_id);
        mapaSVG.resaltarDestinos(destinosEnemigos, 'territorio-destino-ataque');
    }
}

function resaltarReforzables(ids) {
    if (mapaSVG && typeof mapaSVG.resaltarReforzables === 'function') {
        mapaSVG.resaltarReforzables(ids);
    }
}

function actualizarHeader() {
    if (!partidaActual) return;
    const mapaDesc = partidaActual.tipo_mapa === 'NACIONAL' ? 'Nacional' : `Provincial (${partidaActual.provincia_seleccionada})`;
    const jugadorActivo = (partidaActual.jugadores || []).find(j => j.id === partidaActual.jugador_turno_id);
    const etiquetaTipoActivo = jugadorActivo ? (jugadorActivo.es_ia ? '🤖 IA' : (esMiTurnoActual() ? '⚡ VOS' : 'RIVAL')) : '';

    const codigoSalaEl = document.getElementById('codigo-sala');
    if (codigoSalaEl) {
        codigoSalaEl.innerText = `Sala: ${partidaActual.codigo_sala} | ${mapaDesc} | Turno: ${partidaActual.jugador_turno_nombre} (${etiquetaTipoActivo})`;
    }
    const tituloMapaEl = document.getElementById('titulo-mapa');
    if (tituloMapaEl) {
        tituloMapaEl.innerText = `Territorios — ${mapaDesc}`;
    }

    const btnNueva = document.getElementById('btn-nueva-partida');
    const btnUnirse = document.getElementById('btn-unirse-partida');
    const btnIniciar = document.getElementById('btn-iniciar-batalla');
    const btnPasar = document.getElementById('btn-pasar-turno');
    const badgeRef = document.getElementById('badge-refuerzos');
    const banner = document.getElementById('banner-alerta-turno');
    const bannerTitulo = document.getElementById('banner-turno-titulo');
    const bannerPasos = document.getElementById('banner-turno-pasos');

    if (!partidaActual.activa) {
        if (intervaloRelojTurno) clearInterval(intervaloRelojTurno);
        if (btnNueva) btnNueva.classList.remove('hidden');
        if (btnUnirse) btnUnirse.classList.remove('hidden');
        if (btnIniciar) btnIniciar.classList.add('hidden');
        if (btnPasar) btnPasar.classList.add('hidden');
        if (banner) banner.classList.add('hidden');
        return;
    }

    if (btnNueva) btnNueva.classList.add('hidden');
    if (btnUnirse) btnUnirse.classList.add('hidden');

    if (!partidaIniciada) {
        if (btnIniciar) {
            btnIniciar.classList.toggle('hidden', !esCreadorDePartida());
            btnIniciar.disabled = false;
        }
        if (btnPasar) btnPasar.classList.add('hidden');
        if (banner) {
            banner.classList.remove('hidden');
            if (bannerTitulo) bannerTitulo.innerText = '⏸️ SALA PREPARADA — PULSÁ "🚀 INICIAR BATALLA"';
            if (bannerPasos) bannerPasos.innerText = esCreadorDePartida() ? 'Cuando todos estén listos, iniciá la batalla con el botón superior.' : 'Esperando a que quien creó la sala inicie la batalla.';
        }
        return;
    }

    if (btnIniciar) btnIniciar.classList.add('hidden');
    if (btnPasar) btnPasar.classList.toggle('hidden', !esMiTurnoActual());

    const turnoActualId = partidaActual.jugador_turno_id;
    const esMiTurno = esMiTurnoActual();
    if (banner) banner.classList.remove('hidden');

    if (!esMiTurno) {
        if (badgeRef) badgeRef.classList.add('hidden');
        if (bannerTitulo) bannerTitulo.innerText = `⏳ TURNO DE ${String(partidaActual.jugador_turno_nombre || 'OTRO JUGADOR').toUpperCase()}`;
        if (bannerPasos) {
            if (jugadorActivo && jugadorActivo.es_ia) bannerPasos.innerText = 'La inteligencia artificial está realizando su jugada.';
            else if (Number(partidaActual.jugador_turno_tropas) > 0) bannerPasos.innerText = `Está colocando ${partidaActual.jugador_turno_tropas} refuerzos en sus territorios.`;
            else bannerPasos.innerText = 'Está en fase de ataque o maniobras. Esperá el cambio de turno; el reloj sigue corriendo.';
        }
        return;
    }

    if (partidaActual.jugador_turno_tropas > 0) {
        if (badgeRef) badgeRef.classList.remove('hidden');
        const cantRefEl = document.getElementById('cant-refuerzos');
        if (cantRefEl) cantRefEl.innerText = partidaActual.jugador_turno_tropas;
        if (bannerTitulo) bannerTitulo.innerText = `⚡ ¡ES TU TURNO! — DESPLEGÁ TUS ${partidaActual.jugador_turno_tropas} REFUERZOS`;
        if (bannerPasos) bannerPasos.innerText = 'Hacé clic en cualquiera de TUS territorios celestes en el mapa o en el botón "+1 🪖" lateral.';
    } else {
        if (badgeRef) badgeRef.classList.add('hidden');
        if (bannerTitulo) bannerTitulo.innerText = modoReagrupar ? '🔄 FASE DE REAGRUPAMIENTO' : '⚔️ FASE DE ATAQUE Y MANIOBRAS';
        if (bannerPasos) bannerPasos.innerText = modoReagrupar ? 'Seleccioná un territorio propio y luego otro territorio propio conectado para mover tropas.' : 'Seleccioná un territorio propio (2+ tropas) y después un territorio enemigo para atacar.';
    }
}

function renderizarTablero(tablero) {
    if (!mapaSVG) {
        mapaSVG = new MapaArgentinaSVG('mapa-container', {
            onTerritorioClick: (id) => seleccionarTerritorio(id)
        });
    }
    mapaSVG.cargarMapa(tablero, partidaActual.provincia_seleccionada);
    actualizarResaltadosMapa();
}

async function desplegarRefuerzoDirecto(municipioId) {
    if (!partidaActual || !partidaActual.activa || !partidaIniciada) return;
    try {
        const res = await fetch(`${API_URL}/reforzar/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({
                partida_id: partidaActual.id,
                municipio_id: municipioId,
                cantidad: 1
            })
        });
        const data = await res.json();
        if (res.ok) {
            mostrarToast(`➕ +1 tropa desplegada en ${data.municipio}`, 'turno');
            await actualizarEstadoPartida(false);
        } else {
            mostrarToast(data.error || 'No se pudo reforzar.', 'alerta');
        }
    } catch (e) { console.error('Error al reforzar:', e); }
}

function renderizarPanelesLaterales() {
    if (!partidaActual) return;
    const misTerritoriosDiv = document.getElementById('lista-mis-territorios');
    const statsDiv = document.getElementById('lista-jugadores-stats');
    const turnoActualId = partidaActual.jugador_turno_id;
    const miId = miJugadorId;
    const esMiTurno = esMiTurnoActual();
    const puedeReforzar = partidaIniciada && esMiTurno && partidaActual.jugador_turno_tropas > 0;

    if (statsDiv) {
        let htmlStats = '';
        partidaActual.jugadores.forEach(jug => {
            const celdasJ = partidaActual.tablero.filter(t => t.jugador_id === jug.id);
            const totalTropas = celdasJ.reduce((acc, t) => acc + t.tropas, 0);
            htmlStats += `<div class="stat-item" style="padding: 6px; background: #0f131d; border-radius: 6px; margin-bottom: 4px; display: flex; justify-content: space-between;"><span>${jug.nombre}</span><strong>⚔️ ${totalTropas}</strong></div>`;
        });
        statsDiv.innerHTML = htmlStats;
    }

    if (misTerritoriosDiv) {
        let htmlMis = '';
        partidaActual.tablero.forEach(t => {
            if (Number(t.jugador_id) === Number(miId)) {
                const btnPlus = puedeReforzar
                    ? `<button type="button" class="btn-reforzar-directo" onclick="desplegarRefuerzoDirecto(${t.municipio_id})" style="background:#38bdf8; color:#090d16; border:none; border-radius:6px; padding:2px 8px; font-weight:800; cursor:pointer; font-size:0.78rem;">+1 🪖</button>`
                    : '';
                htmlMis += `
                    <div class="territory-item" style="display:flex; justify-content:space-between; align-items:center; width:100%; padding:6px; background:#0f131d; margin-bottom:4px; border-radius:6px;">
                        <span>📍 ${t.municipio_nombre}</span>
                        <div style="display:flex; align-items:center; gap:6px;">
                            <strong>⚔️ ${t.tropas}</strong>
                            ${btnPlus}
                        </div>
                    </div>
                `;
            }
        });
        misTerritoriosDiv.innerHTML = htmlMis || '<p class="empty-msg">Sin territorios propios</p>';
    }
}

async function seleccionarTerritorio(id) {
    if (!partidaActual || !partidaActual.activa || !partidaIniciada) return;
    const turnoActualId = partidaActual.jugador_turno_id;
    const esMiTurno = esMiTurnoActual();
    if (!esMiTurno) {
        mostrarToast('⏳ Esperá tu turno.', 'espera');
        return;
    }

    const celdaTocada = partidaActual.tablero.find(t => t.municipio_id === id);

    if (partidaActual.jugador_turno_tropas > 0) {
        if (celdaTocada && Number(celdaTocada.jugador_id) === Number(miJugadorId)) {
            await desplegarRefuerzoDirecto(id);
            return;
        } else {
            mostrarToast('Colocá tus refuerzos en TUS territorios celestes.', 'alerta');
            return;
        }
    }

    if (!municipioOrigenId) {
        if (!celdaTocada || Number(celdaTocada.jugador_id) !== Number(miJugadorId)) {
            mostrarToast('Tocá uno de TUS territorios para atacar.', 'alerta');
            return;
        }
        if (celdaTocada.tropas < 2) {
            mostrarToast('Necesitás mínimo 2 tropas para atacar.', 'alerta');
            return;
        }
        municipioOrigenId = id;
        actualizarHeader();
        actualizarResaltadosMapa();
        return;
    }

    if (municipioOrigenId === id) {
        municipioOrigenId = null;
        actualizarHeader();
        actualizarResaltadosMapa();
        return;
    }

    municipioDestinoId = id;
    prepararAtaque(municipioOrigenId, municipioDestinoId);
}

async function prepararAtaque(origenId, destinoId) {
    try {
        const res = await fetch(`${API_URL}/preparar-ataque/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({
                partida_id: partidaActual.id,
                origen_id: origenId,
                destino_id: destinoId
            })
        });
        const data = await res.json();
        if (!res.ok) {
            mostrarToast(data.error, 'alerta');
            municipioOrigenId = null;
            municipioDestinoId = null;
            actualizarHeader();
            actualizarResaltadosMapa();
            return;
        }
        triviaActual = data.trivia;
        mostrarOpcionesAtaque(data);
    } catch (err) { console.error('Error preparando ataque:', err); }
}

function crearBotonOpcion(texto, estilo, onClick) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'opcion-btn';
    if (estilo) btn.setAttribute('style', estilo);
    btn.textContent = texto;
    btn.addEventListener('click', onClick);
    return btn;
}

function cancelarCombatePendiente() {
    cerrarModal('modal-trivia');
    municipioOrigenId = null;
    municipioDestinoId = null;
    actualizarHeader();
    actualizarResaltadosMapa();
}

function mostrarPreguntaTrivia(dataAtaque, modalidad) {
    const contenedorOpciones = document.getElementById('trivia-opciones');
    const pregunta = dataAtaque.trivia;
    document.getElementById('trivia-pregunta').innerText = pregunta.texto;
    contenedorOpciones.innerHTML = '';
    (pregunta.opciones || []).forEach(op => {
        contenedorOpciones.appendChild(crearBotonOpcion(op.texto, '', () => ejecutarCombateDirecto(modalidad, op.id)));
    });
}

function mostrarOpcionesAtaque(dataAtaque) {
    document.getElementById('trivia-categoria').innerText = `Combate: ${dataAtaque.origen} vs ${dataAtaque.destino}`;

    const terrenoEl = document.getElementById('trivia-terreno-info');
    if (terrenoEl) {
        const t = dataAtaque.info_terreno;
        terrenoEl.textContent = t ? `${t.icono} ${t.bioma} — ${t.beneficio_def}` : '';
        terrenoEl.classList.toggle('hidden', !t);
    }

    const tienePregunta = Boolean(dataAtaque.trivia && dataAtaque.trivia.opciones && dataAtaque.trivia.opciones.length);

    if (dataAtaque.trivia_obligatoria && tienePregunta) {
        document.getElementById('trivia-categoria').innerText = `⚠️ TRIVIA OBLIGATORIA — ${dataAtaque.origen} vs ${dataAtaque.destino}`;
        mostrarPreguntaTrivia(dataAtaque, 'TRIVIA_OBLIGATORIA');
        abrirModal('modal-trivia');
        return;
    }

    document.getElementById('trivia-pregunta').innerText = 'Elegí la modalidad de combate:';
    const contenedorOpciones = document.getElementById('trivia-opciones');
    contenedorOpciones.innerHTML = '';
    contenedorOpciones.appendChild(crearBotonOpcion(
        'Ataque Directo por Dados', 'background:#38bdf8; color:#090d16; font-weight:bold;',
        () => ejecutarCombateDirecto()
    ));
    if (tienePregunta) {
        contenedorOpciones.appendChild(crearBotonOpcion(
            '🧠 Trivia Argentina (+1 al dado si acertás, +1 defensa rival si fallás)', 'background:#facc15; color:#090d16; font-weight:bold;',
            () => mostrarPreguntaTrivia(dataAtaque, 'TRIVIA')
        ));
    }
    contenedorOpciones.appendChild(crearBotonOpcion('Cancelar', 'background:#1e293b; color:#cbd5e1;', cancelarCombatePendiente));
    abrirModal('modal-trivia');
}

async function ejecutarCombateDirecto(modalidad = 'DADOS', opcionId = null) {
    try {
        const res = await fetch(`${API_URL}/resolver-combate/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({
                partida_id: partidaActual.id,
                origen_id: municipioOrigenId,
                destino_id: municipioDestinoId,
                modalidad: modalidad,
                opcion_id: opcionId
            })
        });
        const r = await res.json();
        cerrarModal('modal-trivia');

        if (!res.ok) {
            mostrarToast(r.error || 'No se pudo resolver el combate.', 'alerta');
            municipioOrigenId = null;
            municipioDestinoId = null;
            await actualizarEstadoPartida(false);
            return;
        }

        const gano = r.resultado === 'victoria';
        let detalle = `<strong>Tu Dado:</strong> ${r.dado_ataque} vs <strong>Defensa:</strong> ${r.dado_defensa}`;
        if (r.trivia_correcta === true) detalle = `✅ Trivia correcta<br>${detalle}`;
        if (r.trivia_correcta === false) detalle = `❌ Trivia incorrecta<br>${detalle}`;
        if (Array.isArray(r.notas_terreno) && r.notas_terreno.length) {
            detalle += `<br><small style="color:#94a3b8;">${r.notas_terreno.join('<br>')}</small>`;
        }
        if (r.conquistado) detalle += '<br><strong style="color:#a6e3a1;">🚩 ¡Territorio conquistado!</strong>';

        mostrarModalResultado(
            r.conquistado ? '🚩 ¡Territorio Conquistado!' : (gano ? '🏆 ¡Ganaste la Tirada!' : '💀 ¡Perdiste la Tirada!'),
            detalle,
            r.conquistado ? obtenerFraseAleatoria(CHISTES_CONQUISTA)
                : (gano ? obtenerFraseAleatoria(CHISTES_VICTORIA) : obtenerFraseAleatoria(CHISTES_DERROTA))
        );
        municipioOrigenId = null;
        municipioDestinoId = null;
        await actualizarEstadoPartida(false);
    } catch (err) { console.error('Error en combate:', err); }
}

async function actualizarEstadoPartida(reiniciarReloj = false) {
    try {
        const res = await fetch(`${API_URL}/partidas/${partidaActual.codigo_sala}/`);
        if (!res.ok) return;
        const nuevaPartida = await res.json();
        const turnoAnteriorId = partidaActual ? Number(partidaActual.jugador_turno_id) : null;
        const inicioAnterior = partidaIniciada;
        const turnoNuevoId = nuevaPartida.jugador_turno_id == null ? null : Number(nuevaPartida.jugador_turno_id);
        const cambioTurno = turnoAnteriorId !== turnoNuevoId;
        const segundosServidor = Math.max(0, Number(nuevaPartida.segundos_restantes ?? nuevaPartida.tiempo_turno ?? 20));

        partidaActual = nuevaPartida;
        partidaIniciada = Boolean(nuevaPartida.iniciada);
        actualizarHeader();
        renderizarTablero(partidaActual.tablero);
        renderizarPanelesLaterales();

        if (partidaIniciada && (reiniciarReloj || cambioTurno || !inicioAnterior ||
            Math.abs(segundosRestantes - segundosServidor) >= 3)) {
            iniciarRelojTurno();
        } else if (!partidaIniciada && intervaloRelojTurno) {
            clearInterval(intervaloRelojTurno);
            intervaloRelojTurno = null;
        }
        if (cambioTurno && turnoNuevoId !== null) {
            const nombre = partidaActual.jugador_turno_nombre || 'Jugador siguiente';
            mostrarToast(esMiTurnoActual() ? `⚔️ ¡Ahora te toca a vos!` : `⏳ Ahora juega ${nombre}.`, esMiTurnoActual() ? 'turno' : 'espera');
        }
    } catch (err) { console.error('Error actualizando estado:', err); }
}


/* =====================================================================
   BLOQUE AGREGADO — Funciones que el index.html ya usaba y faltaban.
   No reemplaza lógica anterior: envuelve las funciones existentes.
   ===================================================================== */

let cartasSeleccionadas = [];
let cartaBeneficioId = null;
let finPartidaAnunciada = null;

const VECINOS_EXTRA_NACIONAL = {
    'chubut': ['río negro', 'santa cruz'],
    'río negro': ['chubut'],
    'santa cruz': ['chubut']
};

function escaparHTML(texto) {
    return String(texto ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function obtenerMiJugador() {
    return (partidaActual?.jugadores || []).find(j => Number(j.id) === Number(miJugadorId)) || null;
}

function enemigosIds() {
    return (partidaActual?.tablero || [])
        .filter(t => Number(t.jugador_id) !== Number(miJugadorId))
        .map(t => t.municipio_id);
}

// Dos territorios son limítrofes según el mapa. Si el mapa no permite saberlo
// (territorio sin vecinos detectados), no se bloquea la jugada.
function sonLimitrofes(idA, idB) {
    const a = partidaActual.tablero.find(t => t.municipio_id === idA);
    const b = partidaActual.tablero.find(t => t.municipio_id === idB);
    if (!a || !b) return false;
    const nomA = a.municipio_nombre.toLowerCase().trim();
    const nomB = b.municipio_nombre.toLowerCase().trim();

    if (partidaActual.tipo_mapa === 'NACIONAL' && (VECINOS_EXTRA_NACIONAL[nomA] || []).includes(nomB)) return true;

    const vecinosA = obtenerVecinosGeo(a.municipio_nombre);
    const vecinosB = obtenerVecinosGeo(b.municipio_nombre);
    if (vecinosA.some(v => v.municipio_id === idB) || vecinosB.some(v => v.municipio_id === idA)) return true;
    return vecinosA.length === 0 || vecinosB.length === 0;
}

/* ---------- Sala creada / compartir código ---------- */

function mostrarSalaCreada() {
    if (!partidaActual) return;
    const codigoEl = document.getElementById('info-codigo-creado');
    const privEl = document.getElementById('info-privacidad-creada');
    if (codigoEl) codigoEl.innerText = partidaActual.codigo_sala;
    if (privEl) privEl.innerText = partidaActual.privacidad === 'CERRADA'
        ? '🔒 Sala privada: pasales también la contraseña.'
        : '🌐 Sala abierta: cualquiera con el código puede entrar.';
    abrirModal('modal-sala-creada');
}

async function copiarTexto(texto) {
    try {
        await navigator.clipboard.writeText(texto);
        return true;
    } catch (e) {
        const tmp = document.createElement('textarea');
        tmp.value = texto;
        document.body.appendChild(tmp);
        tmp.select();
        let ok = false;
        try { ok = document.execCommand('copy'); } catch (e2) { ok = false; }
        document.body.removeChild(tmp);
        return ok;
    }
}

document.getElementById('btn-ver-codigo').addEventListener('click', mostrarSalaCreada);

document.getElementById('btn-copiar-codigo').addEventListener('click', async () => {
    if (!partidaActual) return;
    const ok = await copiarTexto(partidaActual.codigo_sala);
    mostrarToast(ok ? `📋 Código ${partidaActual.codigo_sala} copiado.` : `Código de sala: ${partidaActual.codigo_sala}`, 'info');
});

/* ---------- Contraseña de sala cerrada ---------- */

document.getElementById('crear-privacidad').addEventListener('change', (e) => {
    const campo = document.getElementById('campo-password');
    if (campo) campo.classList.toggle('hidden', e.target.value !== 'CERRADA');
});

/* ---------- Reagrupamiento ---------- */

function salirModoReagrupar() {
    modoReagrupar = false;
    municipioOrigenId = null;
    municipioDestinoId = null;
}

document.getElementById('btn-modo-reagrupar').addEventListener('click', () => {
    if (!esMiTurnoActual() || !partidaIniciada) return;
    if (Number(partidaActual.jugador_turno_tropas) > 0) {
        mostrarToast('Primero desplegá todos tus refuerzos.', 'alerta');
        return;
    }
    bombaActivaId = null;
    municipioOrigenId = null;
    municipioDestinoId = null;
    modoReagrupar = !modoReagrupar;
    if (modoReagrupar) mostrarToast('🔄 Reagrupamiento: elegí un territorio propio de origen. Ojo: después ya no podés atacar en este turno.', 'info');
    actualizarHeader();
    actualizarResaltadosMapa();
});

async function manejarClickReagrupar(id) {
    const celda = partidaActual.tablero.find(t => t.municipio_id === id);
    if (!celda) return;
    const esPropio = Number(celda.jugador_id) === Number(miJugadorId);

    if (!municipioOrigenId) {
        if (!esPropio) { mostrarToast('Elegí primero un territorio TUYO como origen.', 'alerta'); return; }
        if (celda.tropas < 2) { mostrarToast('El origen necesita al menos 2 tropas.', 'alerta'); return; }
        municipioOrigenId = id;
        actualizarHeader();
        actualizarResaltadosMapa();
        return;
    }

    if (municipioOrigenId === id) {
        municipioOrigenId = null;
        actualizarHeader();
        actualizarResaltadosMapa();
        return;
    }

    if (!esPropio) { mostrarToast('El destino del reagrupamiento tiene que ser un territorio propio.', 'alerta'); return; }
    if (!sonLimitrofes(municipioOrigenId, id)) { mostrarToast('El municipio seleccionado no es limítrofe.', 'alerta'); return; }

    const origen = partidaActual.tablero.find(t => t.municipio_id === municipioOrigenId);
    const maximo = origen.tropas - 1;
    let cantidad = 1;
    if (maximo > 1) {
        const respuesta = window.prompt(`¿Cuántas tropas mover de ${origen.municipio_nombre} a ${celda.municipio_nombre}? (1 a ${maximo})`, String(maximo));
        if (respuesta === null) return;
        cantidad = parseInt(respuesta, 10);
        if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad > maximo) {
            mostrarToast(`Ingresá un número entre 1 y ${maximo}.`, 'alerta');
            return;
        }
    }

    try {
        const res = await fetch(`${API_URL}/mover-tropas/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({
                partida_id: partidaActual.id,
                origen_id: municipioOrigenId,
                destino_id: id,
                cantidad
            })
        });
        const data = await res.json();
        if (!res.ok) {
            mostrarToast(data.error || 'No se pudo reagrupar.', 'alerta');
        } else {
            mostrarToast(`🔄 ${data.mensaje}`, 'turno');
            if (Number(data.reagrupamientos_restantes) <= 0) {
                modoReagrupar = false;
                mostrarToast(`🔄 ${data.mensaje}. Ya no te quedan reagrupamientos: pasá el turno.`, 'turno');
            }
        }
        municipioOrigenId = null;
        municipioDestinoId = null;
        await actualizarEstadoPartida(false);
    } catch (err) { console.error('Error al reagrupar:', err); }
}

/* ---------- Cancelar selección ---------- */

document.getElementById('btn-cancelar-accion-mapa').addEventListener('click', () => {
    municipioOrigenId = null;
    municipioDestinoId = null;
    bombaActivaId = null;
    modoReagrupar = false;
    actualizarHeader();
    actualizarResaltadosMapa();
});

/* ---------- Rendirse ---------- */

document.getElementById('btn-rendirse').addEventListener('click', () => {
    if (!partidaActual || !partidaActual.activa || !partidaIniciada) return;
    abrirModal('modal-confirmar-rendicion');
});

document.getElementById('btn-confirmar-rendicion-si').addEventListener('click', async () => {
    cerrarModal('modal-confirmar-rendicion');
    if (!partidaActual || !miJugadorId) return;
    try {
        const res = await fetch(`${API_URL}/rendirse/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({ partida_id: partidaActual.id, jugador_id: miJugadorId })
        });
        const data = await res.json();
        if (!res.ok) { mostrarToast(data.error || 'No se pudo procesar la rendición.', 'alerta'); return; }
        salirModoReagrupar();
        await actualizarEstadoPartida(true);
        if (!data.victoria_final) {
            finPartidaAnunciada = `rendido-${partidaActual.id}`;
            abrirModal('modal-derrotado');
        }
    } catch (err) { console.error('Error al rendirse:', err); }
});

/* ---------- Cartas, canje, beneficios y bomba ---------- */

function misCartasActivas() {
    return (partidaActual?.cartas || []).filter(c => Number(c.jugador_id) === Number(miJugadorId) && !c.canjeada);
}

function renderizarCartas() {
    const lista = document.getElementById('lista-mis-cartas');
    const btnCanje = document.getElementById('btn-canjear-cartas');
    if (!lista || !partidaActual) return;

    const cartas = misCartasActivas();
    const idsValidos = cartas.filter(c => c.tipo_carta === 'TERRITORIO').map(c => c.id);
    cartasSeleccionadas = cartasSeleccionadas.filter(id => idsValidos.includes(id));

    if (!cartas.length) {
        lista.innerHTML = '<p class="empty-msg">Aún no tenés cartas en tu mano.</p>';
        if (btnCanje) btnCanje.classList.add('hidden');
        return;
    }

    const puedeActuar = partidaIniciada && partidaActual.activa && esMiTurnoActual();
    lista.innerHTML = '';

    cartas.forEach(c => {
        const div = document.createElement('div');
        div.className = 'national-card' + (cartasSeleccionadas.includes(c.id) ? ' selected' : '');

        const celda = partidaActual.tablero.find(t => t.municipio_id === c.municipio_id);
        const esTerritorioMio = Boolean(celda && Number(celda.jugador_id) === Number(miJugadorId));

        let html = `
            <div class="card-header-row">
                <span class="card-icon">${escaparHTML(c.emblema_icono)}</span>
                ${c.tipo_carta === 'TERRITORIO' && esTerritorioMio ? '<span class="card-badge-own">PROPIO</span>' : ''}
            </div>
            <div class="card-territory-name">${c.tipo_carta === 'BOMBA' ? escaparHTML(c.emblema_titulo) : escaparHTML(c.municipio_nombre)}</div>
            <div class="card-emblem-name">${c.tipo_carta === 'BOMBA' ? 'Armamento especial' : escaparHTML(c.emblema_titulo)}</div>
        `;
        div.innerHTML = html;

        if (c.tipo_carta === 'TERRITORIO') {
            div.addEventListener('click', () => {
                const i = cartasSeleccionadas.indexOf(c.id);
                if (i >= 0) cartasSeleccionadas.splice(i, 1);
                else if (cartasSeleccionadas.length < 3) cartasSeleccionadas.push(c.id);
                else mostrarToast('Solo podés canjear 3 cartas a la vez.', 'alerta');
                renderizarCartas();
            });
            if (esTerritorioMio && puedeActuar) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-secondary';
                btn.style.cssText = 'width:100%; margin-top:8px; padding:4px 8px; font-size:0.8rem;';
                btn.textContent = '🎖️ Activar beneficio';
                btn.addEventListener('click', (ev) => {
                    ev.stopPropagation();
                    cartaBeneficioId = c.id;
                    const txt = document.getElementById('texto-beneficio-carta');
                    if (txt) txt.innerText = `Elegí el beneficio de ${c.municipio_nombre}:`;
                    abrirModal('modal-beneficio-carta');
                });
                div.appendChild(btn);
            }
        } else if (c.tipo_carta === 'BOMBA' && puedeActuar) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-primary';
            btn.style.cssText = 'width:100%; margin-top:8px; padding:4px 8px; font-size:0.8rem; background:#ef4444; color:#fff;';
            btn.textContent = bombaActivaId === c.id ? '🎯 Elegí el objetivo en el mapa…' : '💣 Lanzar bomba';
            btn.addEventListener('click', () => {
                if (bombaActivaId === c.id) { bombaActivaId = null; }
                else {
                    bombaActivaId = c.id;
                    modoReagrupar = false;
                    municipioOrigenId = null;
                    mostrarToast('💣 Tocá un territorio ENEMIGO para bombardearlo.', 'alerta');
                }
                actualizarHeader();
                actualizarResaltadosMapa();
                renderizarCartas();
            });
            div.appendChild(btn);
        }
        lista.appendChild(div);
    });

    if (btnCanje) btnCanje.classList.toggle('hidden', !(puedeActuar && cartasSeleccionadas.length === 3));
}

document.getElementById('btn-canjear-cartas').addEventListener('click', async () => {
    if (cartasSeleccionadas.length !== 3) return;
    try {
        const res = await fetch(`${API_URL}/canjear-cartas/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({ partida_id: partidaActual.id, cartas_ids: cartasSeleccionadas })
        });
        const data = await res.json();
        if (!res.ok) { mostrarToast(data.error || 'No se pudo canjear.', 'alerta'); return; }
        cartasSeleccionadas = [];
        const extra = (data.bonus_territorios || []).length ? ` (+2 tropas en ${data.bonus_territorios.join(', ')})` : '';
        mostrarToast(`✨ Canje exitoso: +${data.bonus_refuerzos} refuerzos${extra}.`, 'turno');
        await actualizarEstadoPartida(false);
    } catch (err) { console.error('Error al canjear cartas:', err); }
});

async function aplicarBeneficioCarta(beneficio) {
    if (!cartaBeneficioId || !partidaActual) return;
    try {
        const res = await fetch(`${API_URL}/beneficio-carta/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({ partida_id: partidaActual.id, carta_id: cartaBeneficioId, beneficio })
        });
        const data = await res.json();
        cerrarModal('modal-beneficio-carta');
        if (!res.ok) { mostrarToast(data.error || 'No se pudo activar el beneficio.', 'alerta'); return; }
        cartaBeneficioId = null;
        mostrarToast(`🎖️ ${data.mensaje}`, 'turno');
        await actualizarEstadoPartida(false);
    } catch (err) { console.error('Error al aplicar beneficio:', err); }
}

async function lanzarBomba(destinoId) {
    const celda = partidaActual.tablero.find(t => t.municipio_id === destinoId);
    if (!celda) return;
    if (Number(celda.jugador_id) === Number(miJugadorId)) {
        mostrarToast('No podés bombardear tus propios territorios.', 'alerta');
        return;
    }
    try {
        const res = await fetch(`${API_URL}/usar-bomba/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({ partida_id: partidaActual.id, carta_id: bombaActivaId, destino_id: destinoId })
        });
        const data = await res.json();
        if (!res.ok) { mostrarToast(data.error || 'No se pudo lanzar la bomba.', 'alerta'); return; }
        bombaActivaId = null;
        mostrarToast(`💣 ${data.destino}: ${data.bajas} baja(s). Le quedan ${data.tropas_restantes} tropas.`, 'turno');
        await actualizarEstadoPartida(false);
    } catch (err) { console.error('Error al usar bomba:', err); }
}

/* ---------- Avisos de fin de turno ---------- */

function anunciarResultadoTurno(data) {
    const partes = [];
    if (data.evento_carta) partes.push(data.evento_carta);
    if (data.carta_ganada) partes.push(`🃏 Ganaste una carta: ${escaparHTML(data.carta_ganada.municipio_nombre)} ${escaparHTML(data.carta_ganada.emblema_icono)}`);
    if (Array.isArray(data.acciones_ia) && data.acciones_ia.length) {
        partes.push(data.acciones_ia.slice(-4).map(escaparHTML).join('<br>'));
    }
    if (!partes.length) return;
    mostrarToast(partes.join('<br>'), data.evento_carta ? 'alerta' : 'espera');
    const toast = document.getElementById('toast-notificacion');
    if (toast) {
        clearTimeout(toast._timer);
        toast._timer = setTimeout(() => toast.classList.add('hidden'), 7000);
    }
}

/* ---------- Pantallas de victoria / derrota ---------- */

function verificarFinPartida() {
    if (!partidaActual || partidaActual.activa) return;
    const clave = `fin-${partidaActual.id}`;
    if (finPartidaAnunciada === clave || finPartidaAnunciada === `rendido-${partidaActual.id}`) return;
    finPartidaAnunciada = clave;

    const ganador = partidaActual.ganador_nombre;
    const yo = obtenerMiJugador();
    if (ganador && yo && yo.nombre === ganador) {
        const msg = document.getElementById('victoria-mensaje');
        if (msg) msg.innerText = `¡${ganador} conquistó el mapa! ${obtenerFraseAleatoria(CHISTES_VICTORIA)}`;
        abrirModal('modal-victoria');
    } else {
        const msg = document.getElementById('derrotado-mensaje');
        if (msg) msg.innerText = ganador ? `La partida terminó: ganó ${ganador}.` : 'La partida terminó.';
        abrirModal('modal-derrotado');
    }
}

/* ---------- Controles que dependen del estado ---------- */

function actualizarControlesExtra() {
    if (!partidaActual) return;
    const activa = Boolean(partidaActual.activa);
    const esMiTurno = esMiTurnoActual();
    const yo = obtenerMiJugador();
    const sinRefuerzos = Number(partidaActual.jugador_turno_tropas) === 0;

    if (esMiTurno && !sinRefuerzos && modoReagrupar) salirModoReagrupar();

    const btnCodigo = document.getElementById('btn-ver-codigo');
    if (btnCodigo) btnCodigo.classList.toggle('hidden', !activa);

    const btnReag = document.getElementById('btn-modo-reagrupar');
    if (btnReag) {
        const visible = activa && partidaIniciada && esMiTurno && sinRefuerzos;
        btnReag.classList.toggle('hidden', !visible);
        btnReag.innerText = modoReagrupar ? '⚔️ Volver a Atacar' : '🔄 Reagrupar';
        btnReag.style.cssText = modoReagrupar ? 'background:#10b981; color:#052e16; font-weight:800;' : '';
    }

    const btnRendir = document.getElementById('btn-rendirse');
    if (btnRendir) btnRendir.classList.toggle('hidden', !(activa && partidaIniciada && yo && !yo.rendido));

    const btnPasar = document.getElementById('btn-pasar-turno');
    if (btnPasar && yo && yo.rendido) btnPasar.classList.add('hidden');

    const btnCancelar = document.getElementById('btn-cancelar-accion-mapa');
    if (btnCancelar) {
        const haySeleccion = Boolean(municipioOrigenId || bombaActivaId || modoReagrupar);
        btnCancelar.classList.toggle('hidden', !(activa && partidaIniciada && esMiTurno && haySeleccion));
    }

    const indicador = document.getElementById('indicador-fase');
    if (indicador) {
        if (!activa) indicador.innerText = 'Partida finalizada';
        else if (!partidaIniciada) indicador.innerText = 'Sala preparada: esperando el inicio de la batalla';
        else if (!esMiTurno) indicador.innerText = `Turno de ${partidaActual.jugador_turno_nombre}`;
        else if (!sinRefuerzos) indicador.innerText = 'Fase 1: Incorporación de refuerzos';
        else if (modoReagrupar) indicador.innerText = 'Fase 3: Reagrupamiento';
        else indicador.innerText = 'Fase 2: Ataque';
    }
}

/* ---------- Envoltorios de funciones existentes ---------- */

const _actualizarHeaderOriginal = actualizarHeader;
actualizarHeader = function () {
    _actualizarHeaderOriginal.apply(this, arguments);
    actualizarControlesExtra();
    verificarFinPartida();
};

const _renderizarPanelesOriginal = renderizarPanelesLaterales;
renderizarPanelesLaterales = function () {
    _renderizarPanelesOriginal.apply(this, arguments);
    renderizarCartas();
};

const _actualizarResaltadosOriginal = actualizarResaltadosMapa;
actualizarResaltadosMapa = function () {
    _actualizarResaltadosOriginal.apply(this, arguments);
    if (mapaSVG && partidaActual && partidaIniciada && esMiTurnoActual() && bombaActivaId) {
        mapaSVG.limpiarResaltados();
        mapaSVG.resaltarDestinos(enemigosIds(), 'territorio-destino-ataque');
    }
};

const _seleccionarTerritorioOriginal = seleccionarTerritorio;
seleccionarTerritorio = async function (id) {
    if (partidaActual && partidaActual.activa && partidaIniciada && esMiTurnoActual()) {
        if (bombaActivaId) { await lanzarBomba(id); return; }
        if (modoReagrupar && Number(partidaActual.jugador_turno_tropas) === 0) { await manejarClickReagrupar(id); return; }

        // Ataque: el destino debe ser enemigo y limítrofe (el backend delega esta validación al mapa).
        if (municipioOrigenId && municipioOrigenId !== id && Number(partidaActual.jugador_turno_tropas) === 0) {
            const destino = partidaActual.tablero.find(t => t.municipio_id === id);
            if (destino && Number(destino.jugador_id) === Number(miJugadorId)) {
                mostrarToast('No podés atacar tus propios territorios.', 'alerta');
                return;
            }
            if (destino && !sonLimitrofes(municipioOrigenId, id)) {
                mostrarToast('El municipio seleccionado no es limítrofe.', 'alerta');
                return;
            }
        }
    }
    return _seleccionarTerritorioOriginal.apply(this, arguments);
};
