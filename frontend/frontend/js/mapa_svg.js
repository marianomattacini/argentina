/**
 * Renderizador Cartográfico Oficial (Nacional + Islas Malvinas y Provincial)
 */

class MapaArgentinaSVG {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.onTerritorioClick = options.onTerritorioClick || function(){};
    }

    cargarMapa(estadoTablero = [], provinciaSeleccionada = 'Mendoza') {
        this.container.innerHTML = '';

        const esNacional = estadoTablero.some(
            item => item.provincia_nombre && item.municipio_nombre === item.provincia_nombre
        );

        let features = [];
        if (esNacional && typeof GEOJSON_NACIONAL !== 'undefined') {
            features = GEOJSON_NACIONAL.features;
        } else if (!esNacional && typeof GEOJSON_DEPARTAMENTOS !== 'undefined') {
            features = GEOJSON_DEPARTAMENTOS[provinciaSeleccionada] || GEOJSON_DEPARTAMENTOS['Mendoza'] || [];
        }

        if (!features.length) {
            this.container.innerHTML = `<div style="color:#f38ba8; text-align:center; padding:40px;">No se encontraron datos cartográficos.</div>`;
            return;
        }

        this.renderizarGeoJSON({ type: "FeatureCollection", features }, estadoTablero, esNacional);
    }

    renderizarGeoJSON(featureCollection, tablero, esNacional) {
        const width = 650;
        const height = esNacional ? 920 : 780;

        const svg = d3.select(`#${this.container.id}`)
            .append('svg')
            .attr('viewBox', `0 0 ${width} ${height}`)
            .attr('class', 'mapa-argentina-svg');

        svg.append('rect')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('fill', '#0f111a')
            .attr('rx', 14);

        const projection = d3.geoIdentity()
            .reflectY(true)
            .fitExtent([[35, 35], [width - 35, height - 35]], featureCollection);

        const pathGenerator = d3.geoPath().projection(projection);

        const dicTablero = {};
        tablero.forEach(item => {
            dicTablero[item.municipio_nombre.toLowerCase().trim()] = item;
        });

        const capaTerritorios = svg.append('g').attr('class', 'capa-territorios');

        featureCollection.features.forEach((feature) => {
            const props = feature.properties || {};
            const nombreGeo = (props.nombre || '').toLowerCase().trim();

            let itemTablero = dicTablero[nombreGeo] || null;
            if (!itemTablero) {
                for (let k in dicTablero) {
                    if (nombreGeo.includes(k) || k.includes(nombreGeo)) {
                        itemTablero = dicTablero[k];
                        break;
                    }
                }
            }

            const colorHex = itemTablero ? this.obtenerHexColor(itemTablero.jugador_color) : '#2a2d3d';
            const territorioId = itemTablero ? itemTablero.municipio_id : null;

            const manejarClick = (event) => {
                if (event && event.stopPropagation) event.stopPropagation();
                if (territorioId) this.onTerritorioClick(territorioId);
            };

            const g = capaTerritorios.append('g')
                .attr('class', 'territorio-group')
                .attr('data-id', territorioId)
                .style('cursor', territorioId ? 'pointer' : 'default')
                .on('click', manejarClick);

            g.append('title').text(`${props.nombre}${itemTablero ? ` — ${itemTablero.jugador_nombre} (${itemTablero.tropas} tropas)` : ''}`);

            g.append('path')
                .attr('id', territorioId ? `path-${territorioId}` : null)
                .attr('class', 'territorio-path')
                .attr('d', pathGenerator(feature))
                .attr('fill', colorHex)
                .attr('stroke', '#0f111a')
                .attr('stroke-width', 1.2)
                .attr('stroke-linejoin', 'round')
                .on('click', manejarClick);

            const centroide = pathGenerator.centroid(feature);

            if (itemTablero && !isNaN(centroide[0]) && !isNaN(centroide[1])) {
                const badge = g.append('g')
                    .attr('class', 'badge-tropas')
                    .style('pointer-events', 'none')
                    .attr('transform', `translate(${centroide[0]}, ${centroide[1]})`);

                badge.append('circle')
                    .attr('r', esNacional ? 10 : 12)
                    .attr('fill', '#0f111a')
                    .attr('stroke', colorHex)
                    .attr('stroke-width', 2);

                badge.append('text')
                    .attr('y', 3.5)
                    .attr('text-anchor', 'middle')
                    .attr('fill', '#f8fafc')
                    .attr('font-size', esNacional ? '9px' : '10px')
                    .attr('font-weight', 'bold')
                    .text(itemTablero.tropas);
            }
        });
    }

    resaltarOrigen(id) {
        this.limpiarResaltados();
        const path = document.querySelector(`#path-${id}`);
        if (path) path.classList.add('territorio-origen');
    }

    resaltarDestinos(ids = [], clase = 'territorio-destino-ataque') {
        ids.forEach(id => {
            const path = document.querySelector(`#path-${id}`);
            if (path) path.classList.add(clase);
        });
    }

    resaltarReforzables(ids = []) {
        this.limpiarResaltados();
        ids.forEach(id => {
            const path = document.querySelector(`#path-${id}`);
            if (path) path.classList.add('territorio-reforzable');
        });
    }

    limpiarResaltados() {
        document.querySelectorAll('.territorio-origen, .territorio-destino-ataque, .territorio-destino-reagrupe, .territorio-reforzable')
            .forEach(el => el.classList.remove('territorio-origen', 'territorio-destino-ataque', 'territorio-destino-reagrupe', 'territorio-reforzable'));
    }

    obtenerHexColor(color) {
        const c = {
            'Rojo': '#f38ba8',
            'Azul': '#89b4fa',
            'Verde': '#a6e3a1',
            'Amarillo': '#f9e2af',
            'Violeta': '#cba6f7',
            'Naranja': '#fab387'
        };
        return c[color] || '#89dceb';
    }
}