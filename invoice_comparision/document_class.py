from typing import List
from pydantic import BaseModel, Field, conint
from datetime import date


# Define Pydantic models
class Shop_Address(BaseModel):
    name: str = Field(description="the name of the seller")
    address_line: str = Field(description="the address of the seller")
    city: str = Field(description="the city portion of the seller")
    state_province_code: str = Field(description="the state portion of the seller")
    postal_code: int = Field(description="the postal code portion of the seller address")


class Address(BaseModel):
    name: str = Field(description="the name of person or organization")
    address_line: str = Field(
        description="local delivery information such as street, building number, PO box, or apartment")
    city: str = Field(description="the city portion of the address")
    state_province_code: str = Field(description="the state code for US addresses")
    postal_code: int = Field(description="the postal code of the address")


class Product(BaseModel):
    PRODUCT_DESCRIPTION: str = Field(
        description="take the complete description of the product or service into conideration. do not leave anything")
    HSN: str = Field(
        description='HSN Code. if the value is '' then please say "same as above". If the Column is not there just show Null')
    MRP: float = Field(
        description='MRP Price. if the value is '' then set the value as 0. If the Column is not there just show Null')
    GROSS_AMOUNT: float = Field(
        description='Gross AMount. if the value is '' then set the value as 0. If the Column is not there just show Null')
    DISCOUNT_RATE: float = Field(
        description='DIscount Rate. if the value is '' then set the value as 0. If the Column is not there just show Null')
    CGST_RATE: float = Field(
        description='CGST Rate. if the value is '' then set the value as 0. If the Column is not there just show Null')
    CGST_AMOUNT: float = Field(
        description='CGST Amount. if the value is '' then set the value as 0. If the Column is not there just show Null')
    SGST_RATE: float = Field(
        description='SGST Rate. if the value is '' then set the value as 0. If the Column is not there just show Null')
    SGST_AMOUNT: float = Field(
        description='SGST Amount. if the value is '' then set the value as 0. If the Column is not there just show Null')
    COUNT: int = Field(description="number of units bought for the product")
    GST_RATE: float = Field(
        description='GST Rate. if the value is '' then set the value as 0. If the Column is not there just show Null')

    GST_AMOUNT: float = Field(
        description='GST Amount. if the value is '' then set the value as 0. If the Column is not there just show Null')
    UNIT_ITEM_PRICE: float = Field(description="price per unit")
    PRODUCT_TOTAL_PRICE: float = Field(description="the total price, calculated as count * unit_item_price")
    TAXABLE_AMOUNT: float = Field(description="the total price after Discount_AMOUNT")
    NET_AMOUNT: float = Field(description="the total price after adding CGST_AMOUNT and SGST_AMOUNT")


class TotalBill(BaseModel):
    total: float = Field(description="the total amount before tax and delivery charges")
    discount_amount: float = Field(description="discount amount is total cost * discount %")
    tax_amount: float = Field(description="tax amount is tax_percentage * (total - discount_amount)")
    delivery_charges: float = Field(description="the cost of shipping products")
    final_total: float = Field(description="the total price after tax, delivery charges, and discounts")


class Milestone(BaseModel):
    milestone: str = Field(
        description="Name of the payment milestone (e.g., 'advance', 'mid-project', 'final').It should be a single word and in lower case.")
    percentage: conint(ge=0, le=100) = Field(
        description="Percentage of the total contract value to be paid at this milestone (0–100).")


class PaymentTerms(BaseModel):
    total_contract_value: float = Field(description="Total value of the contract in the relevant currency.")
    payment_schedule: List[Milestone] = Field(
        description="Details of the payment terms, including milestones and their percentages.")


class Invoice(BaseModel):
    invoice_number: str = Field(description="extraction of relevant information from invoice")
    po_number: str = Field(
        description="identification number of the corresponding purchase order.if the value is '' then set the value as 'NULL'.")
    contract_number: str = Field(
        description="identification number of the corresponding contract.if the value is '' then set the value as 'NULL'.")
    shop_address: Shop_Address = Field(description="who has generated the bill")
    billing_address: Address = Field(description="where the bill for the product or service is sent")
    product: List[Product] = Field(description="details of the billed products")
    milestone: str = Field(
        description="Name of the payment milestone (e.g., 'advance', 'mid-project', 'final').It should be a single word and in lower case.")
    total_bill: TotalBill = Field(description="details of the total amount, discounts, and taxes")


class PO(BaseModel):
    po_number: str = Field(description="extraction of relevant information from purchase order")
    shop_address: Shop_Address = Field(description="who has generated the purchase order")
    billing_address: Address = Field(description="where the purchase order for the product or service is sent")
    product: List[Product] = Field(description="details of the billed products")
    total_bill: TotalBill = Field(description="details of the total amount, discounts, and taxes")


class Contract(BaseModel):
    contract_number: str = Field(description="Unique identifier for the contract")
    seller_address: Shop_Address = Field(description="The address of the seller involved in the contract")
    buyer_address: Address = Field(description="The address of the buyer involved in the contract")
    start_date: date = Field(description="The start date of the contract's validity")
    end_date: date = Field(description="The end date of the contract's validity")
    terms: str = Field(description="The terms and conditions outlined in the contract")
    total_contract_value: float = Field(description="The total agreed value for the contract")
    payment_terms: PaymentTerms = Field(description="The payment terms agreed upon in the contract")
