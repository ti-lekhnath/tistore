# models/models.py
import base64
import io
import json
import logging
import uuid

from groq import Groq
import numpy as np
import pytesseract
import requests
from PIL import Image, ImageOps
from fuzzywuzzy import fuzz
from odoo import _,fields,models,api
from odoo.exceptions import UserError
from pdf2image import convert_from_bytes
from pypdf import PdfReader


GROQ_API_KEY="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"
DEFAULT_OLG_ENDPOINT = 'https://olg.api.odoo.com'
_logger = logging.getLogger(__name__)


class SaleDigitalize(models.TransientModel):
    _name = 'sale.digitalize'
    _description = 'Digitalizar Factura'

    file = fields.Binary(string='Attach file', required=True)
    attachment_id = fields.Many2one('ir.attachment', string='Adjuntar Archivo')
    filename = fields.Char(string='Nombre de Archivo')
    create_partner = fields.Boolean(string='Create Partner?', default=True)
    create_product = fields.Boolean(string='Create Product?', default=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    match_product = fields.Boolean(string='Try Match Product?', default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')

    @api.onchange('create_partner')
    def _onchange_create_partner(self):
        if not self.create_partner:
            po_ids = self.env.context.get('active_ids')[0]
            purchase_order = self.env['sale.order'].browse(po_ids)
            self.partner_id = purchase_order.partner_id
        else:
            self.partner_id = False

    def act_accept(self):
        if self.file:
            id = self.env.context.get('active_ids', [])
            if id:
                sale_order = self.env['sale.order'].browse(id)
            else:
                partner_id = self.env['res.partner'].search([], limit=1)
                sale_order = self.env['sale.order'].create(
                    {'partner_id': partner_id.id, 'company_id': self.env.company.id})
            self.attachment_id = self.env['ir.attachment'].create({
                    'name': self.filename,
                    'datas': self.file,
                    'res_model': 'sale.order',
                    'res_id': id[0] if id else False,
                    'type': 'binary'
                })


            system_prompt = self._prompt_rules()
            user_prompt = self._prompt_context()
            conversation_history = [{'role': 'system', 'content': system_prompt}]
            response = self.generate_text_llm(user_prompt, conversation_history)
            try:
                response_dict = json.loads(response)
            except json.decoder.JSONDecodeError:
                fixed_json = self._fix_json(response)
                response_dict = json.loads(fixed_json)

            partner_id = self._get_partner_from_response(response_dict)
            line_ids = self._get_sale_order_lines(response_dict)
            ref = response_dict.get('reference') or response_dict.get('reference') or response_dict.get(
                'document_number')

            #due_date el dia de hoy
            due_date =  fields.Date.today()
            sale_date = fields.Date.today()
            try:
                due_date = fields.Date.to_string(fields.Date.to_date(response_dict.get('due_date')))
            except:
                due_date =fields.Date.today()

            try:
                sale_date = fields.Date.to_string(fields.Date.to_date(response_dict.get('sale_date')))
            except:
                sale_date = fields.Date.today()

            extracted_values = {
                'client_order_ref': str(ref),
                'date_order': sale_date,
                'validity_date': due_date,
                'order_line': line_ids,
                'note': response_dict.get('notes'),
            }
            if partner_id:
                extracted_values['partner_id'] = partner_id.id

            sale_order.write(extracted_values)
            return sale_order

    def _prompt_context(self):
        attachment_data = ''
        content = base64.b64decode(self.attachment_id.with_context(bin_size=False).datas)
        f = io.BytesIO(content)
        if 'pdf' in self.attachment_id.mimetype:
            parsed_data = self._get_text_pdf(f)
            if parsed_data == '':
                images = convert_from_bytes(content, dpi=300)
                for image in images:
                    parsed_data += self._image2text(image)
            attachment_data += f'--- {parsed_data} --- '
        elif 'image' in self.attachment_id.mimetype:
            attachment_data += f'--- {self._image2text(f)} --- '
        return " ".join(attachment_data.split())

    def _get_text_pdf(self, f):
        parsed_data = ''
        reader = PdfReader(f)
        for page in reader.pages:
            parsed_data += page.extract_text()

        return parsed_data

    def data_segmentation(self, img):
        """
        Function to do segmentation for the retrieved data after converting it
        into image.
        :param img: The image format of the document that need to undergo the
        segmentation procedure.
        :return: The segments of the image.
        """
        img = ImageOps.grayscale(img)
        img = img.point(lambda x: 255 if x > 176 else 0, '1')
        img_rgb = ImageOps.invert(img.convert("RGB"))
        segments = []
        segment_bounds = img_rgb.getbbox()
        while segment_bounds:
            segment = img_rgb.crop(segment_bounds)
            if segment.size[0] > 0 and segment.size[1] > 0:
                segments.append(segment)
            img_rgb = ImageOps.crop(img_rgb, segment_bounds)
            segment_bounds = img_rgb.getbbox()
        return segments

    def _image2text(self, f):

        try:
            img = Image.open(f)
        except AttributeError:
            img = f

        if img.info.get('dpi', (0, 0)) == (0, 0):
            img.info['dpi'] = (300, 300)  # Set to 300 DPI for better OCR accuracy

        # Convert to grayscale if it's a color image
        data_segmentation = self.data_segmentation(img)

        # Get available languages
        langs = '+'.join(pytesseract.get_languages())

        # Perform OCR on the temporary file
        custom_config = f'--psm 6 --oem 3 -l {langs}'
        text = ''
        for segment in data_segmentation:
            text = pytesseract.image_to_string(segment, config=custom_config)

        return text.strip()

    def _generate_system_prompt(self, ):
        partner_type, document_type, company_type = False, False, False
        sale_type_line = 'vendor', 'bill', 'customer'

        if all([partner_type, document_type, company_type]):
            sale_type_line = f"""The record pertains to {partner_type} {document_type} directed to {company_type} {self.env.company.name}. You'll discover information about the {partner_type} (partner) and its specifics. Exercise caution to avoid conflating vendor and customer details."""

        prompt = f"""You are an sale order digitizer.
        I will receive content extracted through OCR from a document.
        The content will undergo an initial check to identify and rectify errors introduced by OCR.
        Subsequently, relevant values will be extracted and used to populate the JSON structure below.
        {sale_type_line}
        Fill the values in the json with the right data types
        Do not add any explanations and ``` tags.
        Just furnish a JSON object that is valid and conforms to the specified structure.
        """ + """
        {
             "partner": {
                "name": "String",
                "vat_id": "String"
                "email": "String"
             },
             "reference": "String",
             "document_number": "String",
             "sale_date": "YYYY-MM-DD",
             "due_date": "YYYY-MM-DD",
             "sale_order_lines": [
                 {
                     "product": "String",
                     "quantity": Float,
                     "price_unit": Float,
                     "discount": Float,
                     "tax_rate": Float,
                 },
             ],
             "notes": "String"
        }
        """

        return " ".join(prompt.split())

    def _fix_json(self, json_data):
        system = """JSON Fixing Tool: Correct JSON Errors Given a JSON string with mistakes causing """ + \
                 """JSONDecodeError, fix it and respond with a valid JSON. Ensure compliance with RFC8259 """ + \
                 """standards, checking for issues like trailing commas, special characters, and extra """ + \
                 """characters. Do not add explanations or ``` tags. Only provide a correctly formatted JSON object.
                 """
        return self.generate_text_olg_api(system, json_data)

    def _get_partner_from_response(self, response_dict):
        partner_dict = response_dict.get('partner', {})
        name = partner_dict.get('name')
        vat = partner_dict.get('vat_id')
        email = partner_dict.get('email')
        if email and email.strip() != self.env.company.email.strip() and email.strip() not in [x.email.strip() for x in
                                                                                               self.env[
                                                                                                   'res.users'].search(
                                                                                                   [])]:
            email = False

        # Build domain for searching
        domain = [('name', '=', name)] if name else \
            [('email', '=', email)] if email else \
                [('vat', '=', vat)] if vat else []
        # Search for partner using the domain
        partner_id = self.env['res.partner'].search(domain, limit=1)
        # If multiple conditions are provided, refine the search
        if len(partner_id) > 1:
            refined_domain = domain + [('vat', '=', vat)] if vat else domain
            partner_id = self.env['res.partner'].search(refined_domain, limit=1)
        if not partner_id:
            all_partner_ids = self.env['res.partner'].search([])
            threshold_similarity = 80
            filtered_partner = [
                partner for partner in all_partner_ids
                if name and partner.name and fuzz.ratio(name, partner.name) >= threshold_similarity
            ]
            if filtered_partner:
                # Si hay al menos una coincidencia que cumple con el umbral, toma la primera como mejor coincidencia
                partner_id = filtered_partner[0]

        if not partner_id and not self.create_partner:
            partner_id = self.partner_id

        if not partner_id and self.create_partner and name:
            partner_id = self.env['res.partner'].create({
                'name': name,
                'vat': vat if vat else False,
                'email': email if email else False
            })
        return partner_id

    def _get_sale_order_lines(self, response_dict):
        line_ids = []
        for line in response_dict.get('sale_order_lines', []):
            quantity = float(line.get('quantity', 0)) if line.get('quantity') else 0
            price_unit = float(line.get('price_unit', 0)) if line.get('price_unit') else 0
            discount = float(line.get('discount', 0)) if line.get('discount') else 0
            vat_rate = float(line.get('tax_rate', 0)) if line.get('tax_rate') else 0
            type_tax_use = 'sale'
            # Use domain instead of multiple search calls
            tax_domain = [('type_tax_use', '=', type_tax_use), ('amount', '=', vat_rate), ('amount', '!=', 0.0),
                          ('active', '=', True)]
            tax_id = self.env['account.tax'].search(tax_domain, limit=1) if vat_rate else False
            all_product_ids = self.env['product.product'].search([])

            best_match_product = False
            if self.match_product:
                all_product_ids = self.env['product.product'].search([])
                if all_product_ids:
                    product_name_from_response = line.get('product')
                    threshold_similarity = 80
                    filtered_products = [
                        product for product in all_product_ids
                        if fuzz.ratio(product_name_from_response, product.name) >= threshold_similarity
                    ]
                    if filtered_products:
                        # Si hay al menos una coincidencia que cumple con el umbral, toma la primera como mejor coincidencia
                        best_match_product = filtered_products[0]

            if not best_match_product and self.create_product:
                product_template = self.env['product.template'].create({
                    'name': line.get('product'),
                    'list_price': price_unit,
                })
                best_match_product = product_template.product_variant_id

            line_ids.append((0, 0, {
                'product_id': best_match_product.id if best_match_product else False,
                'name': line.get('product'),
                'product_uom_qty': quantity,
                'price_unit': price_unit,
                'discount': discount,
                'tax_ids': tax_id and [(6, 0, tax_id.ids)]  # Convert to Odoo format
            }))

        return line_ids

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def generate_text_olg_api(self, prompt, conversation_history=[]):
        try:
            IrConfigParameter = self.env['ir.config_parameter'].sudo()
            olg_api_endpoint = IrConfigParameter.get_param('web_editor.olg_api_endpoint', DEFAULT_OLG_ENDPOINT)
            response = self.iap_jsonrpc(olg_api_endpoint + "/api/olg/1/chat", params={
                'prompt': prompt,
                'conversation_history': conversation_history or [],
                'version': "17.0",
            }, timeout=30)
            if response['status'] == 'success':
                return response['content']
            elif response['status'] == 'error_prompt_too_long':
                raise UserError(_("Sorry, your prompt is too long. Try to say it in fewer words."))
            else:
                raise UserError(_("Sorry, we could not generate a response. Please try again later."))
        except UserError:
            raise UserError(_("Oops, it looks like our AI is unreachable!"))

    def iap_jsonrpc(self, url, method='call', params=None, timeout=15):
        """
        Calls the provided JSON-RPC endpoint, unwraps the result and
        returns JSON-RPC errors as exceptions.
        """

        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': uuid.uuid4().hex,
        }

        _logger.info('iap jsonrpc %s', url)
        try:
            req = requests.post(url, json=payload, timeout=timeout)
            req.raise_for_status()
            response = req.json()
            _logger.info("iap jsonrpc %s answered in %s seconds", url, req.elapsed.total_seconds())
            if 'error' in response:
                name = response['error']['data'].get('name').rpartition('.')[-1]
                message = response['error']['data'].get('message')
                if name == 'InsufficientCreditError':
                    e_class = UserError
                elif name == 'AccessError':
                    e_class = UserError
                elif name == 'UserError':
                    e_class = UserError
                else:
                    raise requests.exceptions.ConnectionError()
                e = e_class(message)
                e.data = response['error']['data']
                raise e
            return response.get('result')
        except (
                ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema,
                requests.exceptions.Timeout,
                requests.exceptions.HTTPError) as e:
            raise UserError(
                _('The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was %s',
                  url)
            )


    def generate_text_llm(self, prompt, conversation_history=[]):
        client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        chat_completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            response_format={"type": "json_object"},
            messages=[*conversation_history, {"role": "user", "content": prompt}],
        )

        return chat_completion.choices[0].message.content


    def _prompt_rules(self):
        partner_type, document_type, company_type = False, False, False
        sale_type_line = 'vendor', 'bill', 'customer'

        if all([partner_type, document_type, company_type]):
            sale_type_line = f"""The record pertains to {partner_type} {document_type} directed to {company_type} {self.env.company.name}. You'll discover information about the {partner_type} (partner) and its specifics. Exercise caution to avoid conflating vendor and customer details."""

        return f"""
            You are a sale order digitizer.

            CRITICAL RULE:
            - If no product lines are found in the document, return "sale_order_lines": []
            - Do NOT create placeholder or empty product lines

            STRICT RULES (VIOLATION = FAILURE):
            - Output MUST be valid JSON
            - Output MUST match the schema EXACTLY
            - Do NOT add, rename, or remove keys
            - Do NOT include explanations, markdown, or comments
            - Do NOT calculate totals
            - Do NOT infer missing data
            - Use correct JSON data types only
            - Numbers must be numbers, not strings
            - Missing values must be null, empty string, or 0.0
            - Ignore SKUs, descriptions, bracketed codes, and marketing text
            - Product name must be the main item title only

            SCHEMA (LOCKED):
            - partner.name: String
            - partner.vat_id: String
            - partner.email: String | null
            - reference: String
            - document_number: String
            - sale_date: String (YYYY-MM-DD)
            - due_date: String | null
            - sale_order_lines[].product: String
            - sale_order_lines[].quantity: Float
            - sale_order_lines[].price_unit: Float
            - sale_order_lines[].discount: Float
            - sale_order_lines[].tax_rate: Float
            - notes: String


            EXTRACTION RULES:
            - Partner name: company name in billing address
            - VAT ID: value after "Tax ID:"
            - Reference & document_number: value after "Order #"
            - Sale date: value after "Order Date", convert to YYYY-MM-DD
            - Each product line appears under Description / Quantity / Unit Price
            - Quantity is the numeric value before "Units" or "Hours"
            - Unit price is the numeric value after "$"
            - Tax rate is the percentage shown (default 0.0 if not present)
            - Discount is always 0.0 unless explicitly mentioned

            TASK:
            Extract sale order data from the OCR text and populate the JSON.

            OCR CONTENT:
            {sale_type_line}

            OUTPUT JSON (Use the schema above to fill the JSON. Keep types strictly as indicated, Return valid JSON only.):
            {{
            "partner": {{
                "name": "",
                "vat_id": "",
                "email": ""
            }},
            "reference": "",
            "document_number": "",
            "sale_date": "",
            "due_date": "",
            "sale_order_lines": [
                {{
                "product": "",
                "quantity": 0.0,
                "price_unit": 0.0,
                "discount": 0.0,
                "tax_rate": 0.0
                }}
            ],
            "notes": ""
            }}
        """
