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
import re
import subprocess
import time
import yaml

from bs4 import BeautifulSoup
from linuxmuster_base7.functions import firewallApi, getFwConfig, getSetupValue, getSubnetArray, isValidHostIpv4, printScript, putFwConfig, readTextfile, writeTextfile
from IPy import IP

# Constants for subnet field mappings
# Field numbers correspond to columns in subnets.csv:
# 0=network, 1=router, 2=range_start, 3=range_end, 4=nameserver, 5=nextserver
SUBNET_FIELDS = '1,2,3,4,5'  # Fields needed for DHCP subnet configuration

# Module-level execution code has been moved to main() function below


# Template variables - LAN gateway configuration
GW_LAN_DESCR = 'Interface LAN Gateway'
GW_LAN_XML_TPL = """
        <gateway_item>
            <interface>lan</interface>
            <gateway>@@gw_ip@@</gateway>
            <name>@@gw_lan@@</name>
            <weight>1</weight>
            <ipprotocol>inet</ipprotocol>
            <interval></interval>
            <descr>@@gw_lan_descr@@</descr>
            <avg_delay_samples></avg_delay_samples>
            <avg_loss_samples></avg_loss_samples>
            <avg_loss_delay_samples></avg_loss_delay_samples>
            <monitor_disable>1</monitor_disable>
        </gateway_item>
"""

# Template variables - Outbound NAT rules
NAT_RULE_DESCR = 'Outbound NAT rule for subnet'
NAT_RULE_XML_TPL = """
      <rule>
        <source>
          <network>@@subnet@@</network>
        </source>
        <destination>
          <any>1</any>
        </destination>
        <descr>@@nat_rule_descr@@ @@subnet@@</descr>
        <interface>wan</interface>
        <tag/>
        <tagged/>
        <poolopts/>
        <ipprotocol>inet</ipprotocol>
        <created>
          <username>root@@@serverip@@</username>
          <time>@@timestamp@@</time>
          <description>linuxmuster-import-subnet made changes</description>
        </created>
        <target/>
        <targetip_subnet>0</targetip_subnet>
        <sourceport/>
      </rule>
"""


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


def updateFwGw(servernet_router, content, gw_lan_xml):
    """Update VLAN gateway configuration in firewall XML.

    Modifies the firewall's gateway configuration by:
    - Parsing existing gateway items from XML
    - Removing old LAN gateway entries
    - Adding new LAN gateway with updated IP

    Args:
        servernet_router: IP address of the server network router
        content: Firewall XML configuration as string
        gw_lan_xml: Gateway XML template with placeholders

    Returns:
        Tuple of (success_boolean, modified_content_string)
    """
    soup = BeautifulSoup(content, features='xml')
    # get all gateways
    gateways = soup.find('Gateways')
    soup = BeautifulSoup(str(gateways), features='xml')
    # remove old lan gateway from gateways
    gw_array = []
    for gw_item in soup.findAll('gateway_item'):
        if GW_LAN_DESCR not in str(gw_item):
            gw_array.append(gw_item)
    # append new lan gateway
    gw_array.append(gw_lan_xml.replace('@@gw_ip@@', servernet_router))
    # create gateways xml code
    gateways_xml = '<gateways>'
    for gw_item in gw_array:
        gateways_xml = gateways_xml + str(gw_item)
    gateways_xml = gateways_xml + '\n' + '</gateways>'
    content = re.sub(r'<gateways>.*?</gateways>',
                     gateways_xml, content, flags=re.S)
    return True, content


def updateFwNat(subnets, ipnet_setup, nat_rule_xml, content):
    """Update subnet NAT rules in firewall XML configuration.

    Manages outbound NAT rules for subnets by:
    - Extracting existing NAT rules from XML
    - Removing old subnet-specific rules
    - Adding new NAT rules for each subnet (except server network)
    - Each rule allows outbound traffic from subnet to WAN

    Args:
        subnets: List of subnet strings in format 'network:gateway'
        ipnet_setup: Server network address (to be skipped)
        nat_rule_xml: NAT rule XML template with placeholders
        content: Firewall XML configuration as string

    Returns:
        Tuple of (success_boolean, modified_content_string)
    """
    # create array with all nat rules
    soup = BeautifulSoup(content, features='xml')
    out_nat = soup.findAll('outbound')[0]
    soup = BeautifulSoup(str(out_nat), features='xml')
    # remove old subnet rules from array
    nat_rules = []
    for item in soup.findAll('rule'):
        if NAT_RULE_DESCR not in str(item):
            nat_rules.append(item)
    # add new subnet rules to array
    for item in subnets:
        subnet = item.split(':')[0]
        # skip servernet
        if subnet == ipnet_setup:
            continue
        timestamp = str(datetime.datetime.now(datetime.timezone.utc).timestamp())
        nat_rule = nat_rule_xml.replace('@@subnet@@', subnet)
        nat_rule = nat_rule.replace('@@timestamp@@', timestamp)
        nat_rules.append(nat_rule)
    # create nat rules xml code
    nat_xml = '\n<outbound>\n<mode>hybrid</mode>\n'
    for nat_rule in nat_rules:
        nat_xml = nat_xml + str(nat_rule)
    nat_xml = nat_xml + '\n</outbound>'
    # replace code in config content
    content = re.sub(r'<outbound>.*?</outbound>', nat_xml, content, flags=re.S)
    return True, content


