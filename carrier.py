# -*- coding: utf-8 -*-
from trytond.pool import PoolMeta
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval


__metaclass__ = PoolMeta
__all__ = [
    'SaleChannelCarrier',
]

CARRIER_STATES = {
    'readonly': (Eval('id', 0) > 0)
}
CARRIER_DEPENDS = ['id']


class SaleChannelCarrier(ModelSQL, ModelView):
    """
    Shipping Carriers

    This model stores the carriers / shipping methods, each record
    here can be mapped to a carrier in tryton which will then be
    used for managing export of tracking info.
    """
    __name__ = 'sale.channel.carrier'
    _rec_name = 'name'

    name = fields.Char('Name', states=CARRIER_STATES, depends=CARRIER_DEPENDS)
    code = fields.Char("Code", states=CARRIER_STATES, depends=CARRIER_DEPENDS)
    carrier = fields.Many2One('carrier', 'Carrier')
    channel = fields.Many2One(
        'sale.channel', 'Channel', readonly=True
    )
