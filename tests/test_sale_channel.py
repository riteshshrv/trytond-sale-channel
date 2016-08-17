# -*- coding: utf-8 -*-
"""
    tests/test_sale_channel.py

"""
import unittest
from decimal import Decimal
from contextlib import nested

import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, USER, ModuleTestCase, \
    with_transaction
from trytond.exceptions import UserError
from trytond.transaction import Transaction


class BaseTestCase(unittest.TestCase):
    '''
    Base Test Case sale payment module.
    '''

    def setUp(self):
        """
        Set up data used in the tests.
        this method is called before each test function execution.
        """
        trytond.tests.test_tryton.install_module('sale_channel')

        self.Currency = POOL.get('currency.currency')
        self.Company = POOL.get('company.company')
        self.Party = POOL.get('party.party')
        self.User = POOL.get('res.user')
        self.Country = POOL.get('country.country')
        self.Subdivision = POOL.get('country.subdivision')
        self.Sale = POOL.get('sale.sale')
        self.SaleLine = POOL.get('sale.line')
        self.SaleChannel = POOL.get('sale.channel')
        self.Location = POOL.get('stock.location')
        self.PriceList = POOL.get('product.price_list')
        self.Payment_Term = POOL.get('account.invoice.payment_term')
        self.Sequence = POOL.get('ir.sequence')
        self.Group = POOL.get('res.group')
        self.ImportDataWizard = POOL.get(
            'sale.channel.import_data', type='wizard'
        )

    def _create_product_template(self, name, vlist, uri, uom=u'Unit'):
        """
        Create a product template with products and return its ID
        :param name: Name of the product
        :param vlist: List of dictionaries of values to create
        :param uri: uri of product template
        :param uom: Note it is the name of UOM (not symbol or code)
        """
        ProductTemplate = POOL.get('product.template')
        Uom = POOL.get('product.uom')

        for values in vlist:
            values['name'] = name
            values['default_uom'], = Uom.search([('name', '=', uom)], limit=1)
            values['sale_uom'], = Uom.search([('name', '=', uom)], limit=1)
            values['products'] = [('create', [{}])]
        return ProductTemplate.create(vlist)

    def _get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec
        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts[0] if accounts else False

    def _create_coa_minimal(self, company):
        """Create a minimal chart of accounts
        """
        AccountTemplate = POOL.get('account.account.template')
        Account = POOL.get('account.account')

        account_create_chart = POOL.get(
            'account.create_chart', type="wizard")

        account_template, = AccountTemplate.search([
            ('parent', '=', None),
            ('name', '=', 'Minimal Account Chart')
        ])

        session_id, _, _ = account_create_chart.create()
        create_chart = account_create_chart(session_id)
        create_chart.account.account_template = account_template
        create_chart.account.company = company
        create_chart.transition_create_account()

        receivable, = Account.search([
            ('kind', '=', 'receivable'),
            ('company', '=', company),
        ])
        payable, = Account.search([
            ('kind', '=', 'payable'),
            ('company', '=', company),
        ])
        create_chart.properties.company = company
        create_chart.properties.account_receivable = receivable
        create_chart.properties.account_payable = payable
        create_chart.transition_create_properties()

    def get_account_by_kind(self, kind, company=None, silent=True):
        """Returns an account with given spec
        :param kind: receivable/payable/expense/revenue
        :param silent: dont raise error if account is not found
        """
        Account = POOL.get('account.account')
        Company = POOL.get('company.company')

        if company is None:
            company, = Company.search([], limit=1)

        accounts = Account.search([
            ('kind', '=', kind),
            ('company', '=', company)
        ], limit=1)
        if not accounts and not silent:
            raise Exception("Account not found")
        return accounts and accounts[0].id or None

    def _create_payment_term(self):
        """Create a simple payment term with all advance
        """
        PaymentTerm = POOL.get('account.invoice.payment_term')

        return PaymentTerm.create([{
            'name': 'Direct',
            'lines': [('create', [{'type': 'remainder'}])]
        }])

    def setup_defaults(self):
        """Creates default data for testing
        """
        self.currency, = self.Currency.create([{
            'name': 'US Dollar',
            'code': 'USD',
            'symbol': '$',
        }])

        # Create a payment term
        self.payment_term, = self._create_payment_term()

        self.country, = self.Country.create([{
            'name': 'United States of America',
            'code': 'US',
        }])

        self.subdivision, = self.Subdivision.create([{
            'country': self.country.id,
            'name': 'California',
            'code': 'CA',
            'type': 'state',
        }])

        # Create party
        with Transaction().set_context(company=None):
            self.company_party, self.sale_party = self.Party.create([{
                'name': 'Openlabs',
                'addresses': [('create', [{
                    'name': 'Openlabs',
                    'city': 'Gothom',
                    'country': self.country.id,
                    'subdivision': self.subdivision.id,
                }])],
                'customer_payment_term': self.payment_term.id,
            }, {
                'name': 'John Wick',
                'addresses': [('create', [{
                    'name': 'John Wick',
                    'city': 'Gothom',
                    'country': self.country.id,
                    'subdivision': self.subdivision.id,
                }, {
                    'name': 'John Doe',
                    'city': 'Gothom',
                    'country': self.country.id,
                    'subdivision': self.subdivision.id,
                }])],
                'customer_payment_term': self.payment_term.id,
            }])

        self.company, = self.Company.create([{
            'party': self.company_party,
            'currency': self.currency
        }])

        user = self.User(USER)
        self.User.write([user], {
            'company': self.company,
            'main_company': self.company,
        })

        self.sales_user, = self.User.create([{
            'name': 'Sales Person',
            'login': 'sale',
            'company': self.company,
            'main_company': self.company,
            'groups': [('add', [
                self.Group.search([('name', '=', 'Sales')])[0].id
            ])]
        }])

        self.price_list = self.PriceList(
            name='PL 1',
            company=self.company
        )
        self.price_list.save()
        self._create_coa_minimal(self.company)

        # Create product templates with products
        self.template1, = self._create_product_template(
            'product-1',
            [{
                'type': 'goods',
                'salable': True,
                'list_price': Decimal('10'),
                'cost_price': Decimal('5'),
                'account_expense': self._get_account_by_kind('expense').id,
                'account_revenue': self._get_account_by_kind('revenue').id,
            }],
            uri='product-1',
        )
        self.template2, = self._create_product_template(
            'product-2',
            [{
                'type': 'goods',
                'salable': True,
                'list_price': Decimal('15'),
                'cost_price': Decimal('5'),
                'account_expense': self._get_account_by_kind('expense').id,
                'account_revenue': self._get_account_by_kind('revenue').id,
            }],
            uri='product-2',
        )
        self.product1 = self.template1.products[0]
        self.product2 = self.template2.products[0]

        with Transaction().set_context(company=self.company.id):
            self.channel1, self.channel2, self.channel3, self.channel4 = \
                self.SaleChannel.create([{
                    'name': 'Channel 1',
                    'code': 'C1',
                    'address': self.company_party.addresses[0].id,
                    'source': 'manual',
                    'timezone': 'UTC',
                    'warehouse': self.Location.search([
                        ('code', '=', 'WH')
                    ])[0].id,
                    'invoice_method': 'manual',
                    'shipment_method': 'manual',
                    'payment_term': self.payment_term.id,
                    'price_list': self.price_list,
                }, {
                    'name': 'Channel 2',
                    'code': 'C2',
                    'address': self.company_party.addresses[0].id,
                    'source': 'manual',
                    'timezone': 'US/Pacific',
                    'warehouse': self.Location.search([
                        ('code', '=', 'WH')
                    ])[0].id,
                    'invoice_method': 'manual',
                    'shipment_method': 'manual',
                    'payment_term': self.payment_term.id,
                    'price_list': self.price_list,
                    'read_users': [('add', [self.sales_user.id])],
                }, {
                    'name': 'Channel 3',
                    'code': 'C3',
                    'address': self.company_party.addresses[0].id,
                    'source': 'manual',
                    'warehouse': self.Location.search([
                        ('code', '=', 'WH')
                    ])[0].id,
                    'invoice_method': 'manual',
                    'shipment_method': 'manual',
                    'payment_term': self.payment_term.id,
                    'price_list': self.price_list,
                    'read_users': [('add', [self.sales_user.id])],
                    'create_users': [('add', [self.sales_user.id])],
                }, {
                    'name': 'Channel 4',
                    'code': 'C4',
                    'address': self.company_party.addresses[0].id,
                    'source': 'manual',
                    'timezone': 'US/Eastern',
                    'warehouse': self.Location.search([
                        ('code', '=', 'WH')
                    ])[0].id,
                    'invoice_method': 'manual',
                    'shipment_method': 'manual',
                    'payment_term': self.payment_term.id,
                    'price_list': self.price_list,
                    'read_users': [('add', [self.sales_user.id])],
                    'create_users': [('add', [self.sales_user.id])],
                }])

        self.sales_user.current_channel = self.channel3
        self.sales_user.save()
        self.assertTrue(self.channel3.rec_name in self.sales_user.status_bar)

        # Save IDs to share between transactions
        self.sales_user_id = self.sales_user.id

    def create_sale(self, res_user_id, channel=None):
        """
        Create sale in new transaction
        """
        with nested(
                Transaction().set_user(res_user_id),
                Transaction().set_context(
                    company=self.company.id, current_channel=channel
                )):
            sale = self.Sale(
                party=self.sale_party,
                invoice_address=self.sale_party.addresses[0],
                shipment_address=self.sale_party.addresses[0],
                lines=[],
            )
            sale.save()
            sale.on_change_channel()
            self.assertEqual(sale.invoice_method, 'manual')
            if channel:
                self.assertEqual(sale.channel_type, channel.source)
            return sale


