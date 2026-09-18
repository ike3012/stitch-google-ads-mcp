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

"""Test cases for the status (enable/pause/remove) mutate tools."""

import unittest
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError

from ads_mcp.tools import mutate_status
from tests.tools.mutate_fixtures import real_client


class TestSetCampaignStatus(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_preview_builds_correct_operation(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        result = mutate_status.set_campaign_status(
            customer_id="123-456-7890",
            campaign_id=999,
            status="paused",
            confirm=False,
        )

        self.assertTrue(result["preview"])
        _, kwargs = mock_service.mutate_campaigns.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(
            operation.update.resource_name, "customers/1234567890/campaigns/999"
        )
        self.assertEqual(operation.update.status.name, "PAUSED")
        self.assertTrue(kwargs["validate_only"])

    def test_invalid_status_raises_before_any_api_call(self):
        with self.assertRaises(ToolError):
            mutate_status.set_campaign_status(
                customer_id="1234567890", campaign_id=1, status="ARCHIVED"
            )


class TestSetAdStatus(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_ad_group_ad_path(self, mock_get_client, mock_get_service):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_status.set_ad_status(
            customer_id="1234567890",
            ad_group_id=111,
            ad_id=222,
            status="enabled",
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_ads.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(
            operation.update.resource_name,
            "customers/1234567890/adGroupAds/111~222",
        )
        self.assertEqual(operation.update.status.name, "ENABLED")


class TestSetKeywordStatus(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_ad_group_criterion_path(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_status.set_keyword_status(
            customer_id="1234567890",
            ad_group_id=111,
            criterion_id=333,
            status="removed",
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_criteria.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(
            operation.update.resource_name,
            "customers/1234567890/adGroupCriteria/111~333",
        )
        self.assertEqual(operation.update.status.name, "REMOVED")


if __name__ == "__main__":
    unittest.main()
