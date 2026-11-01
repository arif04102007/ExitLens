"""FIXTURE MODE: sample pages for developing and testing WITHOUT spending TinyFish credits.

These pages are FICTIONAL ("ShopEasy" / "Acme Audio"). They exist only so the pipeline can be
tested offline. The UI shows a loud banner whenever fixture mode is on. Never use this for the
real demo: set EXITLENS_MODE=live.
"""
import time

SHOPEASY_HUB = """# ShopEasy Help Centre
Welcome to the ShopEasy help centre. Find answers about orders, payments, delivery and your account.
Browse topics below or contact support. We are here to help every day of the week with anything you need.
- Orders and tracking
- Payments and offers
- Delivery information
- Returns and refunds: see [Returns & Refunds Policy](https://shopeasy.example/help/returns)
- Account and security settings for your profile and saved addresses
Popular articles are updated regularly by our support team to keep information accurate and easy to find.
Thank you for shopping with ShopEasy. Download our app for faster checkout and exclusive member offers.
"""

SHOPEASY_RETURNS = """# ShopEasy Returns & Refunds Policy
Most items can be returned within 7 days of delivery if they are unused and in their original packaging.
Defective or damaged products are eligible for a free replacement within 10 days of delivery.
To raise a return request, keep your order ID and invoice ready, and upload photos of the defect.
Items marked non-returnable on the product page cannot be returned.
Products that show physical damage caused by the customer are not eligible for return.
To start a return, visit https://shopeasy.example/help/returns/start or email returns@shopeasy.example.
Refunds are issued to the original payment method within 5 to 7 business days after the item is received.
"""

ACME_WARRANTY = """# Acme Audio India Warranty Policy
Acme Audio headphones come with a 1 year limited warranty from the date of purchase.
To claim warranty you must provide the original invoice or proof of purchase and the product serial number.
The warranty does not cover physical damage, water damage or damage caused by unauthorised repair.
Warranty claims can be submitted at https://acmeaudio.example/support/warranty or by emailing care@acmeaudio.example.
Replacement or repair is decided by Acme Audio after the product is inspected at a service centre.
Accessories such as ear tips and cables are not covered after 30 days of purchase.
"""

COUPON_BLOG = """# ShopEasy return policy explained
Thinking of returning something to ShopEasy? Read our coupon roundup first and save more today."""

PAGES = {
    "https://shopeasy.example/help": SHOPEASY_HUB,
    "https://shopeasy.example/help/returns": SHOPEASY_RETURNS,
    "https://acmeaudio.example/support/warranty": ACME_WARRANTY,
    "https://coupons-blog.example/shopeasy-return-policy": COUPON_BLOG,
}


class FixtureClient:
    """Same interface as TinyFish, backed by the sample pages above."""

    is_fixture = True

    def search(self, query, **params):
        q = query.lower()
        if "shopeasy" in q:
            return [
                {"position": 1, "title": "ShopEasy Help Centre", "url": "https://shopeasy.example/help", "snippet": "Orders, delivery, returns and refunds help."},
                {"position": 2, "title": "ShopEasy return policy explained (coupons)", "url": "https://coupons-blog.example/shopeasy-return-policy", "snippet": "Unofficial blog."},
            ]
        if "acme" in q:
            return [{"position": 1, "title": "Acme Audio India Warranty Policy", "url": "https://acmeaudio.example/support/warranty", "snippet": "1 year limited warranty."}]
        return []

    def fetch(self, urls, fresh=False):
        if isinstance(urls, str):
            urls = [urls]
        time.sleep(0.4)
        return {u: ({"text": PAGES[u], "final_url": u, "title": u} if u in PAGES else None) for u in urls}

    def agent_run(self, url, goal, max_seconds=90, on_progress=None):
        steps = ["opening the site", "scanning the footer and help links", "following 'Returns and refunds'", "reached the policy page"]
        for s in steps:
            if on_progress:
                on_progress(s)
            time.sleep(0.5)
        if "shopeasy" in url:
            return {"policy_urls": ["https://shopeasy.example/help/returns"], "notes": "fixture agent"}
        return {"policy_urls": [], "notes": "fixture agent found nothing"}
