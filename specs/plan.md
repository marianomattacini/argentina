# PLAN DE ARQUITECTURA TÉCNICA (plan.md)
**Proyecto:** TEG Argentina - Juego de Estrategia Territorial y Trivia  
**Estado:** Propuesto para Revisión del Arquitecto  
**Metodología:** Spec-Driven Development (SDD)

---

## 1. STACK TÉCNICO Y ARQUITECTURA

- **Backend:** Python (Django + Django REST Framework / Channels para tiempo real).
- **Base de Datos:** PostgreSQL (o SQLite para desarrollo local).
- **Frontend:** HTML5, CSS3 (Tailwind CSS / Vanilla), JavaScript (JS ES6+ / Fetch API & WebSockets).
- **Arquitectura:** Modelo Cliente-Servidor con API REST para la lógica de negocio persistente y WebSockets para la actualización en tiempo real del tablero entre los 2 a 10 jugadores.

---

## 2. MODELADO DE DATOS (ESQUEMA ENTIDAD-RELACIÓN)

### 2.1 Tablas Principales (Producción)

1. **`Provincias`** (Regiones continentales)
   - `id` (PK)
   - `nombre` (varchar)
   - `bonus_ejercitos` (integer) - Fichas extra por controlar la provincia completa.

2. **`Municipios`** (Territorios de combate)
   - `id` (PK)
   - `provincia_id` (FK -> Provincias)
   - `nombre` (varchar)
   - `codigo_referencia` (varchar) - Identificador único de mapa (ej. "MND-MAIPU").

3. **`Municipios_Limites`** (Grafo de contigüidad geográfica)
   - `municipio_origen_id` (FK -> Municipios)
   - `municipio_destino_id` (FK -> Municipios)

4. **`Partidas`**
   - `id` (PK)
   - `codigo_sala` (varchar, unique)
   - `estado` (enum: 'ESPERA', 'EN_PROGRESO', 'FINALIZADA')
   - `turno_jugador_id` (FK -> Jugadores)
   - `fase_actual` (enum: 'INCORPORACION', 'ATAQUE', 'REAGRUPACION')
   - `creado_en` (timestamp)

5. **`Jugadores`**
   - `id` (PK)
   - `partida_id` (FK -> Partidas)
   - `nombre_usuario` (varchar)
   - `color` (varchar)
   - `objetivo_secreto` (text)
   - `es_turn_active` (boolean)

6. **`Estado_Tablero`** (Ubicación actual de tropas por partida)
   - `id` (PK)
   - `partida_id` (FK -> Partidas)
   - `municipio_id` (FK -> Municipios)
   - `jugador_id` (FK -> Jugadores)
   - `cantidad_tropas` (integer)

7. **`Trivias`** (Banco de preguntas)
   - `id` (PK)
   - `categoria` (varchar) - Ej: "Geografía", "Historia", "Cultura"
   - `campo_info` (text) - Contexto de la pregunta.
   - `campo_gateway` (text) - Pregunta de diagnóstico/trivia.
   - `campo_accion` (text) - Respuesta correcta y explicación.
   - `opciones_json` (JSON) - Opciones A, B, C, D.

### 2.2 Tabla Temporal (Aprobaciones/Propuestas de Operadores/Jugadores)

8. **`Trivias_Temporales`** (Propuestas de preguntas por parte de la comunidad)
   - `id` (PK)
   - `autor_usuario` (varchar)
   - `campo_info` (text)
   - `campo_gateway` (text)
   - `campo_accion` (text)
   - `estado` (enum: 'PENDIENTE', 'APROBADO', 'RECHAZADO') - Default: 'PENDIENTE'
   - `creado_en` (timestamp)

---

## 3. CONTRATOS DE API (ENDPOINTS)

### 3.1 Gestión de Partida y Tablero
- `POST /api/partidas/crear/`  
  - **Body:** `{ "nombre_jugador": "Mariano", "max_jugadores": 6 }`  
  - **Respuesta:** `{ "partida_id": 1, "codigo_sala": "ARG123", "jugador_id": 1 }`

- `GET /api/partidas/{codigo_sala}/estado/`  
  - **Respuesta:** JSON con el mapa completo, ocupación de cada municipio, ejércitos por jugador y turno activo.

- `POST /api/partidas/{id}/atacar/`  
  - **Body:** `{ "origen_id": 12, "destino_id": 15, "cantidad_dados": 3 }`  
  - **Respuesta:** `{ "resultado_atacante": [6, 4, 1], "resultado_defensor": [5, 5], "bajas_atacante": 1, "bajas_defensor": 1, "conquistado": false }`

### 3.2 Sistema de Trivias
- `GET /api/trivias/aleatoria/`  
  - **Respuesta:** Retorna una pregunta activa con `campo_info` y `campo_gateway`.

- `POST /api/trivias/proponer/` (Tabla Temporal)  
  - **Body:** `{ "autor": "Mariano", "campo_info": "Geografía Mendoza", "campo_gateway": "¿Cuál es la capital?", "campo_accion": "Mendoza Capital" }`  
  - **Respuesta:** `{ "status": "Propuesta enviada", "estado": "PENDIENTE" }`

- `PUT /api/trivias/admin/aprobar/{id}/` (Solo Administrador)  
  - **Body:** `{ "accion": "APROBAR" }` (Transfiere el registro de `Trivias_Temporales` a `Trivias`).

---

## 4. ESTRUCTURA DE ARCHIVOS DEL PROYECTO

```text
Argentina/
├── specs/
│   ├── spec.md
│   └── plan.md
├── backend/             # Proyecto Django
│   ├── manage.py
│   ├── teg_argentina/   # Configuración global
│   └── juego/           # App principal (Models, Views, Endpoints, Sockets)
└── frontend/            # Interfaz visual
    ├── index.html
    ├── css/
    └── js/
