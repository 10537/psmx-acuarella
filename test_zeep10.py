import zeep
from lxml import etree
from zeep import plugins

class PrintPlugin(plugins.HistoryPlugin):
    def egress(self, envelope, http_headers, operation, binding_options):
        print(etree.tostring(envelope, pretty_print=True).decode('utf-8'))
        return envelope, http_headers

client = zeep.Client('https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl', plugins=[PrintPlugin()])

item = etree.Element("item")
item.text = "50014500044"

request_data = {
    'id_rotulo': '55',
    'codigos_remisiones': {'_value_1': [item]},
    'usuario': 'marlonfuenmayor.ws',
    'clave': 'd69a4d797f20c627be9498d811b9a115a7e17f0f5dd000f3cfdf2d7b56504341'
}

try:
    response = client.service.Guias_imprimirRotulos(p=request_data)
    print("SUCCESS")
    print(response)
except Exception as e:
    print(f"ERROR: {e}")

