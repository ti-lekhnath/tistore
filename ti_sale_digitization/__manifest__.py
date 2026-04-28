{
    'name': 'AI Sale Order Digitalization (OCR)',
    'version': '19.0.1.1',
    'category': 'Extra Tools',
    'summary': """Digitize sale order and populate Odoo records  with the extracted data using    OCR    OpenAI's GPT-3.5,
OpenAI,
sale ocr
ocr sale
gpt
chatgpt
Sale
Purchase ocr
Purchase
GPT-3.5
 Inventory Dashboard,
Sales Dashboard,
Account Dashboard,
 Invoice Dashboard,
Revamp Dashboard,
Best Dashboard,
 Odoo Best Dashboard,
Odoo Apps Dashboard,
 Best Ninja Dashboard,
 Analytic Dashboard,
Pre-Configured Dashboard,
Create Dashboard,
Beautiful Dashboard,
 Customized Robust Dashboard,
Predefined Dashboard,
Multiple Dashboards,
Advance Dashboard,
Beautiful Powerful Dashboards,
 Chart Graphs Table View,
All In One Dynamic Dashboard,
 Accounting Stock Dashboard,
 Pie Chart Dashboard,
Modern Dashboard,
Dashboard Studio,
Dashboard Builder,
 Dashboard Designer,
Odoo Studio.

    """,
    'description': """
        This module allows users to digitize sale order, extract relevant information using OCR, and complete Odoo records
         with the extracted data also using artificial intelligence.

 Digitize sale order and populate Odoo records  with the extracted data using    OCR    OpenAI's GPT-3.5,
OpenAI,
sale ocr
ocr sale
Sale
Purchase ocr
Purchase
GPT-3.5
chatgpt
 Inventory Dashboard,
Sales Dashboard,
Account Dashboard,
 Invoice Dashboard,
Revamp Dashboard,
Best Dashboard,
 Odoo Best Dashboard,
Odoo Apps Dashboard,
 Best Ninja Dashboard,
 Analytic Dashboard,
Pre-Configured Dashboard,
Create Dashboard,
Beautiful Dashboard,
 Customized Robust Dashboard,
Predefined Dashboard,
Multiple Dashboards,
Advance Dashboard,
Beautiful Powerful Dashboards,
 Chart Graphs Table View,
All In One Dynamic Dashboard,
 Accounting Stock Dashboard,
 Pie Chart Dashboard,
Modern Dashboard,
Dashboard Studio,
Dashboard Builder,
 Dashboard Designer,
Odoo Studio.
    """,
    'author': "Target Integration",
    'website': "https://targetintegration.com",
    'depends': ['sale', 'sale_management', 'base', 'mail', 'web'],
    'external_dependencies': {
        'python': ['pytesseract', 'pypdf', 'pdf2image', 'numpy', 'Pillow', 'fuzzywuzzy', 'groq'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_digitalize.xml',
        'views/sale_order.xml',
    ],
    'installable': True,
    'application': True,
    'price': 90,
    'auto_install': False,
    'license': 'AGPL-3',
    "images": ["static/ai_completion.gif"],
}
