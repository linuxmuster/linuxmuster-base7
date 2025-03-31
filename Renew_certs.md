# Renew self signed server and firewall certs

To renew ca, server and firewall certs invoke `linuxmuster-renew-certs` on the server:
  ```
  Usage: linuxmuster-renew-certs [options]
  [options] may be:
  -d <#>, --days=<#> : Set number of days (default: 7305).
  -f,     --force    : Skip security prompt.
  -n,     --dry-run  : Test only if the firewall certs can be renewed.
  -r,     --reboot   : Reboot server and firewall finally.
  -h,     --help     : print this help
  ```

Note:
- The script checks if the current firewall certificates are originally created by linuxmuster-setup and therefore are renewable. If this is not the case, the script aborts.
- You may test this with the option `-n` (recommended).
- You need to restart both server and firewall to apply the renewed certificates.
- After the firewall has rebooted, in the OPNsense Web-UI navigate to
  - `System: Access: Tester` and test authentication agains the linuxmuster server and to
  - `Services: Squid Web Proxy: Single Sign-On: Kerberos Authentication` and test the "Kerberos login".
