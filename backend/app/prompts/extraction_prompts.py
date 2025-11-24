"""
Extraction prompts for RAG-based bill data extraction
"""

# Xcel Energy Prompts

XCEL_SUMMARY_PROMPT = """
Based ONLY on the following context from a single utility bill, extract ALL requested information.
Fill out the entire JSON schema provided.

- For `totalCharges`, use the 'Current Charges' value.
- For `amountDue`, use the 'Amount Due' value.
- `charges` should be a list of ALL line items from the 'PREMISES SUMMARY' table.
- Infer dates like `previousStatementDate` from context (e.g., 'As of 08/26' for previous balance).
- If a payment was received, extract the amount. If it says 'No Payments Received', `lastPaymentAmount` should be 0.0.
- If no information is present for a field, leave it as null (it will be handled by the schema).
- The bill is from the USA, so the currency is 'USD' and country is 'USA'.
- DO NOT attempt to fill in 'premiseDetails'. Leave it as null.

Context:
{context}
"""

XCEL_PREMISES_PROMPT = """
Based ONLY on the provided context, find the 'PREMISES SUMMARY' table.
Extract *all* of the 'PREMISES NUMBER' values from that table.
Return only the list of premise number strings.

Context:
{context}
"""

XCEL_PREMISE_DETAILS_PROMPT = """
You will be given context from a utility bill that contains the detailed breakdown
for a specific premise. Based ONLY on this context, extract the following
information for PREMISE NUMBER: {premise_num}.

1.  Find the 'ELECTRICITY SERVICE DETAILS' and 'NATURAL GAS SERVICE DETAILS'.
2.  For each service, extract:
    - Invoice number
    - Service address
    - Meter number
    - Read period or read start/end dates (e.g., '08/25/25 - 09/24/25').
3.  For each service, extract all line items under 'ELECTRICITY CHARGES' or 'NATURAL GAS CHARGES',
    including all taxes (City Fees, State Tax, etc.).
4.  Extract the 'Total' for each service.
5.  Extract the 'Premises Total' for this premise (usually at the end of the gas section).
6.  Also extract the 'YOUR MONTHLY ELECTRICITY USAGE' and 'YOUR MONTHLY NATURAL GAS USAGE'
    daily averages section found near the graphs at the top of each page.
    - For each category, extract:
        • Temperature (this year and last year)
        • Usage (Electricity kWh / Gas Therms)
        • Cost ($)
    - Map these to the following fields:
        category: 'Electricity' or 'Gas'
        currentUsage, previousUsage, currentCost, previousCost, currentTemperature, previousTemperature
7.  Ensure that these are stored in the nested field 'usageSummary' under each corresponding service.
8.  Return the result in the exact JSON schema provided.
    
Context:
{context}
"""

# Duke Energy Prompts

DUKE_SYSTEM_PROMPT = """You are an expert at extracting structured data from Duke Energy utility bills.

Extract ALL information following the exact schema structure provided. Be thorough and accurate.

Key sections to extract:
1. Provider information (name, country)
2. Statement dates, due dates, period dates
3. Financial amounts (total charges, amount due, previous balance, payments)
4. Charges → each line item (customer charge, energy charges by tier, riders, late fees, taxes)
5. Account data with billing address
6. Meter data → for each meter: meter number, service address, usage readings, charges per meter
7. Usages → start/end dates, measured usage, billed kWh/therms, number of days
8. Disconnect notices → past due amounts, disconnect dates, reconnection fees if present
9. Payment coupon → amount due, remit-to address, scanline
10. Messages or notices from the bill

Formatting Rules:
- Monetary values → numbers only (remove $ and commas)
- Dates → "YYYY-MM-DD" format
- If a field is missing or not found, omit it
- Taxes must be included as charges (e.g. "Sales Tax")
- For serviceType, use: "ELECTRICITY", "GAS", or "WATER"
- For chargeType, use: "DEBIT" or "CREDIT"
"""

DUKE_EXTRACTION_PROMPT = "Extract all data from this Duke Energy utility bill:\n\n{context}"

CENTERPOINT_SYSTEM_PROMPT = """You are an expert at extracting structured data from CenterPoint Energy utility bills.

Extract ALL information following the exact schema structure provided. Be thorough and accurate.

Key sections to extract:
1. Provider information (name: 'CenterPoint Energy', country: 'US')
2. Statement dates, due dates, period dates
3. Financial amounts (total charges, amount due, previous balance, payments)
4. Charges → root-level charges (usually sparse, mostly totals)
5. Account data → main account number, billing address
6. Meter data → CRITICAL: Extract one entry for EACH service/meter listed
   - For each meter: serviceType (e.g., 'GAS'), serviceAddress, meterNumber
   - Extract periodStartDate, periodEndDate, totalUsage, totalUsageUnit
   - charges → ALL line items for this meter (Basic charge, Delivery, Cost of gas, taxes)
   - usages → billing period details, measured usage, usage unit, number of days
7. Payment coupon → amount due, due date, remit-to address, scanline
8. Messages → all informational notices, warnings, contact information

Formatting Rules:
- Monetary values → numbers only (remove $ and commas)
- Dates → "YYYY-MM-DD" format
- If a field is missing or not found, omit it
- For serviceType, use: "ELECTRICITY", "GAS", or "WATER"
- For chargeType, use: "DEBIT" or "CREDIT"
- Extract ALL meters/services from summary tables into separate meterData entries
"""

CENTERPOINT_EXTRACTION_PROMPT = "Extract all data from this CenterPoint Energy utility bill:\n\n{context}"

# Green Mountain Energy Prompts

GREEN_MOUNTAIN_SYSTEM_PROMPT = """You are an expert at extracting structured data from Green Mountain Energy utility bills.

Extract ALL information following the exact schema structure provided. Be thorough and accurate.

Key sections to extract:
1. Provider information (name: 'Green Mountain Energy', country: 'US')
2. Statement dates, due dates, period dates
3. Financial amounts (total charges, amount due, previous balance, payments)
4. Payments → extract ALL payment entries from the Account Summary
5. **Balance Adjustments → CRITICAL: Extract items like 'Late Payment Penalty' and 'Disconnect Notice Fee' from the Account Summary and place them in the 'balanceAdjustments' list.**
6. Charges → extract the 'TOTAL BILLED' summary row from Page 2
7. Account data → account number, billing address
8. Meter data → CRITICAL: Extract one entry for EACH meter listed in the usage/charge tables
   - For each meter: serviceType ('ELECTRICITY'), serviceAddress, meterNumber, ESIID
   - Extract periodStartDate, periodEndDate, totalUsage, totalUsageUnit
   - charges → CRITICAL: Extract PUC and GRT Reimburse as SEPARATE charges
     * Only create charges for columns that have actual monetary values
     * If a column is blank for a meter, DO NOT create a charge for it
   - usages → billing period details, measured usage in kWh, number of days
9. Payment coupon → amount due, due date, remit-to address
10. Messages → all informational notices, warnings

Formatting Rules:
- Monetary values → numbers only (remove $ and commas)
- Dates → "YYYY-MM-DD" format
- If a field is missing or not found, omit it
- For serviceType, use: "ELECTRICITY"
- For chargeType, use: "DEBIT" or "CREDIT"
"""

GREEN_MOUNTAIN_EXTRACTION_PROMPT = "Extract all data from this Green Mountain Power utility bill:\n\n{context}"