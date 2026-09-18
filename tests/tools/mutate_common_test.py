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

"""Test cases for the shared mutate helpers."""

import unittest
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError

from ads_mcp.tools import mutate_common
from tests.tools.mutate_fixtures import real_client


class TestCheckEnum(unittest.TestCase):
    def test_valid_value_is_normalized(self):
        self.assertEqual(
            mutate_common.check_enum("paused", {"ENABLED", "PAUSED"}, "status"),
            "PAUSED",
        )

    def test_invalid_value_raises(self):
        with self.assertRaises(ToolError) as ctx:
            mutate_common.check_enum("BOGUS", {"ENABLED", "PAUSED"}, "status")
        self.assertIn("Invalid status 'BOGUS'", str(ctx.exception))


class TestRunMutate(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_preview_defaults_to_validate_only_and_applies_nothing(
        self, mock_get_client, mock_get_service
    ):
        client = real_client()
        mock_get_client.return_value = client
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        operation = client.get_type("CampaignOperation")
        result = mutate_common.run_mutate(
            "CampaignService",
            "mutate_campaigns",
            "1234567890",
            [operation],
            confirm=False,
        )

        mock_service.mutate_campaigns.assert_called_once()
        _, kwargs = mock_service.mutate_campaigns.call_args
        request = kwargs["request"]
        self.assertTrue(request.validate_only)
        self.assertEqual(request.customer_id, "1234567890")

        self.assertTrue(result["preview"])
        self.assertFalse(result["applied"])

    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_confirm_applies_and_returns_resource_names(
        self, mock_get_client, mock_get_service
    ):
        client = real_client()
        mock_get_client.return_value = client
        mock_service = MagicMock()
        mock_result = MagicMock()
        mock_result.resource_name = "customers/123/campaigns/456"
        mock_service.mutate_campaigns.return_value = MagicMock(
            results=[mock_result]
        )
        mock_get_service.return_value = mock_service

        operation = client.get_type("CampaignOperation")
        result = mutate_common.run_mutate(
            "CampaignService",
            "mutate_campaigns",
            "123-456-7890",
            [operation],
            confirm=True,
        )

        _, kwargs = mock_service.mutate_campaigns.call_args
        request = kwargs["request"]
        self.assertFalse(request.validate_only)
        self.assertEqual(request.customer_id, "1234567890")

        self.assertFalse(result["preview"])
        self.assertTrue(result["applied"])
        self.assertEqual(
            result["results"],
            [{"resource_name": "customers/123/campaigns/456"}],
        )

    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_google_ads_exception_becomes_tool_error(
        self, mock_get_client, mock_get_service
    ):
        from google.ads.googleads.errors import GoogleAdsException

        client = real_client()
        mock_get_client.return_value = client
        mock_service = MagicMock()
        mock_error = MagicMock()
        mock_error.message = "Cannot pause a removed campaign."
        mock_failure = MagicMock()
        mock_failure.errors = [mock_error]

        mock_ex = GoogleAdsException(
            MagicMock(), MagicMock(), MagicMock(), MagicMock()
        )
        mock_ex.failure = mock_failure
        mock_ex.request_id = "req-999"
        mock_service.mutate_campaigns.side_effect = mock_ex
        mock_get_service.return_value = mock_service

        operation = client.get_type("CampaignOperation")
        with self.assertRaises(ToolError) as ctx:
            mutate_common.run_mutate(
                "CampaignService",
                "mutate_campaigns",
                "1234567890",
                [operation],
                confirm=True,
            )

        self.assertIn("Cannot pause a removed campaign.", str(ctx.exception))
        self.assertIn("req-999", str(ctx.exception))


class TestBuildUpdateOperation(unittest.TestCase):
    def test_sets_resource_name_field_and_update_mask(self):
        client = real_client()

        operation = mutate_common.build_update_operation(
            client,
            "CampaignOperation",
            "customers/123/campaigns/456",
            status=client.enums.CampaignStatusEnum.PAUSED,
        )

        self.assertEqual(
            operation.update.resource_name, "customers/123/campaigns/456"
        )
        self.assertEqual(
            operation.update.status, client.enums.CampaignStatusEnum.PAUSED
        )
        self.assertIn("status", list(operation.update_mask.paths))
        self.assertIn("resource_name", list(operation.update_mask.paths))


class TestResolveCampaignBudgetResourceName(unittest.TestCase):
    @patch("ads_mcp.tools.search.search")
    def test_returns_budget_resource_name(self, mock_search):
        mock_search.return_value = [
            {
                "campaign.campaign_budget": "customers/123/campaignBudgets/789",
                "campaign.name": "Search - Brand",
            }
        ]

        result = mutate_common.resolve_campaign_budget_resource_name(
            "1234567890", 456
        )

        self.assertEqual(result, "customers/123/campaignBudgets/789")
        mock_search.assert_called_once()
        _, kwargs = mock_search.call_args
        self.assertIn("campaign.id = 456", kwargs["conditions"])

    @patch("ads_mcp.tools.search.search")
    def test_missing_campaign_raises_tool_error(self, mock_search):
        mock_search.return_value = []

        with self.assertRaises(ToolError) as ctx:
            mutate_common.resolve_campaign_budget_resource_name(
                "1234567890", 999
            )
        self.assertIn("999", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
