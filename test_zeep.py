import zeep
client = zeep.Client('https://ws.coordinadora.com/ags/1.5/server.php?wsdl')

def test_quote():
    request_data = {
        'nit': '700326479',
        'div': '01',
        'cuenta': 2,
        'producto': 0,
        'origen': '11001000',
        'destino': '11001000',
        'valoracion': 178500,
        'nivel_servicio': [1],
        'detalle': {'item': [{'ubl': 0, 'alto': 10.0, 'ancho': 10.0, 'largo': 10.0, 'peso': 1.0, 'unidades': 1}]},
        'apikey': '77f0f570-7398-4691-ae82-714214b27d3c',
        'clave': 'vQ8vZ7kL7sP2aA8x'
    }
    try:
        response = client.service.Cotizador_cotizar(p=request_data)
        print(f"SUCCESS Flete={getattr(response, 'flete_total', '?')}")
    except Exception as e:
        print(f"ERROR {e}")

test_quote()
