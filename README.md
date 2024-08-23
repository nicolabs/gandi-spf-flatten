# gandi-spf-flatten

Flatten SPF records with [Gandi LiveDNS API](https://api.gandi.net/docs/livedns/).

In its current state, the script is hard-coded for Gandi API but you may reuse and adapt the code for other domain providers.

I've taken one function from [cetanu/sender_policy_flattener](https://github.com/cetanu/sender_policy_flattener/blob/master/sender_policy_flattener/crawler.py)

## About SPF

This article describes the problem : https://smalltechstack.com/blog/flattening-your-spf-record

There are (were ?) some free online services (e.g. https://dmarcly.com/blog/spf-permerror-too-many-dns-lookups-when-spf-record-exceeds-10-dns-lookup-limit) but apparently you have to register one account different per domain, and I've tried but never received the confirmation email...

Other useful resources on SPF :
- [SPF Record Syntax](https://dmarcian.com/spf-syntax-table/)
- [Can I have a TXT or SPF record longer than 255 characters?](https://kb.isc.org/docs/aa-00356)

## Current manual

    usage: gandi-flatten-spf.py [-h] -d DOMAIN [DOMAIN ...] -e EMAIL_PROVIDERS [EMAIL_PROVIDERS ...] -E EMAIL_PROVIDERS_AS_IS [EMAIL_PROVIDERS_AS_IS ...] [-k API_KEY] [-r DNS [DNS ...]] [-l LOG_LEVEL]
                                [-L LOAD] [-K]

    Flatten SPF records using Gandi's Live DNS API

    options:
      -h, --help            show this help message and exit
      -d DOMAIN [DOMAIN ...], --domain DOMAIN [DOMAIN ...]
                            Domains you own from which to update the TXT record for SPF
      -e EMAIL_PROVIDERS [EMAIL_PROVIDERS ...], --email-providers EMAIL_PROVIDERS [EMAIL_PROVIDERS ...]
                            E-mail providers' SPF domains to add to the TXT record AFTER CONVERSION to a list of IP addresses
      -E EMAIL_PROVIDERS_AS_IS [EMAIL_PROVIDERS_AS_IS ...], --email-providers-as-is EMAIL_PROVIDERS_AS_IS [EMAIL_PROVIDERS_AS_IS ...]
                            E-mail providers' SPF domains to add to the TXT record AS-IS (no IP conversion)
      -k API_KEY, --api-key API_KEY
                            Your Gandi API key (otherwise looks for the 'GANDI_APIKEY' environment variable)
      -r DNS [DNS ...], --dns DNS [DNS ...]
                            DNS servers to use to resolve into IP addresses
      -l LOG_LEVEL, --log-level LOG_LEVEL
                            Log level
      -L LOAD, --load LOAD  A JSON file to load the result from Gandi's API instead of calling the API
      -K, --dry-run         Dry-run mode (will not change the records, only print)

The `-E` option was added because some providers only check that their domain appears in the DNS entries, not the corresponding IP (wrongly, in my opinion), so you can preserve the domains in the final TXT record.


## Example

    python gandi-flatten-spf.py -d mydomain.com -e _spf.google.com _spf.mail.yahoo.com _mailcust.gandi.net _spf.protonmail.ch -E _spf.mailfence.com -l DEBUG

Run without arguments to show the full syntax for your version (including how to pass your Gandi API key).

Put in a *cron job* to run on a regular basis and check if there was any change in the IP addresses of the email providers.

Without flattening, the 5 email providers from this example would produce 12 DNS requests, out of maximum 10 allowed.

## Sample crontab

The following cron entry will :
1. be triggered every hour
2. run the script for the given domain (i.e. flatten its *spf* record)
4. timeout if running more than 3 minutes
5. write debug logs into `/var/log/gandi-flatten-spf-mydomain.com.log`

Make sure to define the `GANDI_APIKEY` environment variable with the Gandi API key.

    @hourly timeout --signal=9 3m /opt/gandi-flatten-spf.py -k ${GANDI_APIKEY} -d mydomain.com -e _spf.mailfence.com _spf.google.com _spf.mail.yahoo.com _mailcust.gandi.net _spf.protonmail.ch -l DEBUG >/var/log/gandi-flatten-spf-mydomain.com.log 2>&1
