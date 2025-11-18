"""
Pydantic models for Xcel Energy utility bill extraction
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Provider(BaseModel):
    """Information about the utility provider."""
    name: str = Field(description="The name of the utility provider, e.g., 'Xcel Energy'.")
    country: str = Field(description="The country where the provider operates, e.g., 'USA'.")


class BillingAddress(BaseModel):
    """Represents a billing address."""
    addressType: str = Field(description="Type of address, e.g., 'FULL' or 'PARTIAL'.", default="FULL")
    streetLine1: str = Field(description="The primary street address line.")
    streetLine2: Optional[str] = Field(description="The secondary street address line (if any).", default=None)
    city: Optional[str] = Field(description="The city of the address.", default=None)
    state: Optional[str] = Field(description="The state or province of the address.", default=None)
    postalCode: Optional[str] = Field(description="The postal or ZIP code.", default=None)
    country: str = Field(description="The country of the address, e.g., 'USA'.")
    recipient: Optional[str] = Field(description="The name of the person or company receiving the bill.", default=None)


class AccountDataItem(BaseModel):
    """A single account data entry."""
    accountNumber: str = Field(description="The unique account number for the customer.")
    billingAddress: BillingAddress


class ChargeItem(BaseModel):
    """A single line item from the *summary* charges table."""
    chargeNameAsPrinted: str = Field(description="The description of the charge as printed on the bill (e.g., 'Electricity Service').")
    chargeAmount: float = Field(description="The monetary value of this specific charge.")
    chargeCurrencyCode: str = Field(description="Currency code for this charge, e.g., 'USD'.", default="USD")
    premisesNumber: Optional[str] = Field(description="The premises number associated with this charge, if available.", default=None)


class DisconnectNotice(BaseModel):
    """Information related to a disconnection notice, if present."""
    pastDueAmount: Optional[float] = Field(default=None)
    disconnectDate: Optional[str] = Field(default=None)
    reconnectionFee: Optional[float] = Field(default=None)
    currencyCode: Optional[str] = Field(default=None)


class PremiseLineItem(BaseModel):
    """A single detailed line item charge (e.g., 'Energy Charge Summer')."""
    description: str
    usageUnits: Optional[str] = None
    rate: Optional[str] = None
    amount: float


class MeterReading(BaseModel):
    """Detailed meter reading information for a specific service."""
    meterNumber: str
    usageType: Optional[str] = None
    previousReading: Optional[float] = None
    currentReading: Optional[float] = None
    usage: Optional[float] = None
    usageUnits: Optional[str] = None
    readStartDate: Optional[str] = None
    readEndDate: Optional[str] = None
    readDays: Optional[int] = None
    nextReadDate: Optional[str] = None


class GasAdjustmentItem(BaseModel):
    """Conversion or adjustment factors for natural gas readings."""
    description: str
    formula: Optional[str] = None
    resultValue: Optional[float] = None
    resultUnits: Optional[str] = None


class UsageSummary(BaseModel):
    """Summary of usage averages for electricity/gas."""
    category: str
    currentUsage: Optional[float] = None
    previousUsage: Optional[float] = None
    currentCost: Optional[float] = None
    previousCost: Optional[float] = None
    currentTemperature: Optional[float] = None
    previousTemperature: Optional[float] = None


class ServiceBreakdown(BaseModel):
    """Details for a single service (Electricity or Gas) at a premise."""
    InvoiceNumber: str
    serviceType: str
    serviceAddress: str
    meterNumber: Optional[str] = None
    readStartDate: Optional[str] = None
    readEndDate: Optional[str] = None
    readDays: Optional[int] = None
    total: float
    lineItems: List[PremiseLineItem]
    meterReadings: Optional[List[MeterReading]] = None
    gasAdjustments: Optional[List[GasAdjustmentItem]] = None
    usageSummary: Optional[List[UsageSummary]] = None


class PremiseDetails(BaseModel):
    """All extracted details for a single, unique premise."""
    premisesNumber: str
    premisesTotal: float
    services: List[ServiceBreakdown]


class PremisesList(BaseModel):
    """Holds the list of all premise numbers found."""
    premise_numbers: List[str]


class PaymentInfo(BaseModel):
    """Represents how the customer pays their bill."""
    paymentMethod: Optional[str] = None
    autoPay: Optional[bool] = None
    remitToAddress: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact details for customer support."""
    phoneNumber: Optional[str] = None
    faxNumber: Optional[str] = None
    website: Optional[str] = None
    mailingAddress: Optional[str] = None


class NoticeInfo(BaseModel):
    """Informational or regulatory notices printed on the bill."""
    title: Optional[str] = None
    message: str
    referenceURL: Optional[str] = None


class UtilityBill(BaseModel):
    """The complete, structured data extracted from a utility bill."""
    type: str = Field(default="BILL")
    provider: Provider
    currencyCode: str = Field(default="USD")
    
    statementNumber: str
    statementDate: str
    previousStatementDate: Optional[str] = None
    dueDate: str
    periodStartDate: Optional[str] = None
    periodEndDate: Optional[str] = None
    
    totalCharges: float
    amountDue: float
    previousBalance: Optional[float] = None
    lastPaymentAmount: Optional[float] = None
    lastPaymentDate: Optional[str] = None
    
    accountData: List[AccountDataItem]
    charges: List[ChargeItem]
    premiseDetails: Optional[List[PremiseDetails]] = Field(
        description="A list of detailed breakdowns for each individual premise.", 
        default=None
    )
    
    # Optional extended fields
    paymentInfo: Optional[PaymentInfo] = None
    contactInfo: Optional[ContactInfo] = None
    notices: Optional[List[NoticeInfo]] = None
    disconnectNotice: Optional[DisconnectNotice] = None

