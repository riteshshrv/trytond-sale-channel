# -*- coding: utf-8 -*-
"""
    __init__.py

"""
from trytond.pool import Pool
from channel import (
    SaleChannel, ReadUser, WriteUser, ChannelException, ChannelOrderState,
    TaxMapping
)
from wizard import (
    ImportDataWizard, ImportDataWizardStart, ImportDataWizardSuccess,
    ExportDataWizard, ExportDataWizardStart, ExportDataWizardSuccess,
    ImportDataWizardProperties, ImportOrderStatesStart, ImportOrderStates,
    ExportPricesStatus, ExportPricesStart, ExportPrices
)
from product import (
    ProductSaleChannelListing, Product, AddProductListing,
    AddProductListingStart, Template, TemplateSaleChannelListing
)
from party import Party, PartySaleChannelListing
from carrier import SaleChannelCarrier
from sale import Sale, SaleLine
from user import User


def register():
    Pool.register(
        SaleChannel,
        TaxMapping,
        ReadUser,
        WriteUser,
        ChannelException,
        ChannelOrderState,
        SaleChannelCarrier,
        Party,
        PartySaleChannelListing,
        User,
        Sale,
        SaleLine,
        ProductSaleChannelListing,
        Product,
        Template,
        TemplateSaleChannelListing,
        ImportDataWizardStart,
        ImportDataWizardSuccess,
        ImportDataWizardProperties,
        ExportDataWizardStart,
        ExportDataWizardSuccess,
        ImportOrderStatesStart,
        ExportPricesStatus,
        ExportPricesStart,
        AddProductListingStart,
        module='sale_channel', type_='model'
    )
    Pool.register(
        AddProductListing,
        ImportDataWizard,
        ExportDataWizard,
        ImportOrderStates,
        ExportPrices,
        module='sale_channel', type_='wizard'
    )
