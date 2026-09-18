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

"""Test cases for the budgets and bids mutate tools."""

import unittest
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError

from ads_mcp.tools import mutate_budgets
from tests.tools.mutate_fixtures import real_client


class TestSetCampaignBudget(unittest.TestCase):
    @patch("ads_mcp.tools.mutate_budgets.resolve_campaign_budget_resource_name")
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_converts_amount_to_micros(
        self, mock_get_client, mock_get_service, mock_resolve_budget
    ):
        mock_get_client.return_value = real_client()
        mock_resolve_budget.return_value = "customers/123/campaignBudgets/789"
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        result = mutate_budgets.set_campaign_budget(
            customer_id="1234567890",
            campaign_id=456,
            amount=25.5,
            confirm=False,
        )

        self.assertTrue(result["preview"])
        _, kwargs = mock_service.mutate_campaign_budgets.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(
            operation.update.resource_name, "customers/123/campaignBudgets/789"
        )
        self.assertEqual(operation.update.amount_micros, 25_500_000)

    def test_non_positive_amount_rejected(self):
        with self.assertRaises(ToolError):
            mutate_budgets.set_campaign_budget(
                customer_id="1234567890", campaign_id=456, amount=0
            )
        with self.assertRaises(ToolError):
            mutate_budgets.set_campaign_budget(
                customer_id="1234567890", campaign_id=456, amount=-5
            )


class TestSetKeywordBid(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_cpc_bid_update(self, mock_get_client, mock_get_service):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_budgets.set_keyword_bid(
            customer_id="1234567890",
            ad_group_id=111,
            criterion_id=333,
            cpc_bid=2.5,
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_criteria.call_args
        operation = kwargs["operations"][0]
        self.assertEqual(
            operation.update.resource_name,
            "customers/1234567890/adGroupCriteria/111~333",
        )
        self.assertEqual(operation.update.cpc_bid_micros, 2_500_000)


if __name__ == "__main__":
    unittest.main()
