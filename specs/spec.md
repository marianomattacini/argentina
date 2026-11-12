# ESPECIFICACIÓN FUNCIONAL DE PRODUCTO (spec.md)
**Proyecto:** TEG Argentina - Juego de Estrategia Territorial y Trivia  
**Estado:** Aprobado  
**Metodología:** Spec-Driven Development (SDD)

---

## 1. Visión del Producto
Desarrollar un juego de estrategia por turnos estilo T.E.G. ambientado en la Argentina, soportando de 2 a 10 jugadores simultáneos. El mapa interactivo estará compuesto por Provincias (regiones principales) y Municipios/Departamentos (territorios de combate). El juego integra una mecánica opcional/asociada de Trivia Argentina para la obtención de bonificaciones de ejércitos.

---

## 2. REGLAS DE NEGOCIO Y MECÁNICAS DE JUEGO

### 2.1 Jugadores y Configuración
- **Capacidad:** De 2 a 10 jugadores.
- **Asignación:** Cada jugador selecciona o se le asigna un color representativo.
- **Repartición Inicial:** Los municipios del país se distribuyen de manera equitativa y aleatoria al inicio de la partida. Se asignan ejércitos iniciales a cada jugador.

### 2.2 Fases por Turno
Cada turno de un jugador consta de 3 fases consecutivas obligatorias:
1. **Fase de Incorporación:** Recepción y colocación de ejércitos calculados según la cantidad de territorios y provincias completas bajo su dominio.
2. **Fase de Ataque:** Combate por simulación de dados entre municipios propios y limítrofes enemigos.
   - Atacante: MÁX 3 dados (requiere al menos N+1 ejércitos en el municipio origen).
   - Defensor: MÁX 3 dados.
   - Resolución: Comparación de dados individuales de mayor a menor. Empates favorecen al defensor.
3. **Fase de Reagrupamiento / Maniobra:** Traslado de fichas entre municipios contiguos bajo control del mismo jugador.

### 2.3 Mecánica de Trivia (Bonificación)
- Al conquistar al menos 1 municipio durante el turno o resolver hitos específicos, el jugador puede responder una tarjeta de trivia histórica/geográfica. 
- La respuesta correcta otorga ejércitos de bonificación para el siguiente turno.

### 2.4 Condiciones de Victoria
- **Objetivo Secreto:** Cumplimiento del objetivo asignado aleatoriamente al inicio de la partida.
- **Dominación Total:** Conquista del 100% de los municipios de la República Argentina.

---

## 3. FLUJOS DE USUARIO

### 3.1 Happy Path (Camino Exitoso)
1. Los jugadores se registran/incorporan a la sala de juego (2 a 10 personas).
2. El sistema distribuye municipios y asigna objetivos secretos.
3. Inicia el Turno 1 con la Fase de Incorporación.
4. El jugador activo selecciona municipio origen, municipio destino limítrofe y lanza dados de ataque.
5. Si el defensor se queda sin fichas, el atacante conquista el municipio y transfiere tropas.
6. El jugador activa la Trivia opcional, responde correctamente y gana fichas extra.
7. El jugador realiza su reagrupamiento y pasa el turno al siguiente jugador.
8. Un jugador cumple su condición de victoria → El sistema detiene la partida, muestra el tablero final y proclama al ganador.

### 3.2 Sad Path (Caminos de Error y Contingencias)
1. **Intento de ataque no válido (Territorio no contiguo):**  
   * *Respuesta:* El sistema bloquea el lanzamiento de dados y muestra una alerta: "El municipio seleccionado no es limítrofe".
2. **Intento de ataque con 1 sola tropa:**  
   * *Respuesta:* El sistema deshabilita el botón de ataque indicando: "Necesitas al menos 2 ejércitos para iniciar un ataque desde este municipio".
3. **Desconexión / Salida de un jugador durante el turno:**  
   * *Respuesta:* El sistema congela el temporizador del turno durante 30 segundos; si no reconecta, pasa el control del ejército a un estado "Neutral / Neutralizado" o automatizado (IA pasiva).
4. **Respuesta incorrecta en la Trivia:**  
   * *Respuesta:* El sistema registra el fallo sin penalización de territorios, finaliza el turno sin otorgar fichas extra y muestra la respuesta correcta.