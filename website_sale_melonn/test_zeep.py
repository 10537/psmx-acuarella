from zeep import Client
client = Client('https://sandbox.coordinadora.com/agw/ws/guias/1.6/server.php?wsdl')
for service in client.wsdl.services.values():
    for port in service.ports.values():
        operations = port.binding._operations.values()
        for operation in operations:
            print(operation.name)
