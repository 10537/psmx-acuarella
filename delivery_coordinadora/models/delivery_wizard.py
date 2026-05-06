# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChooseDeliveryCarrier(models.TransientModel):
    """Extend the standard delivery carrier wizard with Coordinadora package dimensions.

    When the selected carrier is Coordinadora the user can enter the package
    dimensions (alto, ancho, largo, peso) directly in the wizard.  These values
    are injected into the execution context so that coordinadora_rate_shipment
    produces a real quote instead of using fixed defaults.
    """

    _inherit = 'choose.delivery.carrier'

    coordinadora_alto = fields.Float(
        string='Alto (cm)',
        default=10.0,
        help='Altura del paquete en centímetros.',
    )
    coordinadora_ancho = fields.Float(
        string='Ancho (cm)',
        default=10.0,
        help='Ancho del paquete en centímetros.',
    )
    coordinadora_largo = fields.Float(
        string='Largo (cm)',
        default=10.0,
        help='Largo del paquete en centímetros.',
    )
    coordinadora_peso = fields.Float(
        string='Peso (kg)',
        default=1.0,
        help='Peso del paquete en kilogramos.',
    )
    show_coordinadora_dims = fields.Boolean(
        compute='_compute_show_coordinadora_dims',
    )

    @api.depends('carrier_id', 'carrier_id.delivery_type')
    def _compute_show_coordinadora_dims(self):
        for rec in self:
            rec.show_coordinadora_dims = (
                rec.carrier_id.delivery_type == 'coordinadora'
            )

    # ------------------------------------------------------------------
    # Re-compute rate whenever dimensions change
    # ------------------------------------------------------------------

    @api.onchange('coordinadora_alto', 'coordinadora_ancho',
                  'coordinadora_largo', 'coordinadora_peso')
    def _onchange_coordinadora_dims(self):
        if self.carrier_id.delivery_type == 'coordinadora':
            self._get_shipment_rate()

    # ------------------------------------------------------------------
    # Inject dimensions into context before rate computation
    # ------------------------------------------------------------------

    def _get_shipment_rate(self):
        if self.carrier_id.delivery_type == 'coordinadora':
            return super(
                ChooseDeliveryCarrier,
                self.with_context(
                    coordinadora_alto=self.coordinadora_alto,
                    coordinadora_ancho=self.coordinadora_ancho,
                    coordinadora_largo=self.coordinadora_largo,
                    coordinadora_peso=self.coordinadora_peso,
                ),
            )._get_shipment_rate()
        return super()._get_shipment_rate()
