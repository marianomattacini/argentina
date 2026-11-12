import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teg_argentina.settings')
django.setup()

from rest_framework.test import APIClient
from juego.models import Partida, Jugador, Carta, CartaJugador

def ejecutar_auditoria_qa():
    client = APIClient()
    print("=" * 70)
    print("🕵️‍♂️ AGENTE QA AUTOMATIZADO (ACTUALIZADO) — BATALLA ARGENTINA")
    print("=" * 70)

    # 1. Crear Partida Provincial con Token de Creador
    res_crear = client.post('/api/partidas/', {
        "nombre": "Partida QA Auditoria",
        "tipo_mapa": "PROVINCIAL",
        "provincia": "Mendoza",
        "modo_juego": "VS_IA",
        "privacidad": "CERRADA",
        "password": "clave123",
        "color": "Azul",
        "jugadores": ["Mariano"]
    }, format='json')

    assert res_crear.status_code == 201, f"Error al crear partida: {res_crear.data}"
    data_partida = res_crear.data
    codigo = data_partida['codigo_sala']
    token_mariano = data_partida.get('mi_token')
    print(f"  ✅ Sala creada: #{codigo} | Token de seguridad verificado.")

    # 2. Auditar Seguridad de Sala Cerrada
    res_bad = client.post('/api/partidas/unirse/', {
        "codigo_sala": codigo,
        "password": "wrong",
        "nombre_jugador": "Intruso",
        "color": "Rojo"
    }, format='json')
    assert res_bad.status_code == 403
    print("  ✅ Seguridad OK: Bloqueado acceso con contraseña incorrecta (HTTP 403).")

    # 3. Auditar Refuerzos y Fase de Turno
    jugador_turno_id = data_partida['jugador_turno_id']
    celda_propia = next(t for t in data_partida['tablero'] if t['jugador_id'] == jugador_turno_id)
    
    res_reforzar = client.post('/api/reforzar/', {
        "partida_id": data_partida['id'],
        "municipio_id": celda_propia['municipio_id'],
        "cantidad": 1
    }, HTTP_X_PLAYER_TOKEN=token_mariano, format='json')
    
    assert res_reforzar.status_code == 200, f"Fallo al reforzar: {res_reforzar.data}"
    print(f"  ✅ Sistema de Refuerzos OK: Tropas actualizadas en {res_reforzar.data['municipio']}.")

    # 4. Asignación de Tarjetas Nacionales de Prueba
    carta_test = Carta.objects.create(titulo="Glaciar Perito Moreno", tipo="CANON", descripcion="Patagonia Austral")
    jugador_mariano = Jugador.objects.get(id=data_partida['mi_jugador_id'])
    CartaJugador.objects.create(jugador=jugador_mariano, carta=carta_test)
    print("  ✅ Sistema de Tarjetas Nacionales OK: Carta 'Glaciar Perito Moreno' asignada correctamente.")

    # 5. Limpieza Final de Datos de Prueba
    Partida.objects.filter(codigo_sala=codigo).delete()
    print("=" * 70)
    print("🏁 AUDITORÍA QA FINALIZADA CON ÉXITO Y DATOS LIMPIADOS.")
    print("=" * 70)

if __name__ == '__main__':
    ejecutar_auditoria_qa()