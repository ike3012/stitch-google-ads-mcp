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

"""Test cases for the create-responsive-search-ad mutate tool."""

import unittest
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError

from ads_mcp.tools import mutate_ads
from tests.tools.mutate_fixtures import real_client

_VALID_HEADLINES = ["Running Shoes", "Free Shipping", "Shop Now"]
_VALID_DESCRIPTIONS = ["Best trail shoes in NZ.", "Ships same day."]


class TestCreateResponsiveSearchAd(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_ad_with_headlines_and_descriptions(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_ads.create_responsive_search_ad(
            customer_id="1234567890",
            ad_group_id=111,
            headlines=_VALID_HEADLINES,
            descriptions=_VALID_DESCRIPTIONS,
            final_urls=["https://example.com/shoes"],
            path1="shoes",
            path2="sale",
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_ads.call_args
        operation = kwargs["operations"][0]
        rsa = operation.create.ad.responsive_search_ad
        self.assertEqual([h.text for h in rsa.headlines], _VALID_HEADLINES)
        self.assertEqual(
            [d.text for d in rsa.descriptions], _VALID_DESCRIPTIONS
        )
        self.assertEqual(rsa.path1, "shoes")
        self.assertEqual(rsa.path2, "sale")
        self.assertEqual(
            list(operation.create.ad.final_urls), ["https://example.com/shoes"]
        )

    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_defaults_to_paused_even_when_confirm_true(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.resource_name = "customers/123/adGroupAds/111~555"
        mock_service.mutate_ad_group_ads.return_value = MagicMock(
            results=[mock_result]
        )
        mock_get_service.return_value = mock_service

        mutate_ads.create_responsive_search_ad(
            customer_id="1234567890",
            ad_group_id=111,
            headlines=_VALID_HEADLINES,
            descriptions=_VALID_DESCRIPTIONS,
            final_urls=["https://example.com/shoes"],
            confirm=True,
        )

        _, kwargs = mock_service.mutate_ad_group_ads.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(operation.create.status.name, "PAUSED")

    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_start_paused_false_creates_enabled(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_ads.create_responsive_search_ad(
            customer_id="1234567890",
            ad_group_id=111,
            headlines=_VALID_HEADLINES,
            descriptions=_VALID_DESCRIPTIONS,
            final_urls=["https://example.com/shoes"],
            start_paused=False,
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_ads.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(operation.create.status.name, "ENABLED")

    def test_too_few_headlines_rejected(self):
        with self.assertRaises(ToolError):
            mutate_ads.create_responsive_search_ad(
                customer_id="1234567890",
                ad_group_id=111,
                headlines=["Only One"],
                descriptions=_VALID_DESCRIPTIONS,
                final_urls=["https://example.com"],
            )

    def test_too_few_descriptions_rejected(self):
        with self.assertRaises(ToolError):
            mutate_ads.create_responsive_search_ad(
                customer_id="1234567890",
                ad_group_id=111,
                headlines=_VALID_HEADLINES,
                descriptions=["Only one description here."],
                final_urls=["https://example.com"],
            )

    def test_no_final_urls_rejected(self):
        with self.assertRaises(ToolError):
            mutate_ads.create_responsive_search_ad(
                customer_id="1234567890",
                ad_group_id=111,
                headlines=_VALID_HEADLINES,
                descriptions=_VALID_DESCRIPTIONS,
                final_urls=[],
            )

    def test_headline_too_long_rejected(self):
        with self.assertRaises(ToolError):
            mutate_ads.create_responsive_search_ad(
                customer_id="1234567890",
                ad_group_id=111,
                headlines=["A" * 31, "Free Shipping", "Shop Now"],
                descriptions=_VALID_DESCRIPTIONS,
                final_urls=["https://example.com"],
            )

    def test_description_too_long_rejected(self):
        with self.assertRaises(ToolError):
            mutate_ads.create_responsive_search_ad(
                customer_id="1234567890",
                ad_group_id=111,
                headlines=_VALID_HEADLINES,
                descriptions=["A" * 91, "Ships same day."],
                final_urls=["https://example.com"],
            )


if __name__ == "__main__":
    unittest.main()
