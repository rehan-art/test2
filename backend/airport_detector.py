import re


AIRPORT_TERMS = [
    "airport",
    "rajiv gandhi international airport",
    "shamshabad airport",
    "rgi airport",
    "rgia",
    "hyd airport",
    "hydairport",
]


def is_airport_reporting_address(address):

    if address is None:
        return False

    text = re.sub(
        r"\s+",
        " ",
        str(address).strip().lower()
    )

    if not text:
        return False

    return any(
        term in text
        for term in AIRPORT_TERMS
    )