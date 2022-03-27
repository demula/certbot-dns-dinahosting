"""DNS Authenticator for Dinahosting DNS."""
import logging
from typing import Any
from typing import Callable
from typing import Optional

from lexicon.providers import dinahosting
from lexicon.exceptions import AuthenticationError
from requests import HTTPError

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins import dns_common_lexicon
from certbot.plugins.dns_common import CredentialsConfiguration

logger = logging.getLogger(__name__)


API_URL = 'https://dinahosting.com/special/api.php'


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Dinahosting

    This Authenticator uses the Dinahosting API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using Dinahosting for DNS)."
    ttl = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.credentials: Optional[CredentialsConfiguration] = None

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None],
                             default_propagation_seconds: int = 30) -> None:
        super().add_parser_arguments(add, default_propagation_seconds)
        add('credentials', help='Dinahosting credentials INI file.')

    def more_info(self) -> str:
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the Dinahosting API.'

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            'credentials',
            'Dinahosting credentials INI file',
            {
                'username': 'Username for Dinahosting API, obtained from {0}'
                    .format(API_URL),
                'password': 'Password for Dinahosting API, obtained from {0}'
                    .format(API_URL),
            }
        )

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_dinahosting_client().add_txt_record(domain, validation_name, validation)

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        self._get_dinahosting_client().del_txt_record(domain, validation_name, validation)

    def _get_dinahosting_client(self) -> "_DinahostingLexiconClient":
        if not self.credentials:  # pragma: no cover
            raise errors.Error("Plugin has not been prepared.")
        return _DinahostingLexiconClient(
            self.credentials.conf('username'),
            self.credentials.conf('password'),
            self.ttl
        )

class _DinahostingLexiconClient(dns_common_lexicon.LexiconClient):
    """
    Encapsulates all communication with the Dinahosting API via Lexicon.
    """

    def __init__(self, username: str, password: str, ttl: int) -> None:
        super().__init__()

        config = dns_common_lexicon.build_lexicon_config('dinahosting', {
            'ttl': ttl,
        }, {
            'auth_username': username,
            'auth_password': password,
        })

        self.provider = dinahosting.Provider(config)

    def _find_domain_id(self, domain: str) -> None:
        """
        Find the domain_id for a given domain.

        :param str domain: The domain for which to find the domain_id.
        :raises errors.PluginError: if the domain_id cannot be found.
        """

        domain_name_guesses = dns_common.base_domain_name_guesses(domain)

        for domain_name in domain_name_guesses:
            try:
                if hasattr(self.provider, 'options'):
                    # For Lexicon 2.x
                    self.provider.options['domain'] = domain_name
                else:
                    # For Lexicon 3.x
                    self.provider.domain = domain_name

                self.provider.authenticate()

                return  # If `authenticate` doesn't throw an exception, we've found the right name
            except AuthenticationError:
                continue
            except HTTPError as e:
                result1 = self._handle_http_error(e, domain_name)

                if result1:
                    raise result1
            except Exception as e:  # pylint: disable=broad-except
                result2 = self._handle_general_error(e, domain_name)

                if result2:
                    raise result2  # pylint: disable=raising-bad-type

        raise errors.PluginError('Unable to determine zone identifier for {0} using zone names: {1}'
                                 .format(domain, domain_name_guesses))

    def _handle_http_error(self, e: HTTPError, domain_name: str) -> errors.PluginError:
        hint = None
        if str(e).startswith('401 Client Error:'):
            hint = 'Are your username and password correct?'

        hint_disp = f' ({hint})' if hint else ''

        return errors.PluginError(f'Error determining zone identifier for {domain_name}: '
                                  f'{e}.{hint_disp}')

    def _handle_general_error(self, e: Exception, domain_name: str) -> Optional[errors.PluginError]:
        if domain_name in str(e) and str(e).endswith('not found'):
            return None

        return super()._handle_general_error(e, domain_name)
