import zeep
client = zeep.Client('https://ws.coordinadora.com/ags/1.5/server.php?wsdl')

# Convert the provided JSON structure to the dictionary expected by Zeep for the SOAP call
request_data = {
    'nit': '901744069',
    'div': '01',
    'cuenta': 2,
    'producto': 0,
    'origen': '11001000',
    'destino': '11001000',
    'valoracion': 150000,
    'nivel_servicio': [1],
    'detalle': {'item': [{
        'ubl': 1,
        'alto': 10,
        'ancho': 10,
        'largo': 10,
        'peso': 20,
        'unidades': 1
    }]},
    'apikey': '62f4603c-2ef1-4e94-8e28-aacb943cb3d8',
    'clave': 'vV5gA9tV8fS6tK3s'
}

try:
    response = client.service.Cotizador_cotizar(p=request_data)
    print(f"SUCCESS [ubl=1]! Flete Total: {getattr(response, 'flete_total', '?')}")
except Exception as e:
    print(f"ERROR: {e}")

