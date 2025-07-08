certbot-dns-binarylane
==================
<a href="https://github.com/ALameLlama/certbot-dns-binarylane/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-Apache%20License%202.0-blue.svg" alt="License"></a>

[BinaryLane](https://www.binarylane.com.au/) DNS plugin for [Certbot](https://certbot.eff.org/) to authenticate and retrieve Lets Encrypt
certificates. Automates the process of completing a `dns-01` challenge by creating, and subsequently removing, `TXT` records .

It is based on a [Synergy Wholesale](https://synergywholesale.com) DNS plugin,
[certbot-dns-synergy-wholesale](https://github.com/ALameLlama/certbot-dns-synergy-wholesale/) created by [ALameLlama](https://github.com/ALameLlama/).

***To use this plugin the domain must be managed through BinaryLanes DNS service***

Installation
------------
```
# create a virtual environment, to avoid conflicts
python3 -m venv /some/path

# Clone the git repository
git clone (PATH TBC) /path/to/clone

# Change to newly cloned repository
cd /path/to/clone

# use the pip in the virtual environment to install 
/some/path/bin/pip install -e .

# use the cerbot from the virtualenv, to avoid accidentally
# using one from a different environment that does not have this library
/some/path/bin/certbot
```

Named Arguments
---------------
To start using DNS authentication for BinaryLane, pass the following arguments on certbot's command line:

| Option                                  | Description                                                                           |
|-----------------------------------------|---------------------------------------------------------------------------------------|
| `--authenticator dns-binarylane`           | select the authenticator plugin (Required)                                            |
| `--dns-binarylane-credentials FILE`        | credentials INI file. (Required)                                              |

Credentials
-----------

Use of this plugin requires a configuration file containing API credentials, obtained from the mpanel [Developer API
page](https://home.binarylane.com.au/api-info).

This plugin uses the file format of the [BinaryLane CLI tool](https://github.com/binarylane/binarylane-cli/tree/main) so it can use
`~/.config/binarylane/config.ini` generated for the API client

Remember this file will need to have 600 permissions.

`config.ini` is formatted thus:

``` {.sourceCode .ini}
[bl]
api-token = [long string of api token]
```

Examples
--------

To acquire a single certificate for both `example.com` and `*.example.com`

    certbot certonly \
      --authenticator dns-binarylane \
      --dns-binarylane-credentials /path/to/credentials.ini \
      -d 'example.com' \
      -d '*.example.com'

You can also add addtional paramaters such as `--keep-until-expiring --non-interactive --expand` for automation. More information [here](https://eff-certbot.readthedocs.io/en/stable/using.html#certbot-command-line-options)

