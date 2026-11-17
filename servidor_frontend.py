# -*- coding: utf-8 -*-
"""Servidor del frontend SIN cache (para que el navegador siempre cargue la ultima version).
Uso: python servidor_frontend.py <puerto> <carpeta>"""
import functools
import http.server
import sys

puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 5500
carpeta = sys.argv[2] if len(sys.argv) > 2 else '.'


class SinCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()


handler = functools.partial(SinCache, directory=carpeta)
http.server.ThreadingHTTPServer(('127.0.0.1', puerto), handler).serve_forever()
