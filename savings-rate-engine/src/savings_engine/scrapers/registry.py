from .acb import ACBScraper
from .base import BaseScraper
from .bidv import BIDVScraper
from .mb import MBBankScraper
from .techcombank import TechcombankScraper
from .vcb import VCBScraper
from .vietinbank import VietinBankScraper
from .vpbank import VPBankScraper

# Map bank_code → scraper class. Add new scrapers here.
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "VCB":  VCBScraper,
    "BIDV": BIDVScraper,
    "CTG":  VietinBankScraper,
    "TCB":  TechcombankScraper,
    "MBB":  MBBankScraper,
    "ACB":  ACBScraper,
    "VPB":  VPBankScraper,
}


def get_scraper(bank_code: str) -> BaseScraper:
    cls = SCRAPER_REGISTRY.get(bank_code.upper())
    if cls is None:
        raise KeyError(f"No scraper registered for bank code '{bank_code}'")
    return cls()
