"""Business content taken from the JPS planning notes (JPS_website/idea).
Edit prices, services and policy wording here – every page reads from this file."""

PLANS = [
    {"key": "bronze", "name": "Bronze", "price": 65, "services": 2,
     "perks": ["Choose any 2 services from the list", "No call-out fee on extra maintenance",
               "Extra work at $65/h", "Reminders before each visit"]},
    {"key": "silver", "name": "Silver", "price": 99, "services": 3, "popular": True,
     "perks": ["Choose any 3 services from the list", "No call-out fee on extra maintenance",
               "Extra work at $65/h", "Reminders before each visit"]},
    {"key": "gold", "name": "Gold", "price": 120, "services": 4,
     "perks": ["Choose any 4 services from the list", "No call-out fee on extra maintenance",
               "Extra work at $65/h", "Priority booking"]},
]
PLANS_BY_KEY = {p["key"]: p for p in PLANS}
MEMBER_HOURLY = 65

# Services a subscriber can pick for their plan visits (icon, label)
PLAN_SERVICES = [
    ("home", "Gutter cleaning"), ("sun", "Solar panel clean"), ("drop", "Pressure wash driveway / area"),
    ("fan", "Fan & air-cooler filter service"), ("leaf", "Garden tidy-up"), ("window", "Window clean"),
    ("sprout", "Reticulation check"), ("home", "Roof clean"), ("drop", "House wash"), ("leaf", "Garden clean-up"),
]

SERVICES_MAIN = [
    ("wrench", "Handyman", "Repairs, installs, doors, locks, fly screens and the jobs that never get done."),
    ("hammer", "Carpentry", "Decking, pergolas, cabinetry, worktops and custom timber work."),
    ("home", "House renos", "Kitchens, splashbacks and refreshes to get a property rental- or sale-ready."),
]
SERVICES_OUTDOOR = ["Lawn mowing / grass cut", "Gutter cleaning", "Roof pressure clean", "Driveway pressure clean",
                    "House wash", "Window cleaning", "Solar panel cleaning", "Paving", "Decking", "Pergolas",
                    "Pool fencing", "Clotheslines", "Letterboxes", "Fly screens", "Door locks",
                    "Reticulation check", "Garden tidy-up", "General tidy-up"]
SERVICES_INDOOR = ["Doors", "Splashbacks", "Kitchen & bedroom units", "Worktops / benchtops", "Window cleaning",
                   "Cleaning", "Fan & air-cooler filter service", "Minor repairs"]

# Pricing for one-off work (from the quote / call-out notes and the Quotation Fee policy)
CALLOUT_FEE = 150          # includes first hour
CALLOUT_HOURLY = 75        # after first hour, + materials
QUOTE_FEE_THRESHOLD = 2000
QUOTE_FEE_PERCENT = 3
SETTLEMENT_SURCHARGE = 5

REQUEST_KINDS = {
    "quote": "Project / reno quote",
    "callout": "Call-out request",
    "subscriber": "Subscriber request",
}

STATUSES = {
    "new": "New",
    "reviewing": "Reviewing",
    "quoted": "Quote sent",
    "accepted": "Accepted",
    "declined": "Declined",
    "scheduled": "Scheduled",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

CONTACT_METHODS = {"phone": "Phone call", "sms": "Text message", "email": "Email"}

WORK = [  # portfolio placeholders – replace with real project photos
    ("g1", "Carpentry", "Deck restoration", "Sand, repair and re-oil", True),
    ("g2", "Renovations", "Kitchen refresh", "Splashback, worktops, cabinet fronts", False),
    ("g3", "Maintenance", "Rental make-ready", "Garden, gutters, pressure wash", True),
    ("g5", "Carpentry", "New pergola", "Timber pergola build", False),
    ("g6", "Maintenance", "Gutter & solar clean", "Annual plan visit", False),
    ("g4", "Renovations", "Bathroom update", "Vanity, tiling touch-ups, fixtures", True),
    ("g3", "Maintenance", "Pool fencing", "Repair and replacement panels", False),
    ("g2", "Handyman", "Doors & locks", "Re-hang doors, new locks, fly screens", False),
    ("g1", "Renovations", "Pre-sale refresh", "Paid at settlement", True),
]

TERMS = [
    ("Scope of Services", "Just Professional Services provides construction, maintenance, repair, renovation, and property improvement services for residential, commercial, and real estate properties."),
    ("Free Estimates", "Free preliminary estimates may be provided when clients supply clear written descriptions and photos/videos of the work. An on-site inspection may still be required."),
    ("Quotation Fee", "A fee applies for projects over $2,000 or complex works requiring detailed assessment. For jobs over $2,000, the fee is 3% of the estimated project cost. The fee is deducted from the final invoice if the client proceeds."),
    ("Payment Terms", "Payments are due as specified on the invoice. Staged payments may apply. Materials may require prepayment."),
    ("Payment-at-Settlement Option", "For properties listed with a licensed real estate agent, payment may be deferred until settlement. A 5% surcharge applies. Payment is due at or before settlement. If settlement fails, the invoice becomes immediately payable."),
    ("Variations", "Changes requested after quoting will incur additional costs and must be agreed upon."),
    ("Cancellations", "Cancellations with less than 24 hours’ notice may incur fees. Costs for purchased materials or completed work remain payable."),
    ("Warranties & Liability", "All work is performed with reasonable care. The Company is not liable for hidden defects, pre-existing issues, or indirect/consequential losses."),
    ("Client Responsibilities", "Clients must ensure safe access, clear work areas, accurate site information, and required permits."),
    ("Privacy", "Client information is confidential and used only for service delivery except where required by law."),
    ("Governing Law", "These Terms comply with the laws of the service location."),
    ("Amendments", "Terms may be updated periodically. The latest version is available on request."),
]

QUOTE_POLICY = [
    ("Free estimates with client-provided details", "If you provide a clear written description of the work, along with photos or videos, we may be able to offer a free preliminary estimate without the need for an on-site visit."),
    ("When quotation fees apply", "Projects over $2,000: a quotation fee of 3% of the estimated project cost will be charged. Complex jobs: a fee may apply for works involving structural components, roofing, major renovations, multi-trade coordination, or detailed site investigations. We may also apply a fee to other projects requiring extensive assessment, provided this is disclosed to you beforehand."),
    ("Consent", "We will notify you in advance if a quotation fee applies. No quotation fee will be charged without your express consent, given in writing, electronically or verbally. A formal quotation may be withheld until the fee is paid."),
    ("Fee deduction", "If you proceed with the quoted work, the quotation fee is fully deducted from the total job cost. If you choose not to proceed, the fee is non-refundable unless otherwise agreed in writing. Paying the fee does not oblige you to proceed."),
    ("Payment at settlement", "If your property is being sold through a licensed real estate agency, the cost of renovation or maintenance work may be deferred until settlement, subject to approval. A 5% deferred-payment surcharge applies, the selling agent must confirm in writing that settlement funds will be available, and full payment is due at or before settlement."),
    ("Transparency and approval", "You are always informed in advance when quotation fees or deferred-payment arrangements apply. No charges or payment terms are applied without your prior approval."),
]
