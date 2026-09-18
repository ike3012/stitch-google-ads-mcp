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

"""Tools for creating new ad copy.

The Google Ads API does not support editing an existing ad's headlines or
descriptions in place - the standard pattern is to create a new ad with the
copy you want and pause or remove the old one via `status_set_ad_status`.
"""

from typing import Any, Dict, List
from fastmcp import FastMCP
from fastmcp.tools import Tool
from mcp.types import ToolAnnotations
from fastmcp.exceptions import ToolError

import ads_mcp.utils as utils
from ads_mcp.tools.mutate_common import SAFETY_NOTE, clean_id, run_mutate

ads_mcp_ns = FastMCP("ads")

_MIN_HEADLINES, _MAX_HEADLINES = 3, 15
_MIN_DESCRIPTIONS, _MAX_DESCRIPTIONS = 2, 4
_MAX_ASSET_LEN = 30  # headlines: 30 chars, descriptions: 90 - checked below
_MAX_DESCRIPTION_LEN = 90


def create_responsive_search_ad(
    customer_id: str | int,
    ad_group_id: str | int,
    headlines: List[str],
    descriptions: List[str],
    final_urls: List[str],
    path1: str | None = None,
    path2: str | None = None,
    start_paused: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Creates a new responsive search ad in an ad group.

    Args:
        customer_id: The id of the customer that owns the ad group.
        ad_group_id: The id of the ad group to add the ad to.
        headlines: 3-15 headline strings, each up to 30 characters. Google
            rotates these automatically; order is not preserved.
        descriptions: 2-4 description strings, each up to 90 characters.
        final_urls: The landing page URL(s) for the ad, e.g.
            ["https://example.com/shoes"].
        path1: Optional first path segment shown after the domain in the ad
            (max 15 characters), e.g. "shoes".
        path2: Optional second path segment (max 15 characters), e.g. "sale".
        start_paused: If True (the default), the ad is created with status
            PAUSED so a human has to enable it before it can serve - even
            when confirm=True. Set False to create it already ENABLED.
        confirm: Set True to actually apply the change. Defaults to a
            validate-only dry run - see Safety below.
    """
    if not (_MIN_HEADLINES <= len(headlines) <= _MAX_HEADLINES):
        raise ToolError(
            f"headlines must contain between {_MIN_HEADLINES} and "
            f"{_MAX_HEADLINES} entries, got {len(headlines)}."
        )
    if not (_MIN_DESCRIPTIONS <= len(descriptions) <= _MAX_DESCRIPTIONS):
        raise ToolError(
            f"descriptions must contain between {_MIN_DESCRIPTIONS} and "
            f"{_MAX_DESCRIPTIONS} entries, got {len(descriptions)}."
        )
    if not final_urls:
        raise ToolError("final_urls must contain at least one URL.")
    for h in headlines:
        if len(h) > _MAX_ASSET_LEN:
            raise ToolError(
                f"Headline '{h}' is {len(h)} characters; max is "
                f"{_MAX_ASSET_LEN}."
            )
    for d in descriptions:
        if len(d) > _MAX_DESCRIPTION_LEN:
            raise ToolError(
                f"Description '{d}' is {len(d)} characters; max is "
                f"{_MAX_DESCRIPTION_LEN}."
            )

    client = utils.get_googleads_client()
    ad_group_service = client.get_service("AdGroupService")

    operation = client.get_type("AdGroupAdOperation")
    ad_group_ad = operation.create
    ad_group_ad.ad_group = ad_group_service.ad_group_path(
        clean_id(customer_id), clean_id(ad_group_id)
    )
    ad_group_ad.status = (
        client.enums.AdGroupAdStatusEnum.PAUSED
        if start_paused
        else client.enums.AdGroupAdStatusEnum.ENABLED
    )
    ad_group_ad.ad.final_urls.extend(final_urls)

    rsa = ad_group_ad.ad.responsive_search_ad
    for h in headlines:
        asset = client.get_type("AdTextAsset")
        asset.text = h
        rsa.headlines.append(asset)
    for d in descriptions:
        asset = client.get_type("AdTextAsset")
        asset.text = d
        rsa.descriptions.append(asset)
    if path1:
        rsa.path1 = path1
    if path2:
        rsa.path2 = path2

    return run_mutate(
        "AdGroupAdService",
        "mutate_ad_group_ads",
        customer_id,
        [operation],
        confirm,
    )


create_responsive_search_ad.__doc__ = (
    create_responsive_search_ad.__doc__ or ""
) + SAFETY_NOTE
ads_mcp_ns.add_tool(
    Tool.from_function(
        create_responsive_search_ad,
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=False,
            idempotentHint=False,
        ),
    )
)
