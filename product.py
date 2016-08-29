# -*- coding: utf-8 -*-
"""
    product.py

Implementing Add listing wizard for downstream modules:

* In the __setup__ method of `product.listing.add.start` in downstream
  module, add the type as a valid channel type. Since this is non trivial
  a convenience method `add_source` is provided which will add the source
  type in an idempotent fashion.
* Implement a StateView in the `product.listing.add` wizard with the name
  `start_<source_name>`. This StateView can change the state to other state
  views or transitions. Eventually it should end with the `end` state.

"""
from collections import defaultdict

from trytond.pool import PoolMeta, Pool
from trytond.wizard import Wizard, Button, StateTransition, StateView
from trytond.transaction import Transaction
from trytond import backend
from trytond.model import ModelView, fields, ModelSQL
from trytond.pyson import Eval, Bool

__metaclass__ = PoolMeta
__all__ = [
    'ProductSaleChannelListing', 'Product', 'AddProductListing',
    'AddProductListingStart', 'TemplateSaleChannelListing',
    'Template'
]


class AddProductListingStart(ModelView):
    "Add listing form start"
    __name__ = 'product.listing.add.start'

    product = fields.Many2One(
        'product.product', 'Product', readonly=True
    )

    channel = fields.Many2One(
        'sale.channel', 'Channel', required=True,
        domain=[('source', 'in', [])]
    )

    channel_source = fields.Function(
        fields.Char("Channel Source"),
        getter="on_change_with_channel_source"
    )

    @fields.depends('channel')
    def on_change_with_channel_source(self, name=None):
        return self.channel and self.channel.source

    @classmethod
    def add_source(cls, source):
        """
        A convenience method for downstream modules to add channel
        source types once they have implemented the step in the wizard
        below.

        This method must be called from `__setup__` method of downstream
        module.
        """
        source_leaf = cls.channel.domain[0][2]
        if source not in source_leaf:
            source_leaf.append(source)


class AddProductListing(Wizard):
    "Add product Channel Listing Wizard"
    __name__ = 'product.listing.add'

    start = StateView(
        'product.listing.add.start',
        'sale_channel.listing_add_start_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Next', 'next', 'tryton-go-next', default=True),
        ]
    )
    next = StateTransition()

    def default_start(self, fields):
        return {
            'product': Transaction().context['active_id']
        }

    def transition_next(self):
        return 'start_%s' % self.start.channel.source


class Template:
    "Product Template"
    __name__ = 'product.template'

    channel_listings = fields.One2Many(
        'product.template.channel_listing', 'template', 'Channel Listings'
    )


class TemplateSaleChannelListing(ModelSQL, ModelView):
    """
    Template - Sale Channel
    This model keeps a record of a template's association with Sale Channels.
    """
    __name__ = 'product.template.channel_listing'

    channel = fields.Many2One(
        'sale.channel', 'Sale Channel',
        domain=[('source', '!=', 'manual')],
        select=True, required=True,
        ondelete='RESTRICT'
    )
    template = fields.Many2One(
        'product.template', 'Product Template', required=True,
        select=True, ondelete='CASCADE'
    )
    template_identifier = fields.Char(
        'Template Identifier', select=True, required=True
    )

    @classmethod
    def __setup__(cls):
        """
        Setup the class and define constraints
        """
        super(TemplateSaleChannelListing, cls).__setup__()
        cls._sql_constraints += [
            (
                'channel_template_unique',
                'UNIQUE(channel, template_identifier, template)',
                'Product Template is already mapped to this channel with same identifier'  # noqa
            )
        ]


class Product:
    "Product"
    __name__ = "product.product"

    channel_listings = fields.One2Many(
        'product.product.channel_listing', 'product', 'Channel Listings',
    )
    is_fresh_import = fields.Boolean('Is Fresh Import?')

    @staticmethod
    def get_is_fresh_import():
        return False

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls._buttons.update({
            'add_listing': {},
        })

    @classmethod
    @ModelView.button_action('sale_channel.wizard_add_listing')
    def add_listing(cls, products):
        pass

    @classmethod
    def create_from(cls, channel, product_data):
        """
        Create the product for the channel
        """
        raise NotImplementedError(
            "create_from is not implemented in product for %s channels"
            % channel.source
        )

    @classmethod
    def write(cls, products, values, *args):
        """
        Set 'is_fresh_import' to False when product is updated
        """
        for product in products:
            if product.is_fresh_import:
                values['is_fresh_import'] = False

        return super(Product, cls).write(products, values, *args)


