# import_subnets.py README

- reads subnet definitions from the CSV file `/etc/linuxmuster/subnets.csv`. Example:
    ```
    # Network/Prefix ; Router-IP (last available IP in network) ; 1. Range-IP ; Last-Range-IP ; Nameserver (use lmn server if empty) ; nextserver (tftp server, leave empty for default) ; SETUP-Flag
    #
    # server subnet definition
    10.0.0.0/24;10.0.0.253;10.0.0.200;10.0.0.250;;;SETUP
    # add your subnets below
    10.0.100.0/24;10.0.100.254;10.0.100.200;10.0.100.250;;;
    10.0.200.0/24;10.0.200.254;10.0.200.200;10.0.200.250;;;
    ```
- By default only the server subnet `10.0.0.0/16` with gateway `10.0.0.254` is defined.
- When additional subnets are added, the server subnet prefix is changed to `/24`. A Layer-3 switch at `10.0.0.253` then acts as the LAN gateway.
- The IPv4 gateway address of each additional subnet has the value `254` in the last octet.
- The server subnet is identified by the `SETUP` flag in column 6 of the CSV, or by matching the network/prefix configured in `setup.ini`.
- Every skipped CSV row is logged with the reason via `printScript`.

## Requirements

`import_subnets.py` reads `subnets.csv` and performs the following actions:

### 1. DHCP configuration

Writes `/etc/dhcp/subnets.conf`. Example output:

```
# Subnet 10.0.0.0/24
subnet 10.0.0.0 netmask 255.255.255.0 {
option routers 10.0.0.253;
option subnet-mask 255.255.255.0;
option broadcast-address 10.0.0.255;
option netbios-name-servers 10.0.0.1;
range 10.0.0.200 10.0.0.250;
option host-name pxeclient;
}
# Subnet 10.0.100.0/24
subnet 10.0.100.0 netmask 255.255.255.0 {
option routers 10.0.100.254;
option subnet-mask 255.255.255.0;
option broadcast-address 10.0.100.255;
option netbios-name-servers 10.0.0.1;
range 10.0.100.200 10.0.100.250;
option host-name pxeclient;
}
# Subnet 10.0.200.0/24
subnet 10.0.200.0 netmask 255.255.255.0 {
option routers 10.0.200.254;
option subnet-mask 255.255.255.0;
option broadcast-address 10.0.200.255;
option netbios-name-servers 10.0.0.1;
range 10.0.200.200 10.0.200.250;
option host-name pxeclient;
}
```

After writing the file, `isc-dhcp-server` is restarted.

### 2. OPNsense firewall — LAN gateway (API: `/routing/settings/`)

If additional subnets exist:
- Creates a LAN gateway via `add_gateway` (payload key: `gateway_item`):
  - Name: `LAN_GW`
  - Interface: `lan`
  - Address family: IPv4 (`inet`)
  - Priority: 255
  - IP address: router of the server subnet (e.g. `10.0.0.253`)
  - Description: `Interface LAN Gateway`
  - Monitoring disabled
- If the gateway already exists with the correct IP, it is left unchanged.
- If it exists with a wrong IP, it is deleted and recreated.
- Applies changes via `/routing/settings/reconfigure`.

If no additional subnets exist:
- Deletes the `LAN_GW` gateway if present.

**Migration from `GW_LAN` (old name):**
If a gateway named `GW_LAN` is found (created by an older version of the script), it is automatically replaced by `LAN_GW`:
1. All static routes referencing `GW_LAN` are deleted first (and reconfigured) to satisfy the OPNsense dependency check.
2. The `GW_LAN` gateway is then deleted.
3. The new `LAN_GW` gateway is created.

### 3. OPNsense firewall — static routes (API: `/routes/routes/`)

- Adds one static route per additional subnet via `LAN_GW` (e.g. `10.0.100.0/24`, `10.0.200.0/24`).
- Deletes routes that are managed by this script (gateway name `LAN_GW`) but no longer defined in `subnets.csv`.
- Applies changes via `/routes/routes/reconfigure`.
- Note: the routes API returns the gateway field as the plain gateway name (`LAN_GW`), not as a full label.

### 4. OPNsense firewall — outbound NAT (API: `/firewall/source_nat/`)

- Adds one outbound NAT rule per additional subnet (source: subnet → destination: any, interface: WAN).
- Identifies its own rules by the description prefix `Outbound NAT rule for subnet`.
- Deletes rules with that prefix that are no longer defined in `subnets.csv`.
- Applies changes via `/firewall/source_nat/apply`.
- Rules are visible in the OPNsense WebUI under **Firewall → Automation → Source NAT**.

### 5. Netplan — server routing (`/etc/netplan/01-netcfg.yaml`)

- Sets the default route via `gateway` from `setup.ini`.
- Adds one static route per additional subnet via `servernet_router`, if `servernet_router != gateway` (i.e. a L3 switch is present).
- Creates a timestamped backup before any change; rolls back automatically if `netplan apply` fails.

### 6. NTP configuration

Calls `linuxmuster-update-ntpconf` after all changes to update the NTP configuration for the new networks.
