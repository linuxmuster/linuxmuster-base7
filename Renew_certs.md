# Renew self signed server and firewall certs

To renew ca, server and firewall certs invoke `linuxmuster-renew-certs` on the server:
  ```
------------------------------------------------------------------------------
#### linuxmuster-renew-certs started at 2025-04-09 18:05:42               ####
------------------------------------------------------------------------------
Usage: linuxmuster-renew-certs [options]
 [options] may be:
 -c <list>, --certs=<list> : Comma separated list of certificates to be renewed
                             ("ca", "server" and/or "firewall" or "all").
 -d <#>,    --days=<#>     : Set number of days (default: 7305).
 -f,        --force        : Skip security prompt.
 -n,        --dry-run      : Test only if the firewall certs can be renewed.
 -r,        --reboot       : Reboot server and firewall finally.
 -h,        --help         : Print this help.
  ```

Note:
- It is recommended to check beforehand whether the current firewall certificates were originally created by linuxmuster-setup and are therefore renewable. To do this, use the option `-n`.
- You need to restart both server and firewall to apply the renewed certificates.
- You may renew all certicicates seperately with different validity periods (see option `-c`).
- Note: If you renew the ca certificate, you have to renew also all other certificates, which depend on it.
- After the firewall has rebooted login to the OPNsense Web-UI and navigate to
  - `System: Trust: Authorities` and `System: Trust: Certificates` to see if the certificates have been renewed correctly,
  - `System: Access: Tester` to test authentication against the linuxmuster server and
  - `Services: Squid Web Proxy: Single Sign-On: Kerberos Authentication` to test the "Kerberos login".
