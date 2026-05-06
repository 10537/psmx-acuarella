import zeep
from zeep import xsd

client = zeep.Client('https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl')

item = xsd.AnyObject(xsd.String(), '50014500044')

request_data = {
    'id_rotulo': '55',
    'codigos_remisiones': {'_value_1': [item]},
    'usuario': 'marlonfuenmayor.ws',
    'clave': 'd69a4d797f20c627be9498d811b9a115a7e17f0f5dd000f3cfdf2d7b56504341'
}

try:
    response = client.service.Guias_imprimirRotulos(p=request_data)
    print(f"SUCCESS!")
    print(response)
except Exception as e:
    print(f"ERROR: {e}")

