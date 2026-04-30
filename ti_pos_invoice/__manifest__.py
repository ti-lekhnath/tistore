{
    "name": "TI POS Invoice Print release (1.0.1)",
    "version": "1.0.1",
    "summary": "Replace POS full receipt print with customer invoice preview/print.",
    "category": "Point of Sale",
    "author": "TI Store",
    "website": "https://www.example.com",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "account"],
    "data": [],
    "assets": {
        # Load custom JS and templates in the PoS frontend.
        "point_of_sale._assets_pos": [
            "ti_pos_invoice/static/src/**/*",
        ],
    },
    "installable": True,
    "application": False,
}

