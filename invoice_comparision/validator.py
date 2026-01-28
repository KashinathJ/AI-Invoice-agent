import json
from datetime import datetime
from typing import List, Dict, Tuple, Union
from logger import ActivityLogger
import json


class InvoicePOValidator:
    def __init__(self, user: str = "system"):
        self.logger = ActivityLogger(agent_name="invoice_mismatch")
        self.user = user
        self.doc_type = ""

    def address_compare(self, category: str, contract: Dict, invoice: Dict) -> Dict:
        ROUTE_KEY = {
            "PO": "PO_value",
            "Contract": "Contract"
        }

        mismatches = {
            "Issue_category": category,
            f"{category}": {

            }
        }
        flag: int = 0

        for key in set(contract) | set(invoice):  # union of keys
            if contract.get(key) != invoice.get(key):
                flag = 1
                mismatches[category][key] = {ROUTE_KEY[self.doc_type]: contract.get(key), 'Invoice': invoice.get(key)}

        return mismatches if flag else None

    def missing_len(self, mismatch_data: Dict) -> int:
        count = 0
        for item in mismatch_data:
            category = item["Issue_category"]
            data = item[category]
            count = len(data) + count
        return count

    def MismatchProduct_details(self, Invoice_data, PO_data):
        mismatches = {
            "mismatch_len": 0,
            "mismatches": [],
        }

        invoice_products = {p["PRODUCT_DESCRIPTION"]: p for p in Invoice_data["product"]}
        po_products = {p["PRODUCT_DESCRIPTION"]: p for p in PO_data["product"]}

        # Compare only if product exists in both
        for desc in invoice_products.keys() & po_products.keys():
            inv_prod = invoice_products[desc]
            po_prod = po_products[desc]
            field_diffs = {}

            for key in inv_prod.keys():
                if key in po_prod and inv_prod[key] != po_prod[key]:
                    field_diffs[key] = {
                        "Invoice": inv_prod[key],
                        "PO_value": po_prod[key]
                    }

            if field_diffs:
                mismatches["mismatches"].append({
                    "Issue_category": desc,
                    desc: field_diffs,
                })
        return mismatches

    def validate_po(self, po_data, invoice_data) -> Tuple[bool, List[Dict]]:
        self.doc_type = "PO"
        log_dict = {
            "user_id": self.user,
            "invoice_filename": invoice_data.get("invoice_number", ""),
            "invoice_number": invoice_data.get("invoice_number", ""),
            "compared_document_type": self.doc_type,
            "compared_document_name": po_data.get("po_number", ""),
        }

        mismatch_data = []

        po_shop_address = po_data["shop_address"]
        po_billing_address = po_data["billing_address"]

        invoice_shop_address = invoice_data["shop_address"]
        invoice_billing_address = invoice_data["billing_address"]

        missing_shop_address = self.address_compare("seller_address", po_shop_address, invoice_shop_address)
        missing_billing_address = self.address_compare("buyer_address", po_billing_address, invoice_billing_address)

        product_mismatch_data = self.MismatchProduct_details(invoice_data, po_data)

        if missing_shop_address is not None:
            product_mismatch_data["mismatches"].append(missing_shop_address)

        if missing_billing_address is not None:
            product_mismatch_data["mismatches"].append(missing_billing_address)

        print("----------------product mismatch_data")
        print(product_mismatch_data)
        print("-" * 90)

        vendor_name = invoice_data.get('shop_address', {}).get('name', 'Unknown Vendor')
        po_items_map = {
            item['PRODUCT_DESCRIPTION'].upper(): item for item in po_data['product']
        }
        invoice_product_data = invoice_data['product']

        for inv in invoice_product_data:
            item_name = inv['PRODUCT_DESCRIPTION'].upper()
            if item_name not in po_items_map:
                mismatch_data.append({
                    "Issue": f"Item not found in PO",
                    "Item": inv['PRODUCT_DESCRIPTION'],
                })
                continue

            po_item = po_items_map[item_name]
            quantity_po = float(po_item['COUNT'])
            quantity_invoice = float(inv['COUNT'])
            rate_po = float(po_item['UNIT_ITEM_PRICE'])
            rate_invoice = float(inv['UNIT_ITEM_PRICE'])

            # print(quantity_po, quantity_invoice, rate_po, rate_invoice)
            if quantity_po != quantity_invoice or rate_po != rate_invoice:
                mismatch_data.append({
                    "Issue": "Mismatch in quantity or rate",
                    "Item": inv['PRODUCT_DESCRIPTION'],
                    "Quantity PO": quantity_po,
                    "Quantity Invoice": quantity_invoice,
                    "Rate PO": rate_po,
                    "Rate Invoice": rate_invoice,
                    "Total Amount PO": quantity_po * rate_po,
                    "Total Amount Invoice": quantity_invoice * rate_invoice
                })

        mismatch_count = len(mismatch_data)
        log_dict["mismatch_count"] = mismatch_count
        log_dict["event_dts"] = datetime.now()
        log_dict["status"] = "Success"
        log_dict["Vendor_Name"] = vendor_name

        is_mismatch = mismatch_count > 0
        if is_mismatch:
            log_dict["outcome"] = "Mismatch"
            log_dict[
                "comments"] = f"{mismatch_count} mismatches found for {invoice_data.get('invoice_number')}. Details: {mismatch_data}"
        else:
            log_dict["outcome"] = "No Mismatch"
            log_dict["comments"] = f"No mismatches found for {invoice_data.get('invoice_number')}."

        log_id = self.logger.insert_log(log_dict)

        self.logger.insert_fields(self.doc_type, log_id, product_mismatch_data)

        return is_mismatch, mismatch_data, vendor_name

    def validate_contract(self, contract_data, invoice_data) -> Tuple[bool, List[Dict]]:
        self.doc_type = "Contract"
        log_dict = {
            "mismatch_count": 0,
            "user_id": self.user,
            "invoice_filename": invoice_data.get("invoice_number", ""),
            "invoice_number": invoice_data.get("invoice_number", ""),
            "compared_document_type": self.doc_type,
            "compared_document_name": contract_data.get("contract_number", ""),
            "outcome": "No Mismatch",
        }
        mismatch_data = {
            "mismatch_len": 0,
            "mismatches": []
        }
        vendor_name = invoice_data.get('shop_address', {}).get('name', 'Unknown Vendor')

        contract_id = str(contract_data.get("contract_number", "")).strip()
        invoice_contract_id = str(invoice_data.get("contract_number", "")).strip()

        if contract_id != invoice_contract_id:
            log_dict["mismatch_count"] = log_dict["mismatch_count"] + 1
            log_dict["event_dts"] = datetime.now()
            log_dict["status"] = "Success"
            log_dict["outcome"] = "Mismatch"
            log_dict[
                "comments"] = f"The contract number, {contract_id}, in 'contract_doc' does not match the contract number, {invoice_contract_id}, in the invoice."
            mismatch_data["mismatches"].append({
                "Issue_category": f"Contract Number",
                "Contract Number": [{
                    f"Contract": contract_id,
                    f"Invoice": invoice_contract_id,
                }],
            })

            return True, mismatch_data, vendor_name

        milestone = invoice_data.get("milestone", "").strip().lower()
        schedule = contract_data.get("payment_terms", {}).get("payment_schedule", [])
        milestone_match = next((s for s in schedule if s["milestone"].strip().lower() == milestone), None)

        if not milestone_match:
            log_dict["mismatch_count"] = log_dict["mismatch_count"] + 1
            log_dict["event_dts"] = datetime.now()
            log_dict["status"] = "Success"
            log_dict["outcome"] = "Mismatch"
            log_dict["comments"] = f"Milestone '{milestone}' not found in contract payment schedule."

            mismatch_data["mismatches"].append({
                "Issue_category": f"Milestone",
                "Milestone": {
                    f"Contract": milestone_match,
                    f"Invoice": milestone,
                },
            })
        else:
            expected_percent = float(milestone_match["percentage"])
            total_contract_value = float(contract_data["total_contract_value"])
            expected_amount = round((expected_percent / 100) * total_contract_value, 2)
            invoice_total = round(float(invoice_data["total_bill"]["final_total"]), 2)

            if invoice_total != expected_amount:
                log_dict["mismatch_count"] = log_dict["mismatch_count"] + 1
                log_dict["event_dts"] = datetime.now()
                log_dict["status"] = "Success"
                log_dict["outcome"] = "Mismatch"
                log_dict[
                    "comments"] = f"Invoice total {invoice_total} does not match expected amount {expected_amount} for milestone '{milestone}'."

                mismatch_data["mismatches"].append({
                    "Issue_category": "Billing",
                    "Billing": {
                        str(milestone): {
                            "Contract": expected_amount,
                            "Invoice": invoice_total,
                        },
                    }
                }
                )

        Contract_seller_address = contract_data.get("seller_address", {})
        Contract_buyer_address = contract_data.get("buyer_address", {})

        invoice_shop_address = invoice_data.get("shop_address", {})
        invoice_billing_address = invoice_data.get("billing_address", {})

        missing_shop_address = self.address_compare("seller_address", Contract_seller_address, invoice_shop_address)
        missing_billing_address = self.address_compare("buyer_address", Contract_buyer_address, invoice_billing_address)

        if missing_shop_address:
            log_dict["mismatch_count"] = log_dict["mismatch_count"] + 1
            mismatch_data["mismatches"].append(missing_shop_address)

        if missing_billing_address:
            log_dict["mismatch_count"] = log_dict["mismatch_count"] + 1
            mismatch_data["mismatches"].append(missing_billing_address)

        mismatch_category = [mismatch["Issue_category"] for mismatch in mismatch_data["mismatches"]]
        # missing_len = self.missing_len(mismatch_data["mismatches"])

        # log_dict["mismatch_count"] = max(log_dict["mismatch_count"], missing_len)
        log_dict["mismatch_count"] = max(log_dict["mismatch_count"], 0)
        log_dict["event_dts"] = datetime.now()
        log_dict["status"] = "Success"
        log_dict["outcome"] = "Mismatch"
        log_dict["comments"] = f"Mismatch category: {mismatch_category}"
        log_dict["Vendor_Name"] = vendor_name

        is_mismatch = len(mismatch_data) > 0

        log_id = self.logger.insert_log(log_dict)

        self.logger.insert_fields(self.doc_type, log_id, mismatch_data)

        return is_mismatch, mismatch_data, vendor_name

    def validate_invoice(self, invoice_data: Dict, po_data: Dict = None, contract_data: Dict = None) -> Tuple[
        bool, List[Dict]]:
        vendor_name = invoice_data.get('shop_address', {}).get('name', 'Unknown Vendor')
        contract_id = invoice_data.get("contract_number", "").strip()
        po_number = invoice_data.get("po_number", "").strip()

        if contract_id and contract_id.upper() != "NULL":
            if not contract_data:
                log_dict = {
                    "user_id": self.user,
                    "invoice_filename": invoice_data.get("invoice_number", ""),
                    "compared_document_type": "Contract",
                    "compared_document_name": contract_id,
                    "status": "Error",
                    "event_dts": datetime.now(),
                    "comments": f"Contract file not provided for contract_id: {contract_id}",
                }
                self.logger.insert_log(log_dict)
                return True, [{"Issue": f"Contract file not provided for contract_id: {contract_id}"}], vendor_name
            return self.validate_contract(contract_data, invoice_data)

        if po_number and po_number.upper() != "NULL":
            if not po_data:
                log_dict = {
                    "user_id": self.user,
                    "invoice_filename": invoice_data.get("invoice_number", ""),
                    "compared_document_type": "PO",
                    "compared_document_name": po_number,
                    "status": "Error",
                    "event_dts": datetime.now(),
                    "comments": f"PO file not provided for po_number: {po_number}",
                }
                self.logger.insert_log(log_dict)
                return True, [{"Issue": f"PO file not provided for po_number: {po_number}"}], vendor_name
            return self.validate_po(po_data, invoice_data)

        log_dict = {
            "user_id": self.user,
            "invoice_filename": invoice_data.get("invoice_number", ""),
            "status": "Error",
            "event_dts": datetime.now(),
            "comments": "Neither valid contract_number nor po_number provided in invoice.",
        }
        self.logger.insert_log(log_dict)
        return True, [{"Issue": "Neither valid contract_number nor po_number provided in invoice."}], vendor_name


if __name__ == "__main__":
    validator = InvoicePOValidator()
    with open("US_Sample_Invoice.json", "r") as f:
        invoice_data = json.load(f)
    with open("US_Sample_Contract.json", "r") as f:
        contract_data = json.load(f)
    print("----------------------------data is: ")
    print(validator.validate_invoice(invoice_data=invoice_data, contract_data=contract_data))

    # with open("Sample_Invoice (1).json", "r") as f:
    #     invoice_data = json.load(f)
    # with open("Sample_Purchase_Order (1).json", "r") as f:
    #     po_data = json.load(f)
    # validator.validate_invoice(invoice_data=invoice_data, po_data=po_data)

    # with open("Sample_Purchase_Order.json", "r") as f:
    #     po_data = json.load(f)

    # print(validator.validate_invoice(invoice_data=invoice_data, po_data=po_data))
    # validator.logger.fetch_logs_from_table()
