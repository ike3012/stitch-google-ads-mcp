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

"""Shared test helpers for the mutate tool test modules.

Does not match the `*_test.py` discovery pattern, so it is never collected
as a test module itself.
"""

from google.ads.googleads.client import GoogleAdsClient
from google.oauth2.credentials import Credentials


def real_client() -> GoogleAdsClient:
    """Builds a real GoogleAdsClient with a fake token.

    Building the client, resolving proto types (`get_type`), reading enums,
    and building resource paths (`*_path` helpers) are all pure/local
    operations that don't touch the network - only an actual RPC call (e.g.
    `mutate_campaigns`) would need real credentials. Tests patch
    `ads_mcp.utils.get_googleads_service` to intercept that call, so this
    fake-token client can safely be used for everything else, exercising the
    same proto-building code paths production uses.
    """
    return GoogleAdsClient(
        credentials=Credentials(token="fake-token"), use_proto_plus=True
    )
