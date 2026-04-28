
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'



    def action_show_digitalize_order_wizard(self):
        return {
            'name': 'Digitalize Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.digitalize',
            'view_mode': 'form',
            'context': {'active_ids': self.ids},
            'view_id': self.env.ref('ti_sale_digitization.view_digitalize_form').id,
            'target': 'new',
        }
