#!/usr/bin/env python3
"""PMT Planer (web) — lokalny serwer do testów. Własny, bo wbudowany `http.server` na Windows bierze typy plików z rejestru systemu
i potrafi podać .js jako text/plain, a wtedy przeglądarka odmawia uruchomienia modułów. Użycie: python serwer_lokalny.py [port]"""
import http.server, socketserver, sys, os, socket, json

TYPY = {'.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
        '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.wasm': 'application/wasm', '.zip': 'application/zip',
        '.whl': 'application/zip', '.webmanifest': 'application/manifest+json', '.woff2': 'font/woff2', '.ttf': 'font/ttf',
        '.png': 'image/png', '.webp': 'image/webp', '.py': 'text/plain; charset=utf-8', '.txt': 'text/plain; charset=utf-8'}

def adres_w_sieci():
    """Adres IP tego komputera w sieci lokalnej (do kodu QR dla telefonu); pusty, gdy go nie ma. Nic nie jest wysyłane — gniazdo UDP tylko „wybiera” interfejs."""
    ip = ''
    try:
        g = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); g.connect(('10.255.255.255', 1)); ip = g.getsockname()[0]; g.close()
    except Exception:
        try: ip = socket.gethostbyname(socket.gethostname())
        except Exception: ip = ''
    return '' if (not ip or ip.startswith('127.') or ip.startswith('169.254.')) else ip

class Obsluga(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split('?')[0] == '/__adres.json':          # aplikacja pyta o adres komputera, żeby od razu pokazać kod QR
            ip = adres_w_sieci(); port = self.server.server_address[1]
            cialo = json.dumps({'adres': ('http://%s:%d/index.html' % (ip, port)) if ip else ''}).encode('utf-8')
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(cialo))); self.end_headers(); self.wfile.write(cialo); return
        return super().do_GET()
    def list_directory(self, path):
        self.send_error(404, 'Brak pliku')          # bez podglądu zawartości folderów (testy, dystrybucja, vendor…)
        return None
    def guess_type(self, path):
        return TYPY.get(os.path.splitext(path)[1].lower()) or super().guess_type(path)
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')          # w testach zawsze świeże pliki
        super().end_headers()
    def log_message(self, fmt, *a):
        if '404' in (fmt % a): sys.stderr.write('  brak pliku: %s\n' % self.path)

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8080
    tylko_ten = 'lokalnie' in sys.argv[1:]          # python serwer_lokalny.py 8080 lokalnie — nikt inny z sieci nie dosięgnie strony (sekret.txt i menedzer.txt leżą obok)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1' if tylko_ten else '0.0.0.0', port), Obsluga) as s:
        print('PMT Planer: http://localhost:%d/index.html   (Ctrl+C kończy)' % port)
        if tylko_ten: print('Tryb „lokalnie”: strona dostępna tylko na tym komputerze (telefon się nie połączy).')
        else: print('Na telefonie w tej samej sieci Wi-Fi: http://<adres tego komputera>:%d/index.html   (każdy w tej sieci widzi też sekret.txt i menedzer.txt; bez telefonu: dodaj słowo „lokalnie”)' % port)
        try: s.serve_forever()
        except KeyboardInterrupt: print('\nKoniec.')
