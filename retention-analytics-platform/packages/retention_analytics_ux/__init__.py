"""UX-layer services: tenant settings, saved reports, bulk events, flow management, campaigns.

These power the user-facing UI — real forms, saved state, bulk operations —
as opposed to the raw JSON API used by the dev console.
"""

from retention_analytics_ux.campaign import CAMPAIGN_GOALS, CampaignService, evaluate_segment

__all__ = ["CampaignService", "CAMPAIGN_GOALS", "evaluate_segment"]