def updateFw(subnets, firewallip, ipnet_setup, servernet_router, gw_lan_xml, nat_rule_xml):
    """Download, modify and upload firewall configuration.

    Orchestrates firewall configuration updates:
    1. Downloads current config.xml from firewall
    2. Updates gateway configuration (via updateFwGw)
    3. Updates NAT rules (via updateFwNat)
    4. Uploads modified config back to firewall

    Args:
        subnets: List of subnet strings in format 'network:gateway'
        firewallip: IP address of the firewall
        ipnet_setup: Server network address
        servernet_router: Router IP for server network
        gw_lan_xml: Gateway XML template
        nat_rule_xml: NAT rule XML template

    Returns:
        Boolean indicating if changes were made, False on error
    """
    # first get config.xml
    if not getFwConfig(firewallip):
        return False
    # load configfile
    rc, content = readTextfile(environment.FWCONFLOCAL)
    if not rc:
        return rc
    changed = False
    # add vlan gateway to firewall
    rc, content = updateFwGw(servernet_router, content, gw_lan_xml)
    if rc:
        changed = rc
    # add subnet nat rules to firewall
    rc, content = updateFwNat(subnets, ipnet_setup, nat_rule_xml, content)
    if rc:
        changed = rc
    if changed:
        # write changed config
        if writeTextfile(environment.FWCONFLOCAL, content, 'w'):
            printScript('* Saved changed config.')
        else:
            printScript('* Unable to save configfile!')
            return False
        if not putFwConfig(firewallip):
            return False
    return changed


def addFwRoute(subnet):
    """Add a single static route to the firewall via API.

    Creates a new route entry on the firewall that directs
    traffic for the given subnet through the LAN gateway.

    Args:
        subnet: Network address in CIDR notation (e.g., '10.1.0.0/16')

    Returns:
        True if route was added successfully, False on error
    """
    try:
        payload = '{"route": {"network": "' + subnet + '", "gateway": "' + \
            environment.GW_LAN + '", "descr": "Route for subnet ' + \
            subnet + '", "disabled": "0"}}'
        res = firewallApi('post', '/routes/routes/addroute', payload)
        printScript('* Added route for subnet ' + subnet + '.')
        return True
    except Exception as error:
        printScript(f'* Unable to add route for subnet {subnet}: {error}')
        return False


def delFwRoute(uuid, subnet):
    """Delete a static route from the firewall by UUID.

    Removes a route entry from the firewall using the API.

    Args:
        uuid: Unique identifier of the route to delete
        subnet: Network address (used for logging only)

    Returns:
        True if route was deleted successfully, False on error
    """
    try:
        rc = firewallApi('post', '/routes/routes/delroute/' + uuid)
        printScript('* Route ' + uuid + ' - ' + subnet + ' deleted.')
        return True
    except Exception as error:
        printScript(f'* Unable to delete route {uuid} - {subnet}: {error}')
        return False


def updateFwRoutes(subnets, ipnet_setup, servernet_router):
    """Update all static routes on the firewall.

    Synchronizes firewall routes with subnets configuration:
    1. Fetches current routes from firewall
    2. Deletes non-compliant routes (wrong gateway or obsolete subnets)
    3. Adds missing routes for new subnets
    4. All routes use the LAN gateway (servernet_router)

    Args:
        subnets: List of subnet strings in format 'network:gateway'
        ipnet_setup: Server network address (to be skipped)
        servernet_router: Router IP for the server network

    Returns:
        Boolean indicating if changes were made, False on error
    """
    printScript('Updating subnet routing on firewall:')
    try:
        routes = firewallApi('get', '/routes/routes/searchroute')
        staticroutes_nr = len(routes['rows'])
        printScript('* Got ' + str(staticroutes_nr) + ' routes.')
    except Exception as error:
        printScript(f'* Unable to get routes: {error}')
        return False
    # iterate through firewall routes and delete them if necessary
    changed = False
    gateway_orig = environment.GW_LAN + ' - ' + servernet_router
    if staticroutes_nr > 0:
        count = 0
        while (count < staticroutes_nr):
            uuid = routes['rows'][count]['uuid']
            subnet = routes['rows'][count]['network']
            gateway = routes['rows'][count]['gateway']
            # delete not compliant routes
            if (subnet not in str(subnets) and gateway == gateway_orig) or (subnet in str(subnets) and gateway != gateway_orig):
                delFwRoute(uuid, subnet)
                printScript('* Route ' + subnet + ' deleted.')
                changed = True
            count += 1
    # get changed routes
    if changed:
        routes = firewallApi('get', '/routes/routes/searchroute')
    # find and collect routes to be added
    for subnet in subnets:
        # extract subnet from string
        s = subnet.split(':')[0]
        # skip server network
        if s == ipnet_setup:
            continue
        if s not in str(routes):
            rc = addFwRoute(s)
            if rc:
                changed = rc
    return changed
# Functions end


def main():
    """Main entry point for CLI tool.

    This function orchestrates the complete subnet import workflow:
    1. Reads setup configuration (server IP, network, firewall, etc.)
    2. Processes subnets from subnets.csv and generates DHCP configuration
    3. Restarts DHCP service with new configuration
    4. Updates netplan with static routes for subnets
    5. Updates NTP configuration
    6. Updates firewall gateway, NAT rules, and static routes (if not skipped)
    """
    # Step 1: Read necessary values from setup.ini
    serverip = getSetupValue('serverip')
    domainname = getSetupValue('domainname')
    gateway = getSetupValue('gateway')
    firewallip = getSetupValue('firewallip')
    skipfw = getSetupValue('skipfw')  # Boolean flag to skip firewall updates
    bitmask_setup = getSetupValue('bitmask')
    network_setup = getSetupValue('network')
    ipnet_setup = network_setup + '/' + bitmask_setup  # Server network in CIDR notation

    # Prepare XML templates for firewall configuration
    # Replace placeholders in gateway template
    gw_lan_xml = GW_LAN_XML_TPL.replace('@@gw_lan@@', environment.GW_LAN).replace(
        '@@gw_lan_descr@@', GW_LAN_DESCR)
    # Replace placeholders in NAT rule template
    nat_rule_xml = NAT_RULE_XML_TPL.replace(
        '@@nat_rule_descr@@', NAT_RULE_DESCR).replace('@@serverip@@', serverip)

    # Step 2: Process subnets and generate DHCP configuration
    printScript('linuxmuster-import-subnets')
    printScript('', 'begin')
    printScript('Setup values:')
    printScript('* Server address: ' + serverip)
    printScript('* Server network: ' + ipnet_setup)

    printScript('Reading subnets:')
    subnets = readSubnetsCSV(ipnet_setup)
    if not subnets:
        printScript('* No valid subnets found - aborting.')
        printScript('', 'end')
        return

    server_subnet    = next((s for s in subnets if s['is_server']), None)
    extra_subnets    = [s for s in subnets if not s['is_server']]
    servernet_router = server_subnet['router'] if server_subnet else firewallip
    # compat format for legacy firewall functions (will be removed in next commit)
    subnets_fw = [s['ipnet'] + ':' + s['router'] for s in subnets]

    # Step 3: Write DHCP configuration
    if not writeDhcpConfig(subnets, serverip):
        printScript('', 'end')
        return

    # Step 4: Restart DHCP service
    restartDhcp()

    # Step 5: Update netplan configuration with static routes for all subnets
    updateNetplan(extra_subnets, gateway, servernet_router)

    # Step 6: Update NTP configuration to reflect network changes
    subprocess.call('linuxmuster-update-ntpconf', shell=True)

    # Step 7: Update firewall configuration (unless skipfw is set)
    if not skipfw:
        # Update firewall gateway and NAT rules
        changed = updateFw(subnets_fw, firewallip, ipnet_setup,
                           servernet_router, gw_lan_xml, nat_rule_xml)
        if changed:
            # Apply gateway changes via firewall API
            changed = firewallApi('post', '/routes/routes/reconfigure')
            if changed:
                printScript('Applied new gateway.')

        # Update static routes on firewall
        changed = updateFwRoutes(subnets_fw, ipnet_setup, servernet_router)
        if changed:
            # Apply route changes via firewall API
            changed = firewallApi('post', '/routes/routes/reconfigure')
            if changed:
                printScript('Applied new routes.')

    printScript('', 'end')


if __name__ == '__main__':
    main()
