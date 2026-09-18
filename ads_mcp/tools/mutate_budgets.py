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

"""Tools for changing campaign budgets and manual CPC bids.

Amounts are always expressed in the account's own currency (e.g. 25.50 for
NZD 25.50), not micros, and converted to the micros the API expects
internally.
"""

from typing import Any, Dict
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from fastmcp.exceptions import ToolError

import ads_mcp.utils as utils
from ads_mcp.tools.mutate_common import (
    SAFETY_NOTE,
    build_update_operation,
    clean_id,
    resolve_campaign_budget_resource_name,
    run_mutate,
)

budgets_mcp = FastMCP("budgets")


def _to_micros(amount: float, label: str) -> int:
    if amount <= 0:
        raise ToolError(f"{label} must be a positive amount, got {amount}.")
    return round(amount * 1_000_000)


def set_campaign_budget(
    customer_id: str | int,
    campaign_id: str | int,
    amount: float,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Sets the daily budget for the CampaignBudget attached to a campaign.

    If the budget is shared across multiple campaigns, this changes it for
    all of them - the preview response makes this clear since it validates
    against the real account state.

    Args:
        customer_id: The id of the customer that owns the campaign.
        campaign_id: The id of the campaign whose budget should change.
        amount: The new daily budget in the account's currency, e.g. 25.50.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    amount_micros = _to_micros(amount, "amount")
    client = utils.get_googleads_client()

    budget_resource_name = resolve_campaign_budget_resource_name(
        customer_id, campaign_id
    )

    operation = build_update_operation(
        client,
        "CampaignBudgetOperation",
        budget_resource_name,
        amount_micros=amount_micros,
    )

    return run_mutate(
        "CampaignBudgetService",
        "mutate_campaign_budgets",
        customer_id,
        [operation],
        confirm,
    )


def set_ad_group_cpc_bid(
    customer_id: str | int,
    ad_group_id: str | int,
    cpc_bid: float,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Sets the manual max CPC bid for an ad group.

    Only takes effect on campaigns using a manual CPC (or enhanced CPC)
    bidding strategy; the Google Ads API will reject this for campaigns on
    an automated bid strategy (Target CPA, Maximize Conversions, etc.) - the
    error will explain which strategy is in use.

    Args:
        customer_id: The id of the customer that owns the ad group.
        ad_group_id: The id of the ad group to change.
        cpc_bid: The new max CPC bid in the account's currency, e.g. 2.50.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    cpc_bid_micros = _to_micros(cpc_bid, "cpc_bid")
    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")

    operation = build_update_operation(
        client,
        "AdGroupOperation",
        ad_group_service.ad_group_path(
            clean_id(customer_id), clean_id(ad_group_id)
        ),
        cpc_bid_micros=cpc_bid_micros,
    )

    return run_mutate(
        "AdGroupService",
        "mutate_ad_groups",
        customer_id,
        [operation],
        confirm,
    )


def set_keyword_bid(
    customer_id: str | int,
    ad_group_id: str | int,
    criterion_id: str | int,
    cpc_bid: float,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Sets a keyword-level max CPC bid, overriding the ad group's bid for
    just this keyword.

    Only takes effect on campaigns using a manual CPC (or enhanced CPC)
    bidding strategy - see `budgets_set_ad_group_cpc_bid`.

    Args:
        customer_id: The id of the customer that owns the keyword.
        ad_group_id: The id of the ad group the keyword belongs to.
        criterion_id: The id of the keyword criterion to change (the
            ad_group_criterion.criterion_id field from a keyword_view
            query, not the keyword text).
        cpc_bid: The new max CPC bid in the account's currency, e.g. 2.50.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    cpc_bid_micros = _to_micros(cpc_bid, "cpc_bid")
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
        cpc_bid_micros=cpc_bid_micros,
    )

    return run_mutate(
        "AdGroupCriterionService",
        "mutate_ad_group_criteria",
        customer_id,
        [operation],
        confirm,
    )


for _fn in (set_campaign_budget, set_ad_group_cpc_bid, set_keyword_bid):
    _fn.__doc__ = (_fn.__doc__ or "") + SAFETY_NOTE
    budgets_mcp.add_tool(
        Tool.from_function(
            _fn,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=True,
            ),
        )
    )