class TestSaleChannel(BaseTestCase, ModuleTestCase):
    """
    Test Sale Channel Module
    """
    module = "sale_channel"

    @with_transaction()
    def test_0010_permission_sale_admin(self):
        SALE_ADMIN = USER
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        # Creating sale with admin(sale_admin) user
        self.create_sale(SALE_ADMIN, self.channel1)
        self.create_sale(SALE_ADMIN, self.channel2)
        self.create_sale(SALE_ADMIN, self.channel3)
        self.create_sale(SALE_ADMIN, self.channel4)

    @with_transaction()
    def test_0020_permission_sale_user(self):
        """
        Cannot create on channel without any permissions
        """
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        with self.assertRaises(UserError):
            # Can not create without create_permission
            self.create_sale(self.sales_user_id, self.channel1)

    @with_transaction()
    def test_0030_permission_sale_user(self):
        """
        Cannot create sale on readonly channel
        """
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        with self.assertRaises(UserError):
            # Can not create using Read channel
            self.create_sale(self.sales_user_id, self.channel2)

    @with_transaction()
    def test_0040_permission_sale_user(self):
        """
        Ability to read orders in channels the user has access to
        """
        self.setup_defaults()

        # Create a bunch of orders first
        SALE_ADMIN = USER
        sale1 = self.create_sale(SALE_ADMIN, self.channel1)
        sale2 = self.create_sale(SALE_ADMIN, self.channel2)
        sale3 = self.create_sale(SALE_ADMIN, self.channel3)
        sale4 = self.create_sale(SALE_ADMIN, self.channel4)

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        with Transaction().set_user(self.sales_user_id):
            sales = self.Sale.search([])

            self.assertEqual(len(sales), 3)
            self.assertTrue(sale1 not in sales)  # No Access
            self.assertTrue(sale2 in sales)      # R
            self.assertTrue(sale3 in sales)      # RW
            self.assertTrue(sale4 in sales)      # RW

    @with_transaction()
    def test_0050_permission_sale_user(self):
        """
        Cannot edit sale on channel with no access
        """
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        sale1 = self.create_sale(USER, self.channel1)

        with self.assertRaises(UserError):
            with Transaction().set_user(self.sales_user_id):
                sale1 = self.Sale(sale1.id)
                # Try write on No Access Channel's Sale
                sale1.invoice_address = self.sale_party.addresses[1]
                sale1.save()

    @with_transaction()
    def test_0060_permission_sale_user(self):
        """
        CAN edit sale on Create/Read channel
        """
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        sale2 = self.create_sale(USER, self.channel2)
        sale3 = self.create_sale(USER, self.channel3)

        with Transaction().set_user(self.sales_user_id):
            sale2 = self.Sale(sale2.id)
            sale3 = self.Sale(sale3.id)

            sale3.invoice_address = self.sale_party.addresses[1]
            sale3.save()

            self.assertEqual(
                sale3.invoice_address, self.sale_party.addresses[1]
            )

            sale2.invoice_address = self.sale_party.addresses[1]
            sale2.save()

    @with_transaction()
    def test_0070_state_change(self):
        """
        No matter who you are, cannot change channel on quote state
        """
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A
        sale3 = self.create_sale(USER, self.channel3)
        self.Sale.quote([sale3])
        self.assertEqual(sale3.state, 'quotation')

        with self.assertRaises(UserError):
            sale3.channel = self.channel4
            sale3.save()

    @with_transaction()
    def test_0080_check_create_access(self):
        """
        Check user have access to channel
        """
        SALE_ADMIN = USER
        self.setup_defaults()

        #      USER       Channel1    Channel2    Channel3  Channel4
        #    sale_user       -           R           RW       RW
        #    sale_admin     N/A         N/A         N/A      N/A

        # Creating sale with admin(sale_admin) user
        sale1 = self.create_sale(SALE_ADMIN, self.channel1)
        sale2 = self.create_sale(SALE_ADMIN, self.channel2)
        sale3 = self.create_sale(SALE_ADMIN, self.channel3)

        with Transaction().set_user(self.sales_user_id):
            with self.assertRaises(UserError):
                self.Sale.copy([sale1])

            copy_sale2, = self.Sale.copy([sale2])
            self.assertNotEqual(copy_sale2, sale2)
            # Assert with sale_users current channel
            self.assertNotEqual(copy_sale2.channel, sale2.channel)
            self.assertEqual(
                copy_sale2.channel, self.sales_user.current_channel
            )

            copy_sale3, = self.Sale.copy([sale3])
            self.assertNotEqual(copy_sale3, sale3)
            self.assertEqual(copy_sale3.channel, sale3.channel)

    @with_transaction()
    def test_0090_check_channel_exception(self):
        """
        Check if channel exception is being created
        """
        ChannelException = POOL.get('channel.exception')

        self.setup_defaults()

        sale = self.create_sale(1, self.channel1)

        self.assertFalse(sale.has_channel_exception)

        channel_exception, = ChannelException.create([{
            'origin': '%s,%s' % (sale.__name__, sale.id),
            'log': 'Sale has exception',
            'channel': sale.channel.id,
        }])

        self.assert_(channel_exception)

        self.assertTrue(sale.has_channel_exception)

        # Mark exception as resolved
        channel_exception.is_resolved = True
        channel_exception.save()

        self.assertFalse(sale.has_channel_exception)

    @with_transaction()
    def test_0095_check_channel_exception_searcher(self):
        """
        Check searcher for channel exception
        """
        ChannelException = POOL.get('channel.exception')

        self.setup_defaults()

        sale1 = self.create_sale(1, self.channel1)
        sale2 = self.create_sale(1, self.channel1)
        sale3 = self.create_sale(1, self.channel1)

        self.assertFalse(sale1.has_channel_exception)
        self.assertFalse(sale2.has_channel_exception)

        self.assertEqual(
            self.Sale.search([
                ('has_channel_exception', '=', True)
            ], count=True), 0
        )

        self.assertEqual(
            self.Sale.search([
                ('has_channel_exception', '=', False)
            ], count=True), 3
        )

        ChannelException.create([{
            'origin': '%s,%s' % (sale1.__name__, sale1.id),
            'log': 'Sale has exception',
            'channel': sale1.channel.id,
            'is_resolved': False,
        }])

        ChannelException.create([{
            'origin': '%s,%s' % (sale2.__name__, sale2.id),
            'log': 'Sale has exception',
            'channel': sale2.channel.id,
            'is_resolved': True,
        }])

        self.assertEqual(
            self.Sale.search([('has_channel_exception', '=', True)]),
            [sale1]
        )

        # Sale2 has exception but is resolved already
        self.assertEqual(
            self.Sale.search([('has_channel_exception', '=', False)]),
            [sale3, sale2]
        )

    @with_transaction()
    def test_0100_orders_import_wizard(self):
        """
        Check orders import wizard
        """
        self.setup_defaults()
        with Transaction().set_context(
            active_id=self.channel1, company=self.company.id
        ):
            session_id, start_state, end_state = \
                self.ImportDataWizard.create()
            self.ImportDataWizard.execute(session_id, {}, start_state)
            import_data = self.ImportDataWizard(session_id)
            import_data.start.import_orders = True
            import_data.start.import_products = True
            import_data.start.channel = self.channel1

            # 1. Product / Order is being imported but properties are not
            # set So it will ask for properties first
            self.assertFalse(import_data.get_default_property('revenue'))
            self.assertFalse(import_data.get_default_property('expense'))

            self.assertEqual(import_data.transition_next(), 'properties')

            import_data.properties.account_revenue = \
                self.get_account_by_kind('revenue')
            import_data.properties.account_expense = \
                self.get_account_by_kind('expense')
            import_data.properties.company = self.company.id

            self.assertEqual(
                import_data.transition_create_properties(), 'import_'
            )

            # Properties are created
            self.assertTrue(import_data.get_default_property('revenue'))
            self.assertTrue(import_data.get_default_property('expense'))

            # Since properties are set, it wont ask for properties
            # again
            self.assertEqual(import_data.transition_next(), 'import_')

            with self.assertRaises(NotImplementedError):
                # NotImplementedError is thrown in this case.
                # Importing orders feature is not available in this module
                import_data.transition_import_()

    @with_transaction()
    def test_0200_channel_availability(self):
        StockMove = POOL.get('stock.move')
        Location = POOL.get('stock.location')

        self.setup_defaults()

        self.assertEqual(
            self.channel1.get_availability(self.product1),
            {'type': 'bucket', 'value': 'out_of_stock'}
        )
        self.assertEqual(
            self.channel1.get_availability(self.product2),
            {'type': 'bucket', 'value': 'out_of_stock'}
        )

        lost_and_found, = Location.search([
            ('type', '=', 'lost_found')
        ])
        with Transaction().set_context(company=self.company.id):
            # Bring in inventory for item 1
            StockMove.create([{
                'from_location': lost_and_found,
                'to_location': self.channel1.warehouse.storage_location,
                'quantity': 10,
                'product': self.product1,
                'uom': self.product1.default_uom,
            }])
        self.assertEqual(
            self.channel1.get_availability(self.product1),
            {'type': 'bucket', 'value': 'in_stock'}
        )
        self.assertEqual(
            self.channel1.get_availability(self.product2),
            {'type': 'bucket', 'value': 'out_of_stock'}
        )

    @with_transaction()
    def test_0095_check_duplicate_channel_identifier_for_sale(self):
        """
        Check if error is raised for duplicate channel identifier in sale
        """
        self.setup_defaults()

        sale1 = self.create_sale(1, self.channel1)

        sale2 = self.create_sale(1, self.channel1)

        sale1.channel_identifier = 'Test Sale 1'
        sale1.save()

        # Put same channel identifer for sale 2, should raise error
        with self.assertRaises(UserError):
            sale2.channel_identifier = 'Test Sale 1'
            sale2.save()

    @with_transaction()
    def test_0095_check_duplicate_channel_identifier_for_sale_line(self):
        """
        Check if error is raised for duplicate channel identifier in sale line
        """
        self.setup_defaults()

        sale = self.create_sale(1, self.channel1)

        self.SaleLine.create([{
            'type': 'comment',
            'channel_identifier': 'Sale Line 1',
            'description': 'Sale Line',
            'sale': sale.id
        }])

        # Create sale line with same channel identifer, should raise error
        with self.assertRaises(UserError):
            self.SaleLine.create([{
                'type': 'comment',
                'channel_identifier': 'Sale Line 1',
                'sale': sale,
                'description': 'Sale Line',
            }])

    @with_transaction()
    def test_0100_return_sale_with_channel_identifier(self):
        """
        Check if return sale works with channel_identifier
        """
        ReturnSale = POOL.get('sale.return_sale', type='wizard')
        Sale = POOL.get('sale.sale')

        self.setup_defaults()

        # Return sale with channel identifier
        sale1 = self.create_sale(1, self.channel1)

        sale1.channel_identifier = 'Test Sale 1'
        sale1.save()

        session_id, _, _ = ReturnSale.create()

        return_sale = ReturnSale(session_id)

        with Transaction().set_context(active_ids=[sale1.id]):
            return_sale.do_return_(return_sale.return_.get_action())

        # Return sale with lines
        sale2 = self.create_sale(1, self.channel1)
        sale2.channel_identifier = 'Test Sale 2'
        sale2.save()
        Sale.write([sale2], {
            'lines': [
                ('create', [{
                    'type': 'comment',
                    'channel_identifier': 'Test Sale Line',
                    'description': 'Test Desc'
                }])
            ]
        })

        session_id, _, _ = ReturnSale.create()

        return_sale = ReturnSale(session_id)

        with Transaction().set_context(active_ids=[sale2.id]):
            return_sale.do_return_(return_sale.return_.get_action())

    @with_transaction()
    def test_0110_map_tax(self):
        """
        Check if tax is mapped
        """

        SaleChannel = POOL.get('sale.channel')
        SaleChannelTax = POOL.get('sale.channel.tax')
        Tax = POOL.get('account.tax')

        self.setup_defaults()

        new_channel, = SaleChannel.create([{
            'name': 'Channel 1',
            'code': 'C1',
            'address': self.company_party.addresses[0].id,
            'source': 'manual',
            'warehouse': self.Location.search([
                ('code', '=', 'WH')
            ])[0].id,
            'currency': self.currency.id,
            'invoice_method': 'manual',
            'shipment_method': 'manual',
            'payment_term': self.payment_term.id,
            'price_list': self.price_list,
            'company': self.company.id,
        }])

        tax1, = Tax.create([
            {
                'name': "tax1",
                'description': "This is description",
                'type': 'percentage',
                'company': self.company.id,
                'invoice_account': self._get_account_by_kind('revenue').id,
                'credit_note_account':
                    self._get_account_by_kind('revenue').id,
                'rate': Decimal('8.00'),
            }
        ])

        mapped_tax, = SaleChannelTax.create([{
            'name': 'new_channel_tax',
            'rate': Decimal('8.00'),
            'tax': tax1.id,
            'channel': new_channel.id,
        }])

        self.assertEqual(
            new_channel.get_tax('new_channel_tax', Decimal('8.00')), tax1
        )

    @with_transaction()
    def test_0115_check_processing_of_sale(self):
        """
        Check if channel exception is being created
        """
        ChannelException = POOL.get('channel.exception')

        self.setup_defaults()

        sale = self.create_sale(1, self.channel1)

        self.assertFalse(sale.has_channel_exception)

        channel_exception, = ChannelException.create([{
            'origin': '%s,%s' % (sale.__name__, sale.id),
            'log': 'Sale has exception',
            'channel': sale.channel.id,
        }])

        self.assert_(channel_exception)

        self.assertTrue(sale.has_channel_exception)

        # sale should not be confirmed as long as channel exception
        # is not resolved and error should be raised for it
        with self.assertRaises(UserError):
            self.Sale.confirm([sale])

        # Mark exception as resolved
        channel_exception.is_resolved = True
        channel_exception.save()

        self.assertFalse(sale.has_channel_exception)

        # Exception error should not be raised after it is resolved
        self.Sale.confirm([sale])

    @with_transaction()
    def test_0120_check_channel_exception(self):
        """
        Check that duplication of sale does not duplicate its
        exceptions (irrespective of being resolved or not)
        """
        Sale = POOL.get('sale.sale')
        ChannelException = POOL.get('channel.exception')

        self.setup_defaults()

        sale = self.create_sale(1, self.channel1)

        self.assertFalse(sale.has_channel_exception)

        # create an exception manually for sake of test
        channel_exception, = ChannelException.create([{
            'origin': '%s,%s' % (sale.__name__, sale.id),
            'log': 'Sale has some dummy exception',
            'channel': sale.channel.id,
        }])

        self.assert_(channel_exception)
        self.assertTrue(sale.has_channel_exception)

        duplicate_sale, = Sale.copy([sale])
        self.assertFalse(duplicate_sale.has_channel_exception)


def suite():
    """
    Define Suite
    """
    test_suite = trytond.tests.test_tryton.suite()
    test_suite.addTests(
        unittest.TestLoader().loadTestsFromTestCase(TestSaleChannel)
    )
    return test_suite

if __name__ == '__main__':
    unittest.TextTestRunner(verbosity=2).run(suite())
