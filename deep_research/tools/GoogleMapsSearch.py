"""GoogleMapsSearch — Lead Hunter's primary discovery tool.

Implements Step 1 of the website-selling pipeline (the article workflow):

  - Narrow niche + city query (e.g. "cosmetic dentists in West Austin").
  - Skip the top dominant results (configurable; default 3).
  - Surface businesses in the article's "sweet spot": 5+ years online,
    fewer than 50 reviews, no website link OR an outdated/broken one,
    solid star rating despite the bad online presence.

Backed by Google Places API (New) Text Search.
Set GOOGLE_PLACES_API_KEY in your .env to use this tool.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field


PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Field mask: ask for only the fields we actually use. Keeps cost low.
DEFAULT_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.internationalPhoneNumber",
        "places.nationalPhoneNumber",
        "places.businessStatus",
        "places.primaryTypeDisplayName",
        "places.types",
    ]
)


def _looks_like_website_gap(website_uri: Optional[str]) -> bool:
    """The article's 'website link is missing or feels old' signal.

    We can't open every site to check it, but we can flag obvious gaps:
      - No website URL at all on the Google profile.
      - URLs pointing to social-only profiles (a real anti-pattern for SMBs).
      - URLs with `wix.com`, `weebly.com`, `squarespace`, etc. in path —
        owner-built, often outdated.
    """
    if not website_uri:
        return True
    uri = website_uri.lower()
    suspicious_hosts = (
        "facebook.com",
        "instagram.com",
        "linktr.ee",
        "yelp.com",
        "yellowpages.com",
        "linkedin.com",
    )
    if any(h in uri for h in suspicious_hosts):
        return True
    return False


def _is_sweet_spot(place: dict, max_reviews: int) -> bool:
    """Article rule: established, low review count, gappy site, decent rating."""
    review_count = place.get("userRatingCount") or 0
    rating = place.get("rating") or 0.0
    website_uri = place.get("websiteUri")
    if review_count <= 0 or review_count > max_reviews:
        return False
    if rating < 4.0:
        return False
    return _looks_like_website_gap(website_uri)


def _phone(place: dict) -> Optional[str]:
    return place.get("internationalPhoneNumber") or place.get("nationalPhoneNumber")


def _name(place: dict) -> str:
    return (place.get("displayName") or {}).get("text") or "(unnamed)"


def _website_or_none(place: dict) -> Optional[str]:
    return place.get("websiteUri")


class GoogleMapsSearch(BaseTool):
    """
    Search Google Maps for local businesses matching a niche+city query and
    filter for the article's "sweet spot" pattern (low reviews, weak website,
    solid rating). Returns a structured lead list.

    Usage:
      query="cosmetic dentists in West Austin", limit=30, max_reviews=50

    Notes:
      - Requires GOOGLE_PLACES_API_KEY in the environment.
      - Skips the top `skip_dominant_count` results (article rule: avoid the
        top 3-4, those don't need you).
      - `only_sweet_spot=True` (default) hard-filters to the article rule;
        set False to see everything returned by Places.
    """

    query: str = Field(
        ...,
        description=(
            "Narrow niche+city query, e.g. 'cosmetic dentists in West Austin' "
            "or 'fence installers Tampa Florida'. The narrower the better."
        ),
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=20,
        description="Max number of leads to return AFTER filtering. Places API caps single-page text search at 20.",
    )
    skip_dominant_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description=(
            "How many top-ranked results to skip. The article's rule: skip the "
            "businesses crushing it already (top 3-4)."
        ),
    )
    max_reviews: int = Field(
        default=50,
        ge=1,
        description="Sweet-spot max review count. Article default: under 50.",
    )
    only_sweet_spot: bool = Field(
        default=True,
        description=(
            "If True, hard-filter to the article's sweet spot (low reviews, "
            "decent rating, missing or weak website). If False, return all."
        ),
    )

    def run(self) -> str:
        load_dotenv(override=True)
        api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        if not api_key:
            return json.dumps(
                {
                    "error": "GOOGLE_PLACES_API_KEY not set",
                    "fix": (
                        "Add GOOGLE_PLACES_API_KEY=... to .env. Enable the "
                        "'Places API (New)' on your GCP project. Until then, "
                        "the agent can fall back to WebSearchTool but lead "
                        "metadata will be incomplete."
                    ),
                },
                indent=2,
            )

        try:
            import requests  # imported lazily to keep tool import cheap
        except ImportError:
            return json.dumps({"error": "requests is not installed"})

        # Places API caps results per page at ~20. We ask for the most we can,
        # then trim down after skipping dominant ones + filtering.
        page_size = max(self.limit + self.skip_dominant_count, 1)
        page_size = min(page_size, 20)

        body = {
            "textQuery": self.query,
            "pageSize": page_size,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": DEFAULT_FIELD_MASK,
        }

        try:
            resp = requests.post(
                PLACES_TEXT_SEARCH_URL, headers=headers, json=body, timeout=30
            )
        except Exception as e:
            return json.dumps({"error": f"Network error calling Places API: {e}"})

        if resp.status_code != 200:
            return json.dumps(
                {
                    "error": f"Places API returned {resp.status_code}",
                    "body": resp.text[:500],
                }
            )

        data = resp.json()
        places = data.get("places") or []

        # Skip the dominant top results per the article rule.
        candidates = places[self.skip_dominant_count :]

        leads = []
        for place in candidates:
            if self.only_sweet_spot and not _is_sweet_spot(place, self.max_reviews):
                continue

            website = _website_or_none(place)
            leads.append(
                {
                    "place_id": place.get("id"),
                    "name": _name(place),
                    "category": place.get("primaryTypeDisplayName", {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "phone": _phone(place),
                    "rating": place.get("rating"),
                    "review_count": place.get("userRatingCount"),
                    "website": website,
                    "website_gap": _looks_like_website_gap(website),
                    "google_maps_url": place.get("googleMapsUri"),
                    "business_status": place.get("businessStatus"),
                    # The Lead Hunter agent will fill `hook` after enrichment.
                    "hook": None,
                }
            )
            if len(leads) >= self.limit:
                break

        return json.dumps(
            {
                "query": self.query,
                "raw_returned": len(places),
                "after_skip_and_filter": len(leads),
                "filter": {
                    "skip_dominant_count": self.skip_dominant_count,
                    "max_reviews": self.max_reviews,
                    "only_sweet_spot": self.only_sweet_spot,
                },
                "leads": leads,
            },
            indent=2,
        )


if __name__ == "__main__":
    tool = GoogleMapsSearch(query="cosmetic dentists in West Austin")
    print(tool.run())