class ProductSaleChannelListing(ModelSQL, ModelView):
    '''Product - Sale Channel
    This model keeps a record of a product's association with Sale Channels.
    A product can be listed on multiple marketplaces
    '''
    __name__ = 'product.product.channel_listing'

    # TODO: Only show channels where this ability is there. For example
    # showing a manual channel is pretty much useless
    channel = fields.Many2One(
        'sale.channel', 'Sale Channel',
        domain=[('source', '!=', 'manual')],
        required=True, select=True,
        ondelete='RESTRICT'
    )
    product = fields.Many2One(
        'product.product', 'Product', select=True,
        states={'required': Eval('state') == 'active'},
        ondelete='CASCADE', depends=['state']
    )
    product_identifier = fields.Char(
        "Product Identifier", select=True, required=True
    )
    state = fields.Selection([
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ], 'State', required=True, select=True)
    channel_source = fields.Function(
        fields.Char("Channel Source"),
        getter="on_change_with_channel_source"
    )

    quantity = fields.Function(
        fields.Float(
            'Quantity',
            digits=(16, Eval('unit_digits', 2)), depends=['unit_digits']
        ), 'get_availability_fields'
    )
    unit_digits = fields.Function(
        fields.Integer('Unit Digits'), 'get_unit_digits'
    )
    availability_type_used = fields.Function(
        fields.Selection([
            ('bucket', 'Bucket'),
            ('quantity', 'Quantity'),
            ('infinite', 'Infinite'),
        ], 'Type'), 'get_availability_fields'
    )
    availability_used = fields.Function(
        fields.Selection([
            ('in_stock', 'In-Stock'),
            ('out_of_stock', 'Out Of Stock'),
        ], 'Availability', states={
            'invisible': ~Bool(Eval('availability_type_used') == 'bucket')
        }, depends=['availability_type_used']),
        'get_availability_fields'
    )
    listing_url = fields.Function(
        fields.Char('Listing URL'), 'get_listing_url'
    )

    @classmethod
    def __register__(cls, module_name):
        super(ProductSaleChannelListing, cls).__register__(module_name)

        TableHandler = backend.get('TableHandler')
        cursor = Transaction().cursor
        table = TableHandler(cursor, cls, module_name)

        # Remove not null constraint from 'product'
        table.not_null_action('product', action='remove')

    def get_unit_digits(self, name):
        if self.product:
            self.product.default_uom.digits
        return 2

    def get_listing_url(self, name):
        """
        Downstream modules should implement this function
        and return a valid url
        """
        return None

    @classmethod
    def get_availability_fields(cls, listings, names):
        listing_ids = map(int, listings)
        values = defaultdict(lambda: dict.fromkeys(listing_ids, None))
        for name in names:
            # Just call the default dict once so all fields have values
            # even if product is absent
            values[name]

        for listing in listings:
            if listing.product:
                availability = listing.get_availability()
                values['availability_type_used'][listing.id] = \
                    availability['type']
                values['availability_used'][listing.id] = availability.get(
                    'value'
                )
                values['quantity'][listing.id] = availability.get('quantity')
        return values

    @fields.depends('channel')
    def on_change_with_channel_source(self, name=None):
        return self.channel and self.channel.source

    @classmethod
    def __setup__(cls):
        '''
        Setup the class and define constraints
        '''
        super(ProductSaleChannelListing, cls).__setup__()
        cls._sql_constraints += [
            (
                'channel_product_identifier_uniq',
                'UNIQUE(channel, product_identifier)',
                'This external product is already mapped with same channel.'
            )
        ]

        cls._buttons.update({
            'export_inventory_button': {},
        })

    @staticmethod
    def default_state():
        return 'active'

    @classmethod
    def create_from(cls, channel, product_data):
        """
        Create a listing for the product from channel and data
        """
        raise NotImplementedError(
            "create_from is not implemented in channel listing for %s channels"
            % channel.source
        )

    @classmethod
    @ModelView.button
    def export_inventory_button(cls, listings):
        return cls.export_bulk_inventory(listings)

    def export_inventory(self):
        """
        Export listing.product inventory to listing.channel

        Since external channels are implemented by downstream modules, it is
        the responsibility of those channels to implement exporting or call
        super to delegate.
        """
        raise NotImplementedError(
            "Export inventory is not implemented for %s channels"
            % self.channel.source
        )

    @classmethod
    def export_bulk_inventory(cls, listings):
        """
        Export listing.product inventory to listing.channel in bulk

        Since external channels are implemented by downstream modules, it is
        the responsibility of those channels to implement bulk exporting for
        respective channels.
        Default behaviour is to export inventory individually.
        """
        for listing in listings:
            listing.export_inventory()

    def get_availability_context(self):
        """
        Allow overriding the context used to compute availability of
        products.
        """
        return {
            'locations': [self.channel.warehouse.id],
        }

    def get_availability(self):
        """
        Return the availability of the product for this listing
        """
        Product = Pool().get('product.product')

        with Transaction().set_context(**self.get_availability_context()):
            rv = {'type': 'bucket', 'value': None, 'quantity': None}
            if self.product:
                product = Product(self.product.id)
                rv['quantity'] = product.quantity
                if rv['quantity'] > 0:
                    rv['value'] = 'in_stock'
                else:
                    rv['value'] = 'out_of_stock'
            return rv
