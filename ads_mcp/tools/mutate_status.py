# Copyright 2026 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for enabling, pausing, or removing existing campaigns, ad groups,
keywords, and ads.
"""

from typing import Any, Dict
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations

import ads_mcp.utils as utils
from ads_mcp.tools.mutate_common import (
    SAFETY_NOTE,
    build_update_operation,
    check_enum,
    clean_id,
    run_mutate,
)

status_mcp = FastMCP("status")

_STATUSES = {"ENABLED", "PAUSED", "REMOVED"}


def set_campaign_status(
    customer_id: str | int,
    campaign_id: str | int,
    status: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Enables, pauses, or removes a campaign.

    Args:
        customer_id: The id of the customer that owns the campaign.
        campaign_id: The id of the campaign to change.
        status: One of ENABLED, PAUSED, REMOVED.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    status = check_enum(status, _STATUSES, "status")
    client = utils.get_googleads_client()
    campaign_service = client.get_service("CampaignService")

    operation = build_update_operation(
        client,
        "CampaignOperation",
        campaign_service.campaign_path(
            clean_id(customer_id), clean_id(campaign_id)
        ),
        status=getattr(client.enums.CampaignStatusEnum, status),
    )

    return run_mutate(
        "CampaignService",
        "mutate_campaigns",
        customer_id,
        [operation],
        confirm,
    )


def set_ad_group_status(
    customer_id: str | int,
    ad_group_id: str | int,
    status: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Enables, pauses, or removes an ad group.

    Args:
        customer_id: The id of the customer that owns the ad group.
        ad_group_id: The id of the ad group to change.
        status: One of ENABLED, PAUSED, REMOVED.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    status = check_enum(status, _STATUSES, "status")
    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")

    operation = build_update_operation(
        client,
        "AdGroupOperation",
        ad_group_service.ad_group_path(
            clean_id(customer_id), clean_id(ad_group_id)
        ),
        status=getattr(client.enums.AdGroupStatusEnum, status),
    )

    return run_mutate(
        "AdGroupService",
        "mutate_ad_groups",
        customer_id,
        [operation],
        confirm,
    )


def set_ad_status(
    customer_id: str | int,
    ad_group_id: str | int,
    ad_id: str | int,
    status: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Enables, pauses, or removes an existing ad.

    To change an ad's headlines or descriptions, create a new ad with the
    `ads_create_responsive_search_ad` tool and pause or remove this one - the
    Google Ads API does not support editing an ad's copy in place.

    Args:
        customer_id: The id of the customer that owns the ad.
        ad_group_id: The id of the ad group the ad belongs to.
        ad_id: The id of the ad to change.
        status: One of ENABLED, PAUSED, REMOVED.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    status = check_enum(status, _STATUSES, "status")
    client = utils.get_googleads_client()
    ad_group_ad_service = client.get_service("AdGroupAdService")

    operation = build_update_operation(
        client,
        "AdGroupAdOperation",
        ad_group_ad_service.ad_group_ad_path(
            clean_id(customer_id), clean_id(ad_group_id), clean_id(ad_id)
        ),
        status=getattr(client.enums.AdGroupAdStatusEnum, status),
    )

    return run_mutate(
        "AdGroupAdService",
        "mutate_ad_group_ads",
        customer_id,
        [operation],
        confirm,
    )


def set_keyword_status(
    customer_id: str | int,
    ad_group_id: str | int,
    criterion_id: str | int,
    status: str,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Enables, pauses, or removes an existing keyword (or negative keyword).

    Args:
        customer_id: The id of the customer that owns the keyword.
        ad_group_id: The id of the ad group the keyword belongs to.
        criterion_id: The id of the keyword criterion to change (this is the
            ad_group_criterion.criterion_id field from a keyword_view query,
            not the keyword text).
        status: One of ENABLED, PAUSED, REMOVED.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    status = check_enum(status, _STATUSES, "status")
    client = utils.get_googleads_client()
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")

    operation = build_update_operation(
        client,
        "AdGroupCriterionOperation",
        ad_group_criterion_service.ad_group_criterion_path(
            clean_id(customer_id),
            clean_id(ad_group_id),
            clean_id(criterion_id),
        ),
        status=getattr(client.enums.AdGroupCriterionStatusEnum, status),
    )

    return run_mutate(
        "AdGroupCriterionService",
        "mutate_ad_group_criteria",
        customer_id,
        [operation],
        confirm,
    )


for _fn in (
    set_campaign_status,
    set_ad_group_status,
    set_ad_status,
    set_keyword_status,
):
    _fn.__doc__ = (_fn.__doc__ or "") + SAFETY_NOTE
    status_mcp.add_tool(
        Tool.from_function(
            _fn,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=True,
            ),
        )
    )
