"""
Pydantic models for Green Mountain Energy utility bill extraction
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Provider(BaseModel):
    name: str = Field(description="The name of the utility provider, e.g., 'Green Mountain Energy'.")
    country: str = Field(description="The country where the provider operates, e.g., 'US'.")

class BaseAddress(BaseModel):
    streetLine1: Optional[str] = Field(default=None, description="The primary street address line.")
    city: Optional[str] = Field(default=None, description="The city of the address.")
    state: Optional[str] = Field(default=None, description="The state or province of the address.")
    postalCode: Optional[str] = Field(default=None, description="The postal or ZIP code.")
    country: str = Field(description="The country of the address, e.g., 'US'.")

class BillingAddress(BaseAddress):
    addressType: str = Field(default="MAILING")
    recipient: Optional[str] = Field(description="The name of the person or company receiving the bill.")

class ServiceAddress(BaseAddress):
    addressType: str = Field(default="SERVICE")

class MeterCharge(BaseModel):
    # This model remains generic but the data passed to it must be separate items
    chargeNameAsPrinted: str = Field(description="The description of the charge (e.g., 'Energy Charge', 'PUC Charge', 'GRT Reimburse').")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")

class MeterUsage(BaseModel):
    periodStartDate: Optional[str] = Field(description="Start date of the billing period for this meter, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="End date of the billing period for this meter, in YYYY-MM-DD format.")
    measuredUsage: Optional[float] = Field(description="The total usage for this period.")
    usageUnit: Optional[str] = Field(description="The unit of usage, e.g., 'kWh'.")
    numberOfDaysInPeriod: Optional[int] = Field(description="The number of days in this billing period.")

class MeterData(BaseModel):
    serviceType: str = Field(description="Type of utility service, e.g., 'ELECTRICITY'.")
    serviceAddress: ServiceAddress
    meterNumber: Optional[str] = Field(description="The meter number for this service.")
    esiid: Optional[str] = Field(description="The ESIID number for this service.")
    periodStartDate: Optional[str] = Field(description="Start date of the billing period, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="End date of the billing period, in YYYY-MM-DD format.")
    totalUsage: Optional[float] = Field(description="The total usage for this meter, e.g., 412.0.")
    totalUsageUnit: Optional[str] = Field(description="The unit for total usage, e.g., 'kWh'.")
    charges: Optional[List[MeterCharge]] = Field(description="A list of all detailed charges for this meter (Energy Charge, TDSP Charges, etc.).")
    usages: List[MeterUsage] = Field(description="A list containing the usage details for this meter.")

class AccountData(BaseModel):
    accountNumber: str = Field(description="The main account number for the customer (e.g., 008 000137815-9).")
    billingAddress: BillingAddress
    periodStartDate: Optional[str] = Field(description="The earliest service period start date found on the bill, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="The latest service period end date found on the bill, in YYYY-MM-DD format.")
    dueDate: str = Field(description="The date the payment is due, in YYYY-MM-DD format.")
    statementDate: str = Field(description="The date the bill was issued, in YYYY-MM-DD format.")
    outstandingBalance: Optional[float] = Field(description="The total amount due for this account.")
    currencyCode: str = Field(default="USD")
    totalCharges: float = Field(description="The total of *current* charges for this account.")
    meterData: List[MeterData] = Field(description="A list of all detailed meter/service breakdowns for this account.")

class RootChargeItem(BaseModel):
    chargeNameAsPrinted: str = Field(description="The description of the charge as printed on the bill (e.g., 'Energy Charge', 'TDSP Charges').")
    chargeType: str = Field(default="DEBIT")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")
    chargeCurrencyCode: str = Field(default="USD")

class Payment(BaseModel):
    paymentDate: str = Field(description="The date the payment was received, in YYYY-MM-DD format.")
    paymentAmount: float = Field(description="The amount of the payment (should be a positive number).")

class PaymentCoupon(BaseModel):
    amountDue: Optional[float] = Field(description="The amount due shown on the coupon.")
    afterDueDateAmount: Optional[float] = Field(default=None, description="The increased amount due if paid after the due date, extracted from the coupon or summary table.")
    dueDate: Optional[str] = Field(description="The due date shown on the coupon, in YYYY-MM-DD format.")
    remitToAddress: Optional[BaseAddress] = Field(description="The address to mail payments to.")
    scanline: Optional[str] = Field(description="The long string of numbers at the bottom of the coupon.")

class BalanceAdjustment(BaseModel):
    chargeNameAsPrinted: str = Field(description="The description of the financial item (e.g., 'Late Payment Penalty', 'Disconnect Notice Fee').")
    chargeType: str = Field(description="The type of transaction, typically 'DEBIT' for penalties/fees.")
    chargeAmount: float = Field(description="The monetary value of this item.")
    chargeCurrencyCode: str = Field(default="USD")

class UtilityBillExtraction(BaseModel):
    type: str = Field(default="UtilityBillExtraction")
    provider: Provider
    currencyCode: str = Field(default="USD")
    statementDate: str = Field(description="The main billing date of the statement, in YYYY-MM-DD format.")
    previousStatementDate: Optional[str] = Field(default=None)
    dueDate: str = Field(description="The main due date, in YYYY-MM-DD format.")
    periodStartDate: Optional[str] = Field(description="The earliest service period start date found on the bill, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="The latest service period end date found on the bill, in YYYY-MM-DD format.")
    totalCharges: float = Field(description="The 'Total Current Charges' from the Page 1 Account Summary.")
    amountDue: float = Field(description="The 'Total Due' from the Page 1 Account Summary.")
    afterDueDateAmount: Optional[float] = Field(default=None, description="The increased amount due if paid after the due date.")
    previousBalance: Optional[float] = Field(description="The 'Previous Amount Due' from the Page 1 Account Summary.")
    payments: List[Payment] = Field(description="A list of all payments shown in the Page 1 Account Summary.")
    balanceAdjustments: List[BalanceAdjustment] = Field(description="A list of non-usage-related charges/penalties from the Account Summary (e.g., Late Payment Penalty, Disconnect Notice Fee).")
    # The charges array here is for the TOTAL BILLED row, which already combines PUC/GRT.
    charges: List[RootChargeItem] = Field(description="A list of all charges from the 'TOTAL BILLED' summary row on Page 2.")
    accountData: List[AccountData] = Field(description="A list containing the details for the main account and all its nested meters.")
    paymentCoupon: Optional[PaymentCoupon] = Field(description="Data extracted from the payment stub.")
    messages: List[str] = Field(description="A list of all informational messages, warnings, or notices (e.g., 'Hurricane Preparedness').")

