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

## Example

    python gandi-flatten-spf.py -d mydomain.com -e _spf.mailfence.com _spf.google.com _spf.mail.yahoo.com _mailcust.gandi.net _spf.protonmail.ch -l DEBUG

Run without arguments to show the full syntax (including how to pass your Gandi API key).

Put in a *cron* to run on a regular basis and check if there were any change in the IP addresses of the email providers.

Without flattening, the 5 email providers from this example would produce 12 DNS requests, out of maximum 10 allowed.
