# Renew self signed server and firewall certs

- To renew ca and server cert for another 20 years, invoke
  `/usr/share/linuxmuster/renew_server_cert.sh`
   on the server.
- Reboot the server to apply the new certs to all services.
- The updated certificate files are now located in `/etc/linuxmuster/ssl`.
- Import the ca key and the new ca cert in the OPNsense Web-UI:
  - Navigate to `System: Trust: Authorities`.
  - Edit the linuxmuster authority.
  - Choose `Method: Import an existing Authoritiy` from the dropdown menu.
  - Unfold the section `Output (PEM format)`.
  - Paste the content of `cacert.pem` into the field `Certificate data`.
  - Paste the content of `cakey.pem.extracted` into the field `Private key data`.
  - Save.
- Renew the firewall certificate:
  - Navigate to `System: Trust: Certificates`.
  - Edit the linuxmuster - firewall certificate.
  - Choose `Method: Reissue and replace certificate` from the dropdown menu.
  - Unfold the section `Key`.
  - Adjust `Lifetime (days)` to your needs.
  - Save.
- Reboot the firewall to apply the new certs to all services.
- Again in the OPNsense Web-UI navigate to `Services: Squid Web Proxy: Single Sign-On` and test the kerberos login.
- Note: It is safe to delete the file `cakey.pem.extracted` finally. It contains the ca key without password protection and is only needed for firewall import.
