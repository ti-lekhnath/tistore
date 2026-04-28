/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { registry } from "@web/core/registry";
import { ReceiptScreen } from '@point_of_sale/app/screens/receipt_screen/receipt_screen';
import { useErrorHandlers, useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { InvoiceTemplate } from "@ti_pos_invoice/app/invoice/invoice_template";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";


class ReceiptInvoice extends ReceiptScreen {
    static template = "point_of_sale.ReceiptScreen";
    static components = { OrderReceipt };
    static props = { orderUuid: { type: String } };


    setup() {
        super.setup();
        console.log(this.templ)
        this.doPrintInvoice = useTrackedAsync(() =>
            this.printInvoice({ order: this.currentOrder })
        );
    }

    async printInvoice(order) {
        console.log("Print Invoice")
    }
}



registry.category("pos_pages").add("ReceiptInvoice", {
    name: "ReceiptInvoice",
    component: ReceiptInvoice,
    route: `/pos/ui/${odoo.pos_config_id}/receipt/{string:orderUuid}`,
    params: {
        orderUuid: true,
        orderFinalized: true,
    },
});
