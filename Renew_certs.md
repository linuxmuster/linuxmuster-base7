# Renew self signed server and firewall certs

To renew ca, server and firewall certs invoke `linuxmuster-renew-certs` on the server:
  ```
  Usage: linuxmuster-renew-certs [options]
  [options] may be:
  -d <#>, --days=<#> : Set number of days (default: 7305).
  -f,     --force    : Skip security prompt.
  -r,     --reboot   : Reboot server and firewall finally.
  -h,     --help     : print this help
  ```

The script checks if the current firewall certificates are originally created by linuxmuster-setup. If this is not the case, the script aborts.
