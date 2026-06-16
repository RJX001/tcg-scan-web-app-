"""eBay Partner Network affiliate URL builder."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def build_ebay_affiliate_url(
    item_url: str,
    *,
    tracking_id: str,
    campaign_id: str,
) -> str:
    """Append EPN tracking params to an eBay item URL."""
    parsed = urlparse(item_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update(
        {
            "mkevt": "1",
            "mkcid": "1",
            "campid": campaign_id,
            "customid": tracking_id,
            "toolid": "10001",
        }
    )
    return urlunparse(parsed._replace(query=urlencode(params)))
