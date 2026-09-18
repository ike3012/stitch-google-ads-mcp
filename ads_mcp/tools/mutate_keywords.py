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

"""Tools for adding and removing keywords (including negative keywords).

To change a keyword's status (pause/enable/remove) or its bid, see the
`status` and `budgets` tool namespaces - `keywords_remove_keywords` is for
deleting the criterion entirely, not pausing it.
"""

from typing import Any, Dict, List
from typing_extensions import TypedDict
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from fastmcp.exceptions import ToolError

import ads_mcp.utils as utils
from ads_mcp.tools.mutate_common import SAFETY_NOTE, clean_id, run_mutate

keywords_mcp = FastMCP("keywords")

_MATCH_TYPES = {"BROAD", "PHRASE", "EXACT"}


class KeywordInput(TypedDict, total=False):
    text: str
    match_type: str
    negative: bool
    cpc_bid: float


def add_keywords(
    customer_id: str | int,
    ad_group_id: str | int,
    keywords: List[KeywordInput],
    confirm: bool = False,
) -> Dict[str, Any]:
    """Adds one or more keywords (or negative keywords) to an ad group.

    Args:
        customer_id: The id of the customer that owns the ad group.
        ad_group_id: The id of the ad group to add keywords to.
        keywords: A list of keywords to add. Each item is a dict with:
            - text (required): the keyword text, e.g. "running shoes".
            - match_type (required): one of BROAD, PHRASE, EXACT.
            - negative (optional, default False): True to add as a negative
              keyword instead of a bid-eligible one.
            - cpc_bid (optional): a keyword-level max CPC bid in the
              account's currency, e.g. 2.50. Only takes effect on manual CPC
              campaigns.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    if not keywords:
        raise ToolError("keywords must contain at least one entry.")

    # Validate every entry up front, before touching credentials or building
    # any API objects, so a malformed request fails fast and cleanly.
    for i, kw in enumerate(keywords):
        text = kw.get("text")
        match_type = kw.get("match_type", "").upper()
        if not text:
            raise ToolError(f"keywords[{i}] is missing required field 'text'.")
        if match_type not in _MATCH_TYPES:
            raise ToolError(
                f"keywords[{i}] has invalid match_type '{kw.get('match_type')}'. "
                f"Must be one of {sorted(_MATCH_TYPES)}."
            )
        if kw.get("negative") and kw.get("cpc_bid") is not None:
            raise ToolError(
                f"keywords[{i}] is a negative keyword and cannot carry a "
                "cpc_bid."
            )

    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")
    ad_group_path = ad_group_service.ad_group_path(
        clean_id(customer_id), clean_id(ad_group_id)
    )

    operations = []
    for kw in keywords:
        text = kw["text"]
        match_type = kw["match_type"].upper()

        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = ad_group_path
        criterion.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
        criterion.negative = bool(kw.get("negative", False))
        criterion.keyword.text = text
        criterion.keyword.match_type = getattr(
            client.enums.KeywordMatchTypeEnum, match_type
        )
        if kw.get("cpc_bid") is not None:
            criterion.cpc_bid_micros = round(kw["cpc_bid"] * 1_000_000)

        operations.append(operation)

    return run_mutate(
        "AdGroupCriterionService",
        "mutate_ad_group_criteria",
        customer_id,
        operations,
        confirm,
    )


def remove_keywords(
    customer_id: str | int,
    ad_group_id: str | int,
    criterion_ids: List[str | int],
    confirm: bool = False,
) -> Dict[str, Any]:
    """Permanently removes one or more keyword criteria from an ad group.

    To temporarily turn a keyword off without losing its history, use
    `status_set_keyword_status` with status=PAUSED instead.

    Args:
        customer_id: The id of the customer that owns the keywords.
        ad_group_id: The id of the ad group the keywords belong to.
        criterion_ids: The ad_group_criterion.criterion_id values to remove
            (from a keyword_view query, not the keyword text).
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    if not criterion_ids:
        raise ToolError("criterion_ids must contain at least one entry.")

    client = utils.get_googleads_client()
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")

    operations = []
    for criterion_id in criterion_ids:
        operation = client.get_type("AdGroupCriterionOperation")
        operation.remove = ad_group_criterion_service.ad_group_criterion_path(
            clean_id(customer_id), clean_id(ad_group_id), clean_id(criterion_id)
        )
        operations.append(operation)

    return run_mutate(
        "AdGroupCriterionService",
        "mutate_ad_group_criteria",
        customer_id,
        operations,
        confirm,
    )


for _fn, _destructive in (
    (add_keywords, False),
    (remove_keywords, True),
):
    _fn.__doc__ = (_fn.__doc__ or "") + SAFETY_NOTE
    keywords_mcp.add_tool(
        Tool.from_function(
            _fn,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=_destructive,
                idempotentHint=False,
            ),
        )
    )
