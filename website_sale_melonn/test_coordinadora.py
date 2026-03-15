import zeep
import logging
import sys

logging.basicConfig(level=logging.DEBUG)
logging.getLogger('zeep.transports').setLevel(logging.DEBUG)

client = zeep.Client('https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl')

# 1. Test Guias_generarGuia
request_data = {
    'codigo_remision': 'TEST-0001',
    'fecha': '2026-03-15',
    'id_cliente': 50846,
    'id_remitente': 0, # Depending on doc
    'nit_remitente': '700326479',
    'nombre_remitente': 'Prueba',
    'direccion_remitente': 'Cll 123',
    'telefono_remitente': '1234567',
    'ciudad_remitente': '11001000', # Bogota
    'nit_destinatario': '123456789',
    'nombre_destinatario': 'Test User',
    'direccion_destinatario': 'Cll 321',
    'telefono_destinatario': '7654321',
    'codigo_ciudad_destino': '11001000',
    'valor_declarado': 100000.0,
    'codigo_cuenta': 1,
    'codigo_producto': 0,
    'nivel_servicio': 1,
    'contenido': 'Test',
    'referencia': 'Test Ref',
    'observaciones': 'Test Obs',
    'detalle_envio': [
        {
            'peso': 1.0,
            'alto': 10,
            'ancho': 10,
            'largo': 10,
            'unidades': 1,
            'referencia': 'A'
        }
    ]
}

try:
    response = client.service.Guias_generarGuia(
        id_cliente=50846, 
        usuario='marlonfuenmayor.ws',
        clave='Mjb!41s',
        # Needs exactly matching the required params from the doc
    )
except Exception as e:
    print(e)
