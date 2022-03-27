"""Tests for certbot_dns_dinahosting._internal.dns_dinahosting."""

import unittest

try:
    import mock
except ImportError: # pragma: no cover
    from unittest import mock # type: ignore
from requests.exceptions import HTTPError

from certbot.compat import os
from certbot.plugins import dns_test_common
from certbot.plugins import dns_test_common_lexicon
from certbot.tests import util as test_util

USERNAME = 'foo'
PASSWORD = 'bar'


class AuthenticatorTest(test_util.TempDirTestCase,
                        dns_test_common_lexicon.BaseLexiconAuthenticatorTest):

    def setUp(self):
        super().setUp()

        from certbot_dns_dinahosting._internal.dns_dinahosting import Authenticator

        path = os.path.join(self.tempdir, 'file.ini')
        credentials = {
            "dinahosting_username": USERNAME,
            "dinahosting_password": PASSWORD,
        }
        dns_test_common.write(credentials, path)

        self.config = mock.MagicMock(dinahosting_credentials=path,
                                     dinahosting_propagation_seconds=0)  # don't wait during tests

        self.auth = Authenticator(self.config, "dinahosting")

        self.mock_client = mock.MagicMock()
        # _get_dinahosting_client | pylint: disable=protected-access
        self.auth._get_dinahosting_client = mock.MagicMock(return_value=self.mock_client)


class DinahostingLexiconClientTest(unittest.TestCase, dns_test_common_lexicon.BaseLexiconClientTest):
    DOMAIN_NOT_FOUND = Exception('Domain example.com not found')
    LOGIN_ERROR = HTTPError('2200 Client Error: Forbidden for url: https://dinahosting.com/api.php...')

    def setUp(self):
        from certbot_dns_dinahosting._internal.dns_dinahosting import _DinahostingLexiconClient

        self.client = _DinahostingLexiconClient(
            USERNAME, PASSWORD, 0
        )

        self.provider_mock = mock.MagicMock()
        self.client.provider = self.provider_mock


if __name__ == "__main__":
    unittest.main()  # pragma: no cover