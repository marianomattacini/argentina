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
            abrirModal('modal-sala-creada');
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
        mostrarToast('No se pudo conectar con el servidor para iniciar la partida.', 'alerta');
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

function mostrarOpcionesAtaque(dataAtaque) {
    document.getElementById('trivia-categoria').innerText = `Combate: ${dataAtaque.origen} vs ${dataAtaque.destino}`;
    document.getElementById('trivia-pregunta').innerText = 'Elegí la modalidad de combate:';
    const contenedorOpciones = document.getElementById('trivia-opciones');
    contenedorOpciones.innerHTML = `
        <button class="opcion-btn" style="background:#38bdf8; color:#090d16; font-weight:bold;" onclick="ejecutarCombateDirecto()">
            Ataque Directo por Dados
        </button>
    `;
    abrirModal('modal-trivia');
}

async function ejecutarCombateDirecto() {
    try {
        const res = await fetch(`${API_URL}/resolver-combate/`, {
            method: 'POST',
            headers: headersConAuth(),
            body: JSON.stringify({
                partida_id: partidaActual.id,
                origen_id: municipioOrigenId,
                destino_id: municipioDestinoId,
                modalidad: 'DADOS',
                opcion_id: null
            })
        });
        const r = await res.json();
        cerrarModal('modal-trivia');
        const gano = r.resultado === 'victoria';
        mostrarModalResultado(
            gano ? '🏆 ¡Ganaste la Tirada!' : '💀 ¡Perdiste la Tirada!',
            `<strong>Tu Dado:</strong> ${r.dado_ataque} vs <strong>Defensa:</strong> ${r.dado_defensa}`,
            gano ? obtenerFraseAleatoria(CHISTES_VICTORIA) : obtenerFraseAleatoria(CHISTES_DERROTA)
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