"""
Pydantic models for CenterPoint Energy utility bill extraction
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Provider(BaseModel):
    """Information about the utility provider."""
    name: str = Field(description="The name of the utility provider, e.g., 'CenterPoint Energy'.")
    country: str = Field(description="The country where the provider operates, e.g., 'US'.")

class BaseAddress(BaseModel):
    """Base model for an address."""
    streetLine1: Optional[str] = Field(description="The primary street address line.")
    city: Optional[str] = Field(description="The city of the address.")
    state: Optional[str] = Field(description="The state or province of the address.")
    postalCode: Optional[str] = Field(description="The postal or ZIP code.")
    country: str = Field(description="The country of the address, e.g., 'US'.")

class BillingAddress(BaseAddress):
    """Represents a billing (mailing) address."""
    addressType: str = Field(default="MAILING")
    recipient: Optional[str] = Field(description="The name of the person or company receiving the bill.")

class ServiceAddress(BaseAddress):
    """Represents a service address."""
    addressType: str = Field(default="SERVICE")

class MeterCharge(BaseModel):
    """A single detailed line item charge for a specific meter."""
    chargeNameAsPrinted: str = Field(description="The description of the charge (e.g., 'Basic charge', 'Cost of gas').")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")

class MeterUsage(BaseModel):
    """Detailed meter usage information for a specific service."""
    periodStartDate: Optional[str] = Field(description="Start date of the billing period for this meter, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="End date of the billing period for this meter, in YYYY-MM-DD format.")
    measuredUsage: Optional[float] = Field(description="The total usage for this period.")
    usageUnit: Optional[str] = Field(description="The unit of usage, e.g., 'THM'.")
    numberOfDaysInPeriod: Optional[int] = Field(description="The number of days in this billing period.")

class MeterData(BaseModel):
    """Details for a single service (meter) at a specific location."""
    serviceType: str = Field(description="Type of utility service, e.g., 'GAS'.")
    serviceAddress: ServiceAddress
    meterNumber: Optional[str] = Field(description="The meter number for this service.")
    periodStartDate: Optional[str] = Field(description="Start date of the billing period, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="End date of the billing period, in YYYY-MM-DD format.")
    totalUsage: Optional[float] = Field(description="The total usage for this meter, e.g., 1067.0.")
    totalUsageUnit: Optional[str] = Field(description="The unit for total usage, e.g., 'THM'.")
    charges: List[MeterCharge] = Field(description="A list of all detailed charges for this meter (Basic charge, Delivery, etc.).")
    usages: List[MeterUsage] = Field(description="A list containing the usage details for this meter.")

class AccountData(BaseModel):
    """A single account, which may contain multiple meters/services."""
    accountNumber: str = Field(description="The main account number for the customer (e.g., 8000013866-1).")
    billingAddress: BillingAddress
    periodStartDate: Optional[str] = Field(description="The earliest service start date on the bill, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="The latest service end date on the bill, in YYYY-MM-DD format.")
    dueDate: str = Field(description="The date the payment is due, in YYYY-MM-DD format.")
    statementDate: str = Field(description="The date the bill was issued, in YYYY-MM-DD format.")
    outstandingBalance: Optional[float] = Field(description="The total amount due for this account.")
    currencyCode: str = Field(default="USD")
    totalCharges: float = Field(description="The total of *current* charges for this account.")
    meterData: List[MeterData] = Field(description="A list of all detailed meter/service breakdowns for this account.")

class RootChargeItem(BaseModel):
    """A single line item from the *root* (top-level) charges, if any."""
    chargeNameAsPrinted: str = Field(description="The description of the charge as printed on the bill.")
    chargeType: str = Field(default="DEBIT")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")
    chargeCurrencyCode: str = Field(default="USD")

class PaymentCouponAddress(BaseAddress):
    """The 'remit to' address for payments."""
    addressType: str = Field(default="REMIT")

class PaymentCoupon(BaseModel):
    """Information from the payment stub."""
    amountDue: Optional[float] = Field(description="The amount due shown on the coupon.")
    dueDate: Optional[str] = Field(description="The due date shown on the coupon, in YYYY-MM-DD format.")
    remitToAddress: Optional[PaymentCouponAddress] = Field(description="The address to mail payments to.")
    scanline: Optional[str] = Field(description="The long string of numbers at the bottom of the coupon.")

class UtilityBillExtraction(BaseModel):
    """The complete, structured data extracted from a utility bill."""
    type: str = Field(default="UtilityBillExtraction")
    provider: Provider
    currencyCode: str = Field(default="USD")
    
    statementDate: str = Field(description="The main billing date of the statement, in YYYY-MM-DD format.")
    previousStatementDate: Optional[str] = Field(default=None)
    dueDate: str = Field(description="The main due date (e.g., Bankdraft Date), in YYYY-MM-DD format.")
    periodStartDate: Optional[str] = Field(description="The earliest service period start date found on the bill, in YYYY-MM-DD format.")
    periodEndDate: Optional[str] = Field(description="The latest service period end date found on the bill, in YYYY-MM-DD format.")
    
    totalCharges: float = Field(description="The total of *current* charges (e.g., 'Current gas charges').")
    amountDue: float = Field(description="The total amount due to be paid (e.g., 'Total amount due to be drafted').")
    previousBalance: Optional[float] = Field(description="The previous amount due.")
    lastPaymentAmount: Optional[float] = Field(description="The amount of the last payment received.")
    lastPaymentDate: Optional[str] = Field(description="The date the last payment was received, in YYYY-MM-DD format.")
    
    charges: List[RootChargeItem] = Field(description="A list of any charges found at the *root* summary level. (This is often sparse).")
    accountData: List[AccountData] = Field(description="A list containing the details for the main account (e.g., 8000013866-1) and all its nested meters.")
    paymentCoupon: Optional[PaymentCoupon] = Field(description="Data extracted from the payment stub.")
    messages: List[str] = Field(description="A list of all informational messages, warnings, or notices (e.g., 'Gas leak or emergency').")
