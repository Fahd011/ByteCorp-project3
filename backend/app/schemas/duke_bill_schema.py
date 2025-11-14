"""
Pydantic models for Duke Energy utility bill extraction
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Provider(BaseModel):
    name: str
    country: str


class BillingAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    streetLine2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str
    recipient: Optional[str] = None


class ServiceAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    city: str
    state: str
    postalCode: str
    country: str


class ChargeItem(BaseModel):
    chargeNameAsPrinted: str
    chargeType: str = "DEBIT"
    chargeAmount: float
    chargeCurrencyCode: str = "USD"
    usageUnit: Optional[str] = None
    chargeRate: Optional[float] = None
    unitsPerRate: Optional[float] = None
    chargeGroupHeading: Optional[str] = None


class MeterCharge(BaseModel):
    chargeNameAsPrinted: str
    chargeAmount: float


class Usage(BaseModel):
    periodStartDate: str
    periodEndDate: str
    measuredUsage: float
    usageUnit: str
    numberOfDaysInPeriod: int


class MeterData(BaseModel):
    serviceType: str
    serviceAddress: ServiceAddress
    meterNumber: Optional[str] = None
    periodStartDate: str
    periodEndDate: str
    totalUsage: Optional[float] = None
    totalUsageUnit: Optional[str] = None
    demandKW: Optional[float] = None
    charges: List[MeterCharge] = []
    usages: List[Usage] = []


class AccountDataItem(BaseModel):
    accountNumber: str
    billingAddress: BillingAddress
    periodStartDate: str
    periodEndDate: str
    dueDate: str
    statementDate: Optional[str] = None
    disconnectDate: Optional[str] = None
    outstandingBalance: Optional[float] = None
    currencyCode: str = "USD"
    totalCharges: float
    meterData: List[MeterData] = []


class RemitToAddress(BaseModel):
    addressType: str = "FULL"
    streetLine1: str
    city: str
    state: str
    postalCode: str
    country: str


class PaymentCoupon(BaseModel):
    amountDue: float
    dueDate: str
    remitToAddress: RemitToAddress
    scanline: Optional[str] = None


class DisconnectNotice(BaseModel):
    pastDueAmount: Optional[float] = None
    disconnectDate: Optional[str] = None
    reconnectionFee: Optional[float] = None
    currencyCode: Optional[str] = None


class UtilityBillExtraction(BaseModel):
    """Duke Energy utility bill schema (meter-based, no premises)"""
    type: str = "BILL"
    provider: Provider
    currencyCode: str = "USD"
    statementDate: str
    previousStatementDate: Optional[str] = None
    dueDate: str
    periodStartDate: str
    periodEndDate: str
    totalCharges: float
    amountDue: float
    previousBalance: Optional[float] = None
    lastPaymentAmount: Optional[float] = None
    lastPaymentDate: Optional[str] = None
    charges: List[ChargeItem] = []
    accountData: List[AccountDataItem] = []
    paymentCoupon: Optional[PaymentCoupon] = None
    disconnectNotice: Optional[DisconnectNotice] = None
    messages: List[str] = []
    dataIngestionMethod: Optional[str] = None
    sourceType: Optional[str] = None

