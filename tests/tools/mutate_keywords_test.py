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

"""Test cases for the add/remove keywords mutate tools."""

import unittest
from unittest.mock import MagicMock, patch

from fastmcp.exceptions import ToolError

from ads_mcp.tools import mutate_keywords
from tests.tools.mutate_fixtures import real_client


class TestAddKeywords(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_one_operation_per_keyword(
        self, mock_get_client, mock_get_service
    ):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_keywords.add_keywords(
            customer_id="1234567890",
            ad_group_id=111,
            keywords=[
                {"text": "running shoes", "match_type": "exact"},
                {
                    "text": "free shoes",
                    "match_type": "broad",
                    "negative": True,
                },
                {
                    "text": "trail shoes",
                    "match_type": "phrase",
                    "cpc_bid": 1.75,
                },
            ],
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_criteria.call_args
        ops = kwargs["operations"]
        self.assertEqual(len(ops), 3)

        self.assertEqual(ops[0].create.keyword.text, "running shoes")
        self.assertEqual(ops[0].create.keyword.match_type.name, "EXACT")
        self.assertFalse(ops[0].create.negative)

        self.assertEqual(ops[1].create.keyword.text, "free shoes")
        self.assertEqual(ops[1].create.keyword.match_type.name, "BROAD")
        self.assertTrue(ops[1].create.negative)

        self.assertEqual(ops[2].create.cpc_bid_micros, 1_750_000)
        self.assertEqual(
            ops[2].create.ad_group, "customers/1234567890/adGroups/111"
        )

    def test_empty_keywords_rejected(self):
        with self.assertRaises(ToolError):
            mutate_keywords.add_keywords(
                customer_id="1234567890", ad_group_id=111, keywords=[]
            )

    def test_invalid_match_type_rejected(self):
        with self.assertRaises(ToolError):
            mutate_keywords.add_keywords(
                customer_id="1234567890",
                ad_group_id=111,
                keywords=[{"text": "shoes", "match_type": "FUZZY"}],
            )

    def test_negative_keyword_with_bid_rejected(self):
        with self.assertRaises(ToolError):
            mutate_keywords.add_keywords(
                customer_id="1234567890",
                ad_group_id=111,
                keywords=[
                    {
                        "text": "shoes",
                        "match_type": "BROAD",
                        "negative": True,
                        "cpc_bid": 1.0,
                    }
                ],
            )


class TestRemoveKeywords(unittest.TestCase):
    @patch("ads_mcp.utils.get_googleads_service")
    @patch("ads_mcp.utils.get_googleads_client")
    def test_builds_remove_operations(self, mock_get_client, mock_get_service):
        mock_get_client.return_value = real_client()
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mutate_keywords.remove_keywords(
            customer_id="1234567890",
            ad_group_id=111,
            criterion_ids=[333, 444],
            confirm=False,
        )

        _, kwargs = mock_service.mutate_ad_group_criteria.call_args
        ops = kwargs["operations"]
        self.assertEqual(
            [op.remove for op in ops],
            [
                "customers/1234567890/adGroupCriteria/111~333",
                "customers/1234567890/adGroupCriteria/111~444",
            ],
        )

    def test_empty_criterion_ids_rejected(self):
        with self.assertRaises(ToolError):
            mutate_keywords.remove_keywords(
                customer_id="1234567890", ad_group_id=111, criterion_ids=[]
            )


if __name__ == "__main__":
    unittest.main()
