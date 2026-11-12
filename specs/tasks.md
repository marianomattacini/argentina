# LISTADO DE TAREAS ATÓMICAS (tasks.md)
**Proyecto:** TEG Argentina - Juego de Estrategia Territorial y Trivia  
**Estado:** Pendiente de Ejecución  
**Metodología:** Spec-Driven Development (SDD)

---

## MÓDULO 1: Configuración Inicial del Proyecto y Entorno
- [ ] **Task 1.1:** Crear la estructura de directorios del proyecto (`backend/` y `frontend/`) e inicializar el entorno virtual de Python en `backend/`.
- [ ] **Task 1.2:** Instalar dependencias base en el entorno virtual (`django`, `djangorestframework`, `django-cors-headers`) y generar el proyecto Django `teg_argentina` con la app `juego`.
- [ ] **Task 1.3:** Configurar `settings.py` de Django (Apps instaladas, CORS, middleware) y verificar que el servidor inicie correctamente.

---

## MÓDULO 2: Persistencia y Modelado de Datos (Base de Datos)
- [ ] **Task 2.1:** Definir el modelo `Provincia` en `juego/models.py` (id, nombre, bonus_ejercitos) y generar migraciones.
- [ ] **Task 2.2:** Definir el modelo `Municipio` en `juego/models.py` (id, provincia_id, nombre, codigo_referencia) y su relación con `Provincia`.
- [ ] **Task 2.3:** Definir el modelo de autox-referencia `MunicipioLimite` para representar el grafo de contigüidad geográfica de Argentina.
- [ ] **Task 2.4:** Definir los modelos de la partida: `Partida`, `Jugador` y `EstadoTablero` (ubicación y cantidad de tropas).
- [ ] **Task 2.5:** Definir los modelos de trivias: `Trivia` (producción) y `TriviaTemporal` (propuestas con estado PENDIENTE, APROBADO, RECHAZADO).
- [ ] **Task 2.6:** Crear y ejecutar un script `seed_geografia.py` para cargar las provincias, municipios de Argentina y sus conexiones límites básicas.
- [ ] **Task 2.7:** Crear y ejecutar un script `seed_trivias.py` para cargar un banco inicial de preguntas de geografía e historia argentina.

---

## MÓDULO 3: Backend - APIs REST (Lógica de Negocio)
- [ ] **Task 3.1:** Crear los Serializers REST para los modelos `Provincia`, `Municipio`, `Partida` y `EstadoTablero`.
- [ ] **Task 3.2:** Crear el endpoint `POST /api/partidas/crear/` para inicializar una nueva sala, asignar color e incorporar al primer jugador.
- [ ] **Task 3.3:** Crear el endpoint `GET /api/partidas/{codigo_sala}/estado/` que devuelva la distribución de tropas, turnos y municipios de la partida activa.
- [ ] **Task 3.4:** Crear el endpoint `POST /api/partidas/{id}/atacar/` que valide límites entre municipios, ejecute la tirada de dados (hasta 3 atacante vs 3 defensor) y devuelva las bajas y conquista.
- [ ] **Task 3.5:** Crear el endpoint `GET /api/trivias/aleatoria/` para consultar preguntas de trivia durante la partida.
- [ ] **Task 3.6:** Crear el endpoint `POST /api/trivias/proponer/` para enviar propuestas de trivias a la tabla temporal.
- [ ] **Task 3.7:** Crear el endpoint `PUT /api/trivias/admin/aprobar/{id}/` (protegido) para la aprobación o rechazo de trivias por parte del administrador.

---

## MÓDULO 4: Frontend - Interfaz Visual e Interacción
- [ ] **Task 4.1:** Crear la estructura base del Frontend (`index.html`, `css/styles.css`, `js/app.js`) con interfaz visual del tablero (layout del mapa de Argentina).
- [ ] **Task 4.2:** Diseñar el panel de control lateral: estado del jugador, fase del turno actual (Incorporación, Ataque, Reagrupamiento) y conteo de ejércitos.
- [ ] **Task 4.3:** Implementar en `js/api.js` la comunicación con el Backend (`fetch` a los endpoints de crear partida y consultar estado).
- [ ] **Task 4.4:** Conectar la selección interactiva de municipios origen/destino en el mapa con la llamada al endpoint de ataque `POST /api/partidas/{id}/atacar/`.
- [ ] **Task 4.5:** Diseñar el modal de Trivia de Argentina (visualización de pregunta, opciones de respuesta y mensaje de feedback con ejércitos ganados).
- [ ] **Task 4.6:** Diseñar el panel de administración de Trivias para listar, aprobar o rechazar preguntas temporales.

---

## MÓDULO 5: Integración, Pruebas y Sad Paths
- [ ] **Task 5.1:** Validar las reglas de Sad Path: bloqueo de ataques no contiguos y municipios con 1 sola tropa.
- [ ] **Task 5.2:** Realizar prueba de integración de punta a punta (Happy Path completo: desde creación de sala hasta victoria/conquista).