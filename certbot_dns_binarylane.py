"""DNS Authenticator for BinaryLane"""
import logging
from typing import Any, Callable, Optional, Union

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

import requests

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for BinaryLane managed domains"""

    description = "Obtain certificates using a DNS TXT record from BinaryLane"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """ Initialise Authenticator class

        Required options:
          `name`: name of this plugin; 'binarylane'
        """
        super().__init__(*args, **kwargs)
        self.credentials: Optional[CredentialsConfiguration] = None

    @classmethod
    def add_parser_arguments(
        cls, add: Callable[..., None], default_propagation_seconds: int = 30
    ) -> None:
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="BinaryLane credentials INI file.")

    def more_info(self) -> str:
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the BinaryLane API."
        )

    @property
    def _provider_name(self) -> str:
        return "binarylane"

    def _validate(self, credentials) -> None:
        # Error messages indicated values are in the format dns_[plugin name]_[setting_name]; this seems to be working though
        if not credentials.confobj['bl']['api-token']:
            raise errors.PluginError(
                "Missing property in credentials configuration file {0}: {1}\nPerhaps this isn't a BinaryLane configuration file?".format(
                    credentials.confobj.filename, "api-token"
                )
            )

    def _setup_credentials(self) -> None:
        self.credentials = self._configure_credentials(
            "credentials",
            "Binarylane CLI configuration file",
            {
#                 "api-token": "BinaryLane API token",
            },
            self._validate,
        )

    # The certbot docs say to use perform() and cleanup() but DNSAuthenticator has _perform() and _cleanup() we can use instead (which are called by
    # the others)

    def _perform(self, domain, validation_name, validation) -> None:
        error = self._get_binarylane_client().add_txt_record(
          domain,
          validation_name,
          validation,
        )
        """
        Performs a dns-01 challenge by creating a DNS TXT record.

        :param str domain: The domain being validated.
        :param str validation_domain_name: The validation record domain name.
        :param str validation: The validation record content.
        :raises errors.PluginError: If the challenge cannot be performed
        """

        if error is not None:
            raise errors.PluginError(
                "An error occurred adding the DNS TXT record: {0}".format(error)
            )

    def _cleanup(self, domain, validation_name, validation) -> None:
        error = self._get_binarylane_client().del_txt_record(
            domain,
            validation,
        )
        """
        Deletes the DNS TXT record which would have been created by `_perform_achall`.

        Fails gracefully if no such record exists.

        :param str domain: The domain being validated.
        :param str validation_domain_name: The validation record domain name.
        :param str validation: The validation record content.
        """

        if error is not None:
            logger.warn("Unable to find or delete the DNS TXT record: %s", error)

    # I don't need to implement get_chall_pref; this is provided by DNSAuthenticator as we only have one option

    def _get_binarylane_client(self) -> "_BinaryLane":
        """Create instance of BL API client for use during Authentication"""
        if not self.credentials:
            raise errors.Error("Plugin has not been configured.")
        return _BinaryLane(
            self.credentials.confobj['bl']['api-token']
        )

class _BinaryLane:
    """
    Encapsulates all communication with the BinaryLane API.
    """
    request_endpoint = 'domains'

    def __init__(self, api_token) -> None:
        self.api_token = api_token
        self.client = requests.Session()
        self.binarylane_api_endpoint = "https://api.binarylane.com.au/v2"
        self.binarylane_api_auth_header = {
          "Authorization": "Bearer {0}".format(self.api_token),
        }

    def domainsplitter(self, full_domain):
      """Split domain in to parent and subdomains

      BinaryLane API requires the registered domain for its API interactions
      so we have to extract that from our FQDN.

      Returns tuple of (domain, subdomain)
      """

      # FIXME: do this better
      # extract the parent domain
      parentdomain = '.'.join(full_domain.split(sep='.')[-2:])
      # And extract the subdomain
      subdomain = full_domain.removesuffix('.' + parentdomain)

      return parentdomain, subdomain


    def add_txt_record(self, fullDomain, validation_name, validation) -> Union[str, None]:
      """Add txt records using API

      fullDomain is the domain being authenticated, eg www.example.com or demo.example.net; unused in tihs function
      validation_name is the FQDN used for validation, eg _acme-challenge.www.example.com
      validation is the content of the TXT record which will be created named validation_name.
      """

      domain, subdomain = self.domainsplitter(validation_name)

      request_post_data = {
        "type": "TXT",
        "name": "{0}".format(subdomain),
        "data": "{0}".format(validation),
        }

      response = self.client.request('POST', '{0}/{1}/{2}/{3}'.format(self.binarylane_api_endpoint, self.request_endpoint, domain, 'records'),
          headers=self.binarylane_api_auth_header, json=request_post_data)

      return None if response.ok else response.reason

    def del_txt_record(self, fullDomain, validation) -> Union[str, None]:
        """Delete records using API

        Unlike add_txt_record, this doesn't know which type of record is being removed and will remove anything find_txt_record_id says it should.

        domain is the top level domain, eg example.com
        validation is the content of the TXT record which will be removed.
        """

        domain, subdomain = self.domainsplitter(fullDomain)

        # Unfortunately removing is a two step process - list all the records, then delete the one we want
        validation_name_id = self.find_txt_record_id(domain, validation)

        # If we failed to get id, return early
        if validation_name_id is None:
            return "Failed to find record"

        response = self.client.request('DELETE', '{0}/{1}/{2}/records/{3}'.format(self.binarylane_api_endpoint, self.request_endpoint, domain,
              validation_name_id ), headers=self.binarylane_api_auth_header)

        # Expected results are 200 and 204 but leaving this open to others.
        return None if response.ok else response.reason

    def find_txt_record_id(self, domain, validation) -> Union[str, None]:
        """Helper function to locate specific record in list"""

        response = self.client.request('GET', '{0}/{1}/{2}/{3}'.format(self.binarylane_api_endpoint, self.request_endpoint, domain,
              'records?type=txt'), headers=self.binarylane_api_auth_header)

        # If we failed to get the zone, return early
        if response.status_code > 200:
            return None

        for record in response.json()["domain_records"]:
            if record["type"] == "TXT" and record["data"] == validation:
                return record["id"]
        return None

