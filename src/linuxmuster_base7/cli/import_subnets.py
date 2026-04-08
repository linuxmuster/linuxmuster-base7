#!/usr/bin/python3
#
# linuxmuster-import-subnets
# thomas@linuxmuster.net
# 20260326
#
# Requirements (import_subnets.md):
#  - Writes DHCP configuration to /etc/dhcp/subnets.conf
#  - Manages LAN gateway and static routes on OPNsense via API
#  - Removes obsolete routes / gateway when no extra subnets are present
#  - Synchronises outbound NAT rules on OPNsense via API
#  - Updates static routes in /etc/netplan/01-netcfg.yaml
#  - Calls linuxmuster-update-ntpconf

import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import csv
import datetime
import environment
import json
import subprocess
import time
import yaml

from IPy import IP
from linuxmuster_base7.functions import (
    firewallApi, getSetupValue, isValidHostIpv4, printScript
)

# LAN gateway constants
LAN_GW_NAME     = 'LAN_GW'
LAN_GW_NAME_OLD = 'GW_LAN'   # legacy name - replaced during migration
LAN_GW_DESCR    = 'Interface LAN Gateway'
LAN_GW_PRIORITY = '255'

# Outbound NAT constant - used as description prefix to identify own rules
NAT_RULE_DESCR = 'Outbound NAT rule for subnet'

# OPNsense API paths
# Note: verify paths against the installed OPNsense version
API_GW_SEARCH      = '/routing/settings/search_gateway'
API_GW_ADD         = '/routing/settings/add_gateway'
API_GW_DEL         = '/routing/settings/del_gateway/'
API_GW_RECONFIGURE = '/routing/settings/reconfigure'
API_RT_SEARCH      = '/routes/routes/searchroute'
API_RT_ADD         = '/routes/routes/addroute'
API_RT_DEL         = '/routes/routes/delroute/'
API_RT_RECONFIGURE = '/routes/routes/reconfigure'
API_NAT_SEARCH     = '/firewall/source_nat/search_rule'
API_NAT_ADD        = '/firewall/source_nat/add_rule'
API_NAT_DEL        = '/firewall/source_nat/del_rule/'
API_NAT_APPLY      = '/firewall/source_nat/apply'


# --------------------------------------------------------------------------- #
# CSV parsing                                                                  #
# --------------------------------------------------------------------------- #

def readSubnetsCSV(ipnet_setup):
    """Read subnets.csv and return a list of subnet dicts.

    CSV fields (semicolon-separated):
      0 network/prefix  1 router  2 range_start  3 range_end
      4 nameserver      5 nextserver              6 SETUP flag

    The server subnet is identified by the SETUP flag in column 6 or by
    matching ipnet_setup from setup.ini.

    Every skipped row is logged with its reason via printScript.

    Returns:
        List of dicts with keys:
          ipnet, router, range1, range2, nameserver, nextserver,
          network, netmask, broadcast, is_server
    """
    subnets = []
    try:
        infile = open(environment.SUBNETSCSV, newline='')
    except Exception as e:
        printScript(f'* Cannot open {environment.SUBNETSCSV}: {e}')
        return []

    with infile:
        reader = csv.reader(infile, delimiter=';', quoting=csv.QUOTE_NONE)
        for row in reader:
            # skip empty lines and comment/header lines
            if not row:
                continue
            first = row[0].strip()
            if not first or not first[0].isalnum():
                continue

            def field(i, default=''):
                return row[i].strip() if len(row) > i else default

            ipnet      = field(0)
            router     = field(1)
            range1     = field(2)
            range2     = field(3)
            nameserver = field(4)
            nextserver = field(5)
            setup_flag = field(6)

            # router IP is mandatory
            if not isValidHostIpv4(router):
                printScript(f'* Skipping {ipnet}: invalid router IP "{router}"')
                continue

            # compute network parameters from CIDR notation
            try:
                n         = IP(ipnet, make_net=True)
                network   = IP(n).strNormal(0)
                netmask   = IP(n).strNormal(2).split('/')[1]
                broadcast = IP(n).strNormal(3).split('-')[1]
                cidr      = network + '/' + str(IP(n).prefixlen())
            except Exception as e:
                printScript(f'* Skipping {ipnet}: invalid network notation: {e}')
                continue

            # validate optional IPs, clear on failure
            if not isValidHostIpv4(range1) or not isValidHostIpv4(range2):
                range1 = range2 = ''
            if not isValidHostIpv4(nameserver):
                nameserver = ''
            if not isValidHostIpv4(nextserver):
                nextserver = ''

            is_server = (setup_flag.upper() == 'SETUP') or (cidr == ipnet_setup)

            subnets.append({
                'ipnet':      cidr,
                'router':     router,
                'range1':     range1,
                'range2':     range2,
                'nameserver': nameserver,
                'nextserver': nextserver,
                'network':    network,
                'netmask':    netmask,
                'broadcast':  broadcast,
                'is_server':  is_server,
            })

    return subnets


# --------------------------------------------------------------------------- #
# DHCP configuration                                                           #
# --------------------------------------------------------------------------- #

def writeDhcpConfig(subnets, serverip):
    """Write /etc/dhcp/subnets.conf from the subnet list.

    Output format follows the specification in import_subnets.md (no indentation).

    Returns:
        True on success, False on error.
    """
    printScript('Writing DHCP configuration:')
    try:
        with open(environment.DHCPSUBCONF, 'w') as f:
            for s in subnets:
                printScript('* ' + s['ipnet'])
                f.write('# Subnet ' + s['ipnet'] + '\n')
                f.write('subnet ' + s['network'] + ' netmask ' + s['netmask'] + ' {\n')
                f.write('option routers ' + s['router'] + ';\n')
                f.write('option subnet-mask ' + s['netmask'] + ';\n')
                f.write('option broadcast-address ' + s['broadcast'] + ';\n')
                if s['nameserver']:
                    f.write('option domain-name-servers ' + s['nameserver'] + ';\n')
                else:
                    f.write('option netbios-name-servers ' + serverip + ';\n')
                if s['nextserver']:
                    f.write('next-server ' + s['nextserver'] + ';\n')
                if s['range1']:
                    f.write('range ' + s['range1'] + ' ' + s['range2'] + ';\n')
                f.write('option host-name pxeclient;\n')
                f.write('}\n')
        return True
    except Exception as e:
        printScript(f'* Failed to write {environment.DHCPSUBCONF}: {e}')
        return False


def restartDhcp():
    """Restart isc-dhcp-server and verify it is running.

    Returns:
        True if the service is active, False otherwise.
    """
    service = 'isc-dhcp-server'
    msg = 'Restarting ' + service + ' '
    printScript(msg, '', False, False, True)
    subprocess.call('service ' + service + ' stop', shell=True)
    subprocess.call('service ' + service + ' start', shell=True)
    time.sleep(1)
    rc = subprocess.call('systemctl is-active --quiet ' + service, shell=True)
    if rc == 0:
        printScript(' OK!', '', True, True, False, len(msg))
    else:
        printScript(' Failed!', '', True, True, False, len(msg))
    return rc == 0


# --------------------------------------------------------------------------- #
# Netplan                                                                      #
# --------------------------------------------------------------------------- #

def updateNetplan(extra_subnets, gateway, servernet_router):
    """Update static routes in /etc/netplan/01-netcfg.yaml.

    - Sets the default route via gateway
    - Adds one route per extra subnet via servernet_router, provided that
      servernet_router != gateway (i.e. a L3 switch is present)
    - Creates a timestamped backup before any change; rolls back automatically
      if 'netplan apply' fails

    Returns:
        True on success, False on error.
    """
    printScript('Updating netplan configuration:')
    cfgfile = environment.NETCFG
    timestamp = (str(datetime.datetime.now())
                 .replace('-', '').replace(' ', '').replace(':', '')
                 .split('.')[0])
    bakfile = cfgfile + '-' + timestamp
    if subprocess.call(['cp', cfgfile, bakfile]) != 0:
        printScript('* Failed to back up ' + cfgfile + '!')
        return False

    with open(cfgfile) as f:
        netcfg = yaml.safe_load(f)

    iface = str(netcfg['network']['ethernets']).split('\'')[1]
    ifcfg = netcfg['network']['ethernets'][iface]

    # remove deprecated gateway4 entry
    if 'gateway4' in ifcfg:
        del ifcfg['gateway4']
        printScript('* Removed deprecated gateway4 entry.')

    # remove existing routes
    if 'routes' in ifcfg:
        del ifcfg['routes']
        printScript('* Removed old routes.')

    # set default route
    ifcfg['routes'] = [{'to': 'default', 'via': gateway}]

    # add subnet routes if servernet_router differs from gateway
    if extra_subnets and servernet_router != gateway:
        for s in extra_subnets:
            ifcfg['routes'].append({'to': s['ipnet'], 'via': servernet_router})
        printScript('* Added routes for all extra subnets.')

    with open(cfgfile, 'w') as f:
        f.write(yaml.dump(netcfg, default_flow_style=False))

    if subprocess.call(['netplan', 'apply']) == 0:
        printScript('* New netplan configuration applied.')
        return True

    printScript('* netplan apply failed - rolling back.')
    subprocess.call(['cp', bakfile, cfgfile])
    subprocess.call(['netplan', 'apply'])
    return False


# --------------------------------------------------------------------------- #
# Firewall: version check                                                      #
# --------------------------------------------------------------------------- #

FW_MIN_VERSION = '26.1'

def checkFwVersion():
    """Check that the firewall runs at least FW_MIN_VERSION.

    Uses GET /core/firmware/info which returns 'product_version' at the
    top level (e.g. "26.1.2" or "26.7").

    Returns:
        True  if installed version >= FW_MIN_VERSION
        False on version mismatch or API error
    """
    res = firewallApi('get', '/core/firmware/info')
    if res is None:
        printScript('* Failed to retrieve firewall firmware info.')
        return False
    version_str = res.get('product_version', '')
    if not version_str:
        printScript('* Could not determine firewall version.')
        return False
    try:
        installed = tuple(int(x) for x in version_str.split('-')[0].split('.')[:2])
        required  = tuple(int(x) for x in FW_MIN_VERSION.split('.')[:2])
    except ValueError:
        printScript(f'* Unexpected firmware version format: {version_str}')
        return False
    if installed >= required:
        printScript(f'* Firewall version {version_str} OK.')
        return True
    printScript(f'* Firewall version {version_str} is too old.')
    return False


# --------------------------------------------------------------------------- #
# Firewall: LAN gateway (API)                                                  #
# --------------------------------------------------------------------------- #

def getFwGateway(name):
    """Look up a firewall gateway by name via API.

    Returns:
        (uuid, gateway_dict)  if found
        (None, None)          if not present
        (False, None)         on API error
    """
    res = firewallApi('get', API_GW_SEARCH)
    if res is None:
        printScript('* API error while fetching gateways.')
        return False, None
    for gw in res.get('rows', []):
        if gw.get('name') == name:
            return gw.get('uuid'), gw
    return None, None


def addFwGateway(router):
    """Create the LAN gateway on the firewall via API.

    The payload key must be 'gateway_item' as required by the OPNsense
    MVC framework (addBase("gateway_item", "gateway_item")).

    Returns:
        True on success, False on error.
    """
    payload = json.dumps({
        'gateway_item': {
            'name':            LAN_GW_NAME,
            'interface':       'lan',
            'ipprotocol':      'inet',
            'gateway':         router,
            'priority':        LAN_GW_PRIORITY,
            'descr':           LAN_GW_DESCR,
            'monitor_disable': '1',
        }
    })
    res = firewallApi('post', API_GW_ADD, payload)
    if res and res.get('result') == 'saved':
        printScript(f'* LAN gateway {LAN_GW_NAME} ({router}) created.')
        return True
    printScript(f'* Failed to create LAN gateway: {res}')
    return False


def delFwGateway(uuid, name):
    """Delete a firewall gateway by UUID via API.

    Returns:
        True on success, False on error.
    """
    res = firewallApi('post', API_GW_DEL + uuid)
    if res and res.get('result') == 'deleted':
        printScript(f'* Gateway {name} deleted.')
        return True
    printScript(f'* Failed to delete gateway {name} ({uuid}): {res}')
    return False


def delFwRoutesByGateway(gateway_name):
    """Delete all static routes that use a given gateway.

    Used during GW_LAN migration cleanup. The routes API returns the gateway
    field as the plain gateway name (e.g. "GW_LAN").

    Required to resolve the dependency before a gateway can be deleted.
    Applies changes immediately via API_RT_RECONFIGURE.

    Returns:
        True if all deletions succeeded, False on error.
    """
    res = firewallApi('get', API_RT_SEARCH)
    if res is None:
        printScript('* Failed to fetch routes.')
        return False
    ok = True
    deleted = False
    for route in res.get('rows', []):
        if route.get('gateway') != gateway_name:
            continue
        r = firewallApi('post', API_RT_DEL + route['uuid'])
        if r and r.get('result') == 'deleted':
            printScript(f'* Route {route["network"]} via {gateway_name} deleted.')
            deleted = True
        else:
            printScript(f'* Failed to delete route {route["network"]}.')
            ok = False
    if deleted:
        firewallApi('post', API_RT_RECONFIGURE)
    return ok


def updateFwGateway(extra_subnets, servernet_router):
    """Create or remove the LAN gateway depending on extra subnets.

    Also migrates a legacy GW_LAN gateway to LAN_GW:
    If a GW_LAN entry is found, all dependent static routes are deleted
    first, then the gateway is replaced by LAN_GW.

    - Extra subnets present: create gateway (or update IP if changed)
    - No extra subnets:      delete gateway if present

    Returns:
        True  if the gateway was actually created, deleted, or replaced
        False if the gateway was already in the desired state (no change)
        None  on API error
    """
    printScript('Updating LAN gateway on firewall:')

    # Migration: remove legacy GW_LAN if present
    old_uuid, old_gw = getFwGateway(LAN_GW_NAME_OLD)
    if old_uuid is False:
        return None  # API error
    if old_uuid is not None:
        printScript(f'* Legacy gateway {LAN_GW_NAME_OLD} found - replacing.')
        delFwRoutesByGateway(LAN_GW_NAME_OLD)
        if not delFwGateway(old_uuid, LAN_GW_NAME_OLD):
            return None

    uuid, gw = getFwGateway(LAN_GW_NAME)
    if uuid is False:
        return None  # API error

    if extra_subnets:
        if uuid is None:
            ok = addFwGateway(servernet_router)
            return True if ok else None
        if gw.get('gateway') != servernet_router:
            # wrong IP: recreate
            delFwGateway(uuid, LAN_GW_NAME)
            ok = addFwGateway(servernet_router)
            return True if ok else None
        printScript('* LAN gateway already correctly configured.')
        return False  # no change
    else:
        if uuid is not None:
            delFwRoutesByGateway(LAN_GW_NAME)
            ok = delFwGateway(uuid, LAN_GW_NAME)
            return True if ok else None
        printScript('* No LAN gateway present, nothing to remove.')
        return False  # no change


# --------------------------------------------------------------------------- #
# Firewall: static routes (API)                                                #
# --------------------------------------------------------------------------- #

def updateFwRoutes(extra_subnets, servernet_router):
    """Synchronise static routes on the firewall with extra_subnets.

    The routes API (/routes/routes/) validates gateways via the configd action
    'interface gateways list' (gateways.php), which reads OPNsense\\Routing\\Gateways
    model and returns gateway names as keys. Routes therefore reference gateways
    by their plain name (LAN_GW_NAME), not by UUID.

    Note: 'interface gateways list' has a 20-second configd cache. After a new
    gateway is created, the caller must wait for this cache to expire before
    calling updateFwRoutes, otherwise validation will fail. This is handled in
    main() by sleeping after a gateway change.

    - Deletes own routes (gateway == LAN_GW_NAME) that are no longer desired
    - Creates missing routes for new extra subnets

    Returns:
        True if changes were made,
        False if no changes were needed,
        None on API error.
    """
    printScript('Updating static routes on firewall:')

    res = firewallApi('get', API_RT_SEARCH)
    if res is None:
        printScript('* Failed to fetch routes from firewall.')
        return None

    existing = {r['network']: r for r in res.get('rows', [])}
    desired  = {s['ipnet'] for s in extra_subnets}
    changed  = False

    # delete obsolete own routes
    for network, route in existing.items():
        if route.get('gateway') != LAN_GW_NAME:
            continue  # foreign route - leave untouched
        if network not in desired:
            res = firewallApi('post', API_RT_DEL + route['uuid'])
            if res and res.get('result') == 'deleted':
                printScript(f'* Route {network} deleted.')
                changed = True
            else:
                printScript(f'* Failed to delete route {network}.')

    # create missing routes
    for ipnet in desired:
        if ipnet in existing:
            continue
        payload = json.dumps({
            'route': {
                'network':  ipnet,
                'gateway':  LAN_GW_NAME,
                'descr':    'Route for subnet ' + ipnet,
                'disabled': '0',
            }
        })
        res = firewallApi('post', API_RT_ADD, payload)
        if res and res.get('result') == 'saved':
            printScript(f'* Route {ipnet} created.')
            changed = True
        else:
            printScript(f'* Failed to create route {ipnet}: {res}')

    return changed


# --------------------------------------------------------------------------- #
# Firewall: outbound NAT (API)                                                 #
# --------------------------------------------------------------------------- #

def updateFwNat(extra_subnets):
    """Synchronise outbound NAT rules on the firewall with extra_subnets.

    Own rules are identified by the NAT_RULE_DESCR prefix in the description.
    - Deletes own rules whose subnet is no longer in extra_subnets
    - Creates missing rules for new extra subnets
    - Applies changes via API_NAT_APPLY

    NAT rules are visible in the OPNsense WebUI under
    Firewall -> Automation -> Source NAT.

    Returns:
        True if changes were successfully applied,
        False if no changes were needed or an error occurred.
    """
    printScript('Updating outbound NAT rules on firewall:')

    res = firewallApi('get', API_NAT_SEARCH)
    if res is None:
        printScript('* Failed to fetch NAT rules.')
        return False

    existing = {r['description']: r for r in res.get('rows', [])
                if r.get('description', '').startswith(NAT_RULE_DESCR)}
    desired  = {NAT_RULE_DESCR + ' ' + s['ipnet']: s['ipnet']
                for s in extra_subnets}
    changed  = False

    # delete obsolete own rules
    for descr, rule in existing.items():
        if descr not in desired:
            res = firewallApi('post', API_NAT_DEL + rule['uuid'])
            if res and res.get('result') == 'deleted':
                printScript(f'* NAT rule "{descr}" deleted.')
                changed = True
            else:
                printScript(f'* Failed to delete NAT rule "{descr}".')

    # create missing rules
    for descr, ipnet in desired.items():
        if descr in existing:
            continue
        payload = json.dumps({
            'rule': {
                'enabled':         '1',
                'interface':       'wan',
                'ipprotocol':      'inet',
                'source_net':      ipnet,
                'destination_net': 'any',
                'description':     descr,
            }
        })
        res = firewallApi('post', API_NAT_ADD, payload)
        if res and res.get('result') == 'saved':
            printScript(f'* NAT rule for {ipnet} created.')
            changed = True
        else:
            printScript(f'* Failed to create NAT rule for {ipnet}.')

    if changed:
        res = firewallApi('post', API_NAT_APPLY)
        if res:
            printScript('* NAT configuration applied.')
        else:
            printScript('* Failed to apply NAT configuration.')

    return changed


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def main():
    """Main entry point for linuxmuster-import-subnets.

    1. Read setup values (server IP, network, firewall IP)
    2. Check firewall version (>= 26.1 required; skipped if skipfw)
    3. Parse subnets.csv - every skipped row is logged
    4. Write /etc/dhcp/subnets.conf
    5. Restart isc-dhcp-server
    6. Update netplan routes
    7. Call linuxmuster-update-ntpconf
    8. Update firewall (only if skipfw is not set):
       - Create/remove LAN gateway via API
       - Synchronise static routes via API
       - Synchronise outbound NAT rules via API
    """
    # Step 1: read setup values
    serverip      = getSetupValue('serverip')
    gateway       = getSetupValue('gateway')
    firewallip    = getSetupValue('firewallip')
    skipfw        = getSetupValue('skipfw')
    bitmask_setup = getSetupValue('bitmask')
    network_setup = getSetupValue('network')
    ipnet_setup   = network_setup + '/' + bitmask_setup

    printScript('linuxmuster-import-subnets')
    printScript('', 'begin')

    # Version check - abort if firewall is too old
    printScript('Checking firewall version:')
    if not skipfw and not checkFwVersion():
        printScript(f'Please upgrade your OPNsense at least to Version >= {FW_MIN_VERSION}')
        printScript('', 'end')
        return

    printScript('Setup values:')
    printScript('* Server address: ' + serverip)
    printScript('* Server network: ' + ipnet_setup)

    # Step 2: parse subnets.csv
    printScript('Reading subnets:')
    subnets = readSubnetsCSV(ipnet_setup)
    if not subnets:
        printScript('* No valid subnets found - aborting.')
        printScript('', 'end')
        return

    server_subnet    = next((s for s in subnets if s['is_server']), None)
    extra_subnets    = [s for s in subnets if not s['is_server']]
    servernet_router = server_subnet['router'] if server_subnet else firewallip

    printScript(f'* {len(subnets)} subnet(s) total, '
                f'{len(extra_subnets)} extra subnet(s).')

    # Step 3: write DHCP configuration
    if not writeDhcpConfig(subnets, serverip):
        printScript('', 'end')
        return

    # Step 4: restart DHCP service
    restartDhcp()

    # Step 5: update netplan
    updateNetplan(extra_subnets, gateway, servernet_router)

    # Step 6: update NTP configuration
    printScript('Updating NTP configuration:')
    subprocess.call(['linuxmuster-update-ntpconf'])

    # Step 7: update firewall
    if skipfw:
        printScript('Skipping firewall updates (skipfw=True).')
    else:
        gw_changed = updateFwGateway(extra_subnets, servernet_router)
        if gw_changed is None:
            printScript('Gateway update failed - skipping routes and NAT.')
            printScript('', 'end')
            return
        if gw_changed:
            res = firewallApi('post', API_GW_RECONFIGURE)
            if res:
                printScript('New gateway applied.')
            else:
                printScript('Failed to apply gateway configuration.')
            # The configd 'interface gateways list' action has a 20-second
            # cache (cache_ttl:20 in actions_interface.conf). Route creation
            # validates against this cached list. Wait for the cache to expire
            # so the newly created gateway is visible to route validation.
            printScript('Waiting for gateway cache to expire...')
            time.sleep(22)

        rt_changed = updateFwRoutes(extra_subnets, servernet_router)
        if rt_changed:
            res = firewallApi('post', API_RT_RECONFIGURE)
            if res:
                printScript('New routes applied.')
            else:
                printScript('Failed to apply route configuration.')

        updateFwNat(extra_subnets)

    printScript('', 'end')


if __name__ == '__main__':
    main()
