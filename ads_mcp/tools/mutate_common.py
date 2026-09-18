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

"""Shared helpers for the write/mutate tool modules.

This module intentionally defines no `FastMCP` instance, so `coordinator.py`
skips it when it scans `ads_mcp/tools/` for tool namespaces to mount.

Every mutate tool built on top of these helpers follows the same safety
contract: it defaults to a dry run (the Google Ads API's own `validate_only`
mode, which validates the request server-side without changing anything) and
only applies the change once the caller explicitly passes `confirm=True`.
"""

from typing import Any, Dict, List

from google.ads.googleads.errors import GoogleAdsException
from google.api_core import protobuf_helpers
from fastmcp.exceptions import ToolError

import ads_mcp.utils as utils

SAFETY_NOTE = """

### Safety
    This tool changes a live Google Ads account.

    By default (confirm=False) it runs the Google Ads API's own validate_only
    check: the request is fully validated server-side - required fields,
    permissions, entity state, and so on - but nothing is actually changed.
    The tool returns a preview describing what would happen.

    Re-run the exact same call with confirm=True to apply the change for
    real. Always show the user the preview result and get their go-ahead
    before setting confirm=True.
"""


def clean_id(entity_id: str | int) -> str:
    """Strips punctuation from a numeric Google Ads entity id (campaign, ad group, etc)."""
    return utils.clean_customer_id(entity_id)


def check_enum(value: str, valid_values: set[str], label: str) -> str:
    """Validates a caller-supplied enum-like string, raising a clear ToolError if invalid."""
    normalized = value.upper()
    if normalized not in valid_values:
        raise ToolError(
            f"Invalid {label} '{value}'. Must be one of {sorted(valid_values)}."
        )
    return normalized


def run_mutate(
    service_name: str,
    mutate_method: str,
    customer_id: str | int,
    operations: List[Any],
    confirm: bool,
) -> Dict[str, Any]:
    """Runs a `mutate_*` call in preview (validate_only) or applied mode.

    Args:
        service_name: The Google Ads service to call, e.g. "CampaignService".
        mutate_method: The mutate method name on that service, e.g.
            "mutate_campaigns".
        customer_id: The id of the customer that owns the resources being
            changed.
        operations: The list of `*Operation` proto messages to send.
        confirm: If False (the default), the request is sent with
            validate_only=True and nothing is changed. If True, the request
            is applied for real.

    Returns:
        A dict describing the outcome: `{"preview": True, ...}` for a dry
        run, or `{"preview": False, "applied": True, "results": [...]}` once
        applied.
    """
    customer_id = utils.clean_customer_id(customer_id)
    service = utils.get_googleads_service(service_name)
    mutate_fn = getattr(service, mutate_method)

    try:
        response = mutate_fn(
            customer_id=customer_id,
            operations=operations,
            validate_only=not confirm,
        )
    except GoogleAdsException as ex:
        error_msgs = [
            f"Google Ads API Error: {error.message}"
            for error in ex.failure.errors
        ]
        raise ToolError(
            f"Request ID: {ex.request_id}\n" + "\n".join(error_msgs)
        )

    if not confirm:
        return {
            "preview": True,
            "applied": False,
            "message": (
                "Validated only - no changes were applied. The request is "
                "valid as written. Call this tool again with confirm=True "
                "to apply it."
            ),
        }

    return {
        "preview": False,
        "applied": True,
        "results": [
            {"resource_name": result.resource_name}
            for result in response.results
        ],
    }


def build_update_operation(
    client: Any, operation_type_name: str, resource_name: str, **fields: Any
) -> Any:
    """Builds a `*Operation` with `update` populated and a matching update_mask.

    Works for any operation whose entity fields are simple scalars/enums set
    directly on the top-level message (status, amount_micros, cpc_bid_micros,
    ...). Nested repeated fields (keyword creation, ad copy) are built by
    hand in their own tool functions instead.

    Args:
        client: A GoogleAdsClient instance.
        operation_type_name: e.g. "CampaignOperation".
        resource_name: The resource name of the entity being updated.
        **fields: Field name/value pairs to set on the update, e.g.
            status=client.enums.CampaignStatusEnum.PAUSED.
    """
    operation = client.get_type(operation_type_name)
    entity = operation.update
    entity.resource_name = resource_name
    for field_name, value in fields.items():
        setattr(entity, field_name, value)
    client.copy_from(
        operation.update_mask,
        protobuf_helpers.field_mask(None, entity._pb),
    )
    return operation


def resolve_campaign_budget_resource_name(
    customer_id: str | int, campaign_id: str | int
) -> str:
    """Looks up the CampaignBudget resource name attached to a campaign."""
    from ads_mcp.tools.search import search

    clean_customer_id = utils.clean_customer_id(customer_id)
    rows = search(
        customer_id=clean_customer_id,
        fields=["campaign.campaign_budget", "campaign.name"],
        resource="campaign",
        conditions=[f"campaign.id = {clean_id(campaign_id)}"],
        limit=1,
    )
    if not rows:
        raise ToolError(
            f"No campaign with id {campaign_id} was found under customer "
            f"{clean_customer_id}."
        )
    return rows[0]["campaign.campaign_budget"]
