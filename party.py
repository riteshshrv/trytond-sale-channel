# -*- coding: utf-8 -*-
"""
    party

"""
from trytond.pool import PoolMeta
from trytond.model import ModelView, fields, ModelSQL, Unique

__metaclass__ = PoolMeta
__all__ = [
    'Party', 'PartySaleChannelListing'
]


class Party:
    "Party"
    __name__ = 'party.party'

    channel_listings = fields.One2Many(
        'party.party.channel_listing', 'party', 'Channel Listings'
    )


class PartySaleChannelListing(ModelSQL, ModelView):
    """
    Party - Sale Channel
    This model keeps a recored of a contact's association with Sale Channels
    """
    __name__ = 'party.party.channel_listing'

    channel = fields.Many2One(
        'sale.channel', 'Sale Channel',
        domain=[('source', '!=', 'manual')],
        select=True, required=True,
        ondelete='RESTRICT'
    )
    party = fields.Many2One(
        'party.party', 'Contact', required=True,
        select=True, ondelete='CASCADE'
    )
    contact_identifier = fields.Char(
        'Contact Identifier', select=True, required=True
    )

    @classmethod
    def __setup__(cls):
        """
        Setup the class and define constraints
        """
        super(PartySaleChannelListing, cls).__setup__()
        table = cls.__table__()
        cls._sql_constraints += [(
            'channel_party_unique',
            Unique(table, table.channel, table.contact_identifier, table.party),
            'Contact is already mapped to this channel with same identifier'
        )]
