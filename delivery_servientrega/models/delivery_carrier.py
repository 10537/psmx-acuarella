from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import requests
import base64
import json
import urllib3
import re

_logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("servientrega", "Servientrega")],
        ondelete={"servientrega": "set default"},
    )

    servientrega_mode = fields.Selection(
        [("qa", "Pruebas (QA)"), ("prod", "Producción")],
        default="qa",
        string="Modo Servientrega"
    )

    servientrega_url_guias = fields.Char(
        string="URL Guías",
        default="https://developer.servientrega.com/WsSisclinetGeneraGuias/GeneracionGuias.asmx"
    )
    servientrega_url_auth = fields.Char(
        string="URL Autenticación",
        default="https://web.servientrega.com:19080/cotizadorcorporativo/api/autenticacion/login"
    )
    servientrega_url_cotizador = fields.Char(
        string="URL Cotizador",
        default="https://web.servientrega.com:19080/CotizadorCorporativo/api/Cotizacion"
    )

    servientrega_user = fields.Char(string="Usuario Servientrega")
    servientrega_password = fields.Char(string="Contraseña Servientrega")
    servientrega_cod_facturacion = fields.Char(string="Código Facturación")
    servientrega_nombre_cargue = fields.Char(string="Nombre Cargue", default="PruebaOdoo")

    servientrega_id_producto = fields.Selection(
        [("2", "Mercancía Premier"), ("6", "Mercancía Industrial")],
        default="2",
        string="Producto Servientrega"
    )

    servientrega_token = fields.Char(readonly=True, string="Token")
    servientrega_manual_token = fields.Char(string="Token Manual (Pruebas)")
    servientrega_use_manual_token = fields.Boolean(string="Usar Token Manual", default=False)
    servientrega_proxy = fields.Char(string="Proxy Servientrega")
    servientrega_timeout = fields.Integer(string="Timeout (segundos)", default=60)

    def _servientrega_get_endpoints(self):
        self.ensure_one()
        return {
            "auth": self.servientrega_url_auth,
            "guias": self.servientrega_url_guias,
            "cotizador": self.servientrega_url_cotizador,
        }

    def servientrega_get_token(self):
        self.ensure_one()
        
        if self.servientrega_use_manual_token and self.servientrega_manual_token:
            return self.servientrega_manual_token
        
        url = self._servientrega_get_endpoints()["auth"]
        payload = {
            "login": self.servientrega_user,
            "password": self.servientrega_password,
            "codFacturacion": self.servientrega_cod_facturacion,
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=60, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token")
                if token:
                    self.servientrega_token = token
                    return token
            return False
        except Exception as e:
            _logger.error("Error en login: %s", e)
            return False

    def servientrega_rate_shipment(self, order):
        self.ensure_one()
        
        dane_origen = getattr(order.company_id.partner_id, "dane_code", None)
        dane_destino = getattr(order.partner_shipping_id, "dane_code", None)
        
        if not dane_origen or len(str(dane_origen)) != 8:
            return {"success": False, "price": 0.0, "error_message": "Origen sin código DANE válido."}
        if not dane_destino or len(str(dane_destino)) != 8:
            return {"success": False, "price": 0.0, "error_message": "Destino sin código DANE válido."}
        
        token = self.servientrega_token or self.servientrega_get_token()
        if not token:
            return {"success": False, "price": 0.0, "error_message": "No se pudo obtener token."}
        
        url = self._servientrega_get_endpoints()["cotizador"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        payload = {
            "objEnvio": {
                "IdProducto": int(self.servientrega_id_producto),
                "ValorDeclarado": int(order.amount_total),
                "IdDaneCiudadOrigen": str(dane_origen).zfill(8),
                "IdDaneCiudadDestino": str(dane_destino).zfill(8),
                "FormaPago": 2,
                "TiempoEntrega": 1,
                "MedioTransporte": 2,
                "NumRecaudo": 0,
                "PesoReal": float(order._get_estimated_weight() or 1.0),
            }
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                valor = data.get("ValorTotal") or data.get("flete") or 0.0
                return {"success": True, "price": float(valor)}
            return {"success": False, "price": 0.0, "error_message": f"Error {resp.status_code}"}
        except Exception as e:
            return {"success": False, "price": 0.0, "error_message": str(e)}

    def rate_shipment(self, order):
        if self.delivery_type == "servientrega":
            return self.servientrega_rate_shipment(order)
        return super().rate_shipment(order)

    def servientrega_send_shipping(self, picking):
        self.ensure_one()
        
        _logger.info("=== GENERANDO GUÍA ===")
        
        company = self.company_id.partner_id
        partner = picking.partner_id

        dane_origen = getattr(company, "dane_code", None)
        dane_destino = getattr(partner, "dane_code", None)

        if not dane_origen or len(str(dane_origen)) != 8:
            raise UserError("La compañía no tiene código DANE válido.")
        if not dane_destino or len(str(dane_destino)) != 8:
            raise UserError("El cliente no tiene código DANE válido.")

        peso = picking.weight or 1.0
        valor_declarado = int(picking.sale_id.amount_total) if picking.sale_id else 0

        xml = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
   <soapenv:Header>
      <tem:AuthHeader>
         <tem:login>{self.servientrega_user or ''}</tem:login>
         <tem:pwd>{self.servientrega_password or ''}</tem:pwd>
         <tem:Id_CodFacturacion>{self.servientrega_cod_facturacion or ''}</tem:Id_CodFacturacion>
         <tem:Nombre_Cargue>{self.servientrega_nombre_cargue or ''}</tem:Nombre_Cargue>
      </tem:AuthHeader>
   </soapenv:Header>
   <soapenv:Body>
      <tem:CargueMasivoExterno>
         <tem:envios>
            <tem:CargueMasivoExternoDTO>
               <tem:objEnvios>
                  <tem:EnviosExterno>
                     <tem:Ide_Producto>{int(self.servientrega_id_producto)}</tem:Ide_Producto>
                     <tem:Num_ValorDeclaradoTotal>{int(valor_declarado)}</tem:Num_ValorDeclaradoTotal>
                     <tem:Des_CiudadOrigen>{dane_origen}</tem:Des_CiudadOrigen>
                     <tem:Des_Ciudad>{dane_destino}</tem:Des_Ciudad>
                     <tem:Des_Direccion>{partner.street or 'Calle 1 # 2-3'}</tem:Des_Direccion>
                     <tem:Nom_Contacto>{partner.name or 'Cliente Prueba'}</tem:Nom_Contacto>
                     <tem:Des_Telefono>{partner.phone or '3001234567'}</tem:Des_Telefono>
                     <tem:Num_PesoTotal>{peso}</tem:Num_PesoTotal>
                     <tem:Num_Alto>15</tem:Num_Alto>
                     <tem:Num_Ancho>20</tem:Num_Ancho>
                     <tem:Num_Largo>30</tem:Num_Largo>
                     <tem:Des_FormaPago>2</tem:Des_FormaPago>
                     <tem:Des_TipoDuracionTrayecto>1</tem:Des_TipoDuracionTrayecto>
                     <tem:Des_MedioTransporte>1</tem:Des_MedioTransporte>
                     <tem:Num_Recaudo>0</tem:Num_Recaudo>
                     <tem:Gen_Cajaporte>false</tem:Gen_Cajaporte>
                     <tem:Gen_Sobreporte>false</tem:Gen_Sobreporte>
                     <tem:Des_UnidadLongitud>cm</tem:Des_UnidadLongitud>
                     <tem:Des_UnidadPeso>kg</tem:Des_UnidadPeso>
                     <tem:Num_Piezas>1</tem:Num_Piezas>
                     <tem:Nom_UnidadEmpaque>GENERICA</tem:Nom_UnidadEmpaque>
                     <tem:Des_TipoGuia>4</tem:Des_TipoGuia>
                     <tem:Des_DiceContener>Paquete prueba</tem:Des_DiceContener>
                  </tem:EnviosExterno>
               </tem:objEnvios>
            </tem:CargueMasivoExternoDTO>
         </tem:envios>
      </tem:CargueMasivoExterno>
   </soapenv:Body>
</soapenv:Envelope>'''

        url = "https://developer.servientrega.com/WsSisclinetGeneraGuias/GeneracionGuias.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/CargueMasivoExterno",
        }

        try:
            response = requests.post(url, data=xml.encode("utf-8"), headers=headers, timeout=60, verify=False)
            _logger.info("Status: %s", response.status_code)
            _logger.info("RESPUESTA: %s", response.text)
            
            guia_match = re.search(r'<Num_Guia>(\d+)</Num_Guia>', response.text)
            if guia_match:
                guia = guia_match.group(1)
                if guia and guia != '0':
                    picking.servientrega_guide_number = guia
                    picking.message_post(body=f"Guía Servientrega: <b>{guia}</b>")
                    _logger.info("Guía generada: %s", guia)
                    return {"tracking_number": guia, "exact_price": 0.0}
            
            error_match = re.search(r'<string>(.*?)</string>', response.text)
            error_msg = error_match.group(1) if error_match else "No se pudo obtener el número de guía"
            raise UserError(f"Servientrega: {error_msg}")
            
        except Exception as e:
            _logger.error("Error: %s", e)
            raise UserError(str(e))

    def servientrega_get_label(self, picking):
        self.ensure_one()
        
        if not picking.servientrega_guide_number or picking.servientrega_guide_number == '0':
            raise UserError("No hay una guía válida generada.")
        
        _logger.info("Generando sticker para guía: %s", picking.servientrega_guide_number)
        
        xml = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
   <soapenv:Header>
      <tem:AuthHeader>
         <tem:login>{self.servientrega_user or ''}</tem:login>
         <tem:pwd>{self.servientrega_password or ''}</tem:pwd>
         <tem:Id_CodFacturacion>{self.servientrega_cod_facturacion or ''}</tem:Id_CodFacturacion>
         <tem:Nombre_Cargue>{self.servientrega_nombre_cargue or ''}</tem:Nombre_Cargue>
      </tem:AuthHeader>
   </soapenv:Header>
   <soapenv:Body>
      <tem:GenerarGuiaSticker>
         <tem:Num_Guia>{picking.servientrega_guide_number}</tem:Num_Guia>
         <tem:sFormatoImpresionGuia>4</tem:sFormatoImpresionGuia>
      </tem:GenerarGuiaSticker>
   </soapenv:Body>
</soapenv:Envelope>'''

        url = "https://developer.servientrega.com/WsSisclinetGeneraGuias/GeneracionGuias.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/GenerarGuiaSticker",
        }

        try:
            response = requests.post(url, data=xml.encode("utf-8"), headers=headers, timeout=60, verify=False)
            _logger.info("Status: %s", response.status_code)
            _logger.info("RESPUESTA STICKER: %s", response.text)
            
            pdf_match = re.search(r'<GenerarGuiaStickerResult>(.*?)</GenerarGuiaStickerResult>', response.text)
            if pdf_match and pdf_match.group(1) and pdf_match.group(1) != 'false':
                pdf_b64 = pdf_match.group(1)
                picking.servientrega_label_pdf = pdf_b64
                picking.servientrega_label_filename = f"servientrega_{picking.servientrega_guide_number}.pdf"
                picking.message_post(
                    body=f"Rótulo generado para guía {picking.servientrega_guide_number}",
                    attachments=[(picking.servientrega_label_filename, base64.b64decode(pdf_b64))]
                )
                return True
            else:
                raise UserError("No se pudo generar el sticker")
        except Exception as e:
            _logger.error("Error sticker: %s", e)
            raise UserError(str(e))