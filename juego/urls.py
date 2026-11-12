from django.urls import path
from .views import (
    CrearPartidaAPIView,
    UnirsePartidaAPIView,
    EstadoPartidaAPIView,
    ReforzarTerritorioAPIView,
    MoverTropasAPIView,
    CanjearCartasAPIView,
    PrepararAtaqueAPIView,
    ResolverCombateAPIView,
    PasarTurnoAPIView,
    UsarBombaAPIView,
    ElegirBeneficioCartaAPIView,
    RendirseAPIView,
)

urlpatterns = [
    path('partidas/', CrearPartidaAPIView.as_view(), name='crear-partida'),
    path('partidas/unirse/', UnirsePartidaAPIView.as_view(), name='unirse-partida'),
    path('partidas/<str:codigo_sala>/', EstadoPartidaAPIView.as_view(), name='estado-partida'),
    path('reforzar/', ReforzarTerritorioAPIView.as_view(), name='reforzar-territorio'),
    path('mover-tropas/', MoverTropasAPIView.as_view(), name='mover-tropas'),
    path('canjear-cartas/', CanjearCartasAPIView.as_view(), name='canjear-cartas'),
    path('preparar-ataque/', PrepararAtaqueAPIView.as_view(), name='preparar-ataque'),
    path('resolver-combate/', ResolverCombateAPIView.as_view(), name='resolver-combate'),
    path('pasar-turno/<int:partida_id>/', PasarTurnoAPIView.as_view(), name='pasar-turno'),
    path('usar-bomba/', UsarBombaAPIView.as_view(), name='usar-bomba'),
    path('beneficio-carta/', ElegirBeneficioCartaAPIView.as_view(), name='beneficio-carta'),
    path('rendirse/', RendirseAPIView.as_view(), name='rendirse'),
]