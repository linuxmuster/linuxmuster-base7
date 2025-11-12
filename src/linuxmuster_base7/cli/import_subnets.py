#!/usr/bin/python3
#
# linuxmuster-import-subnets
# thomas@linuxmuster.net
# 20250721
#

import sys
sys.path.insert(0, '/usr/lib/linuxmuster')
import environment
import datetime
import re
import subprocess
import time
import yaml

from bs4 import BeautifulSoup
from linuxmuster_base7.functions import firewallApi, getFwConfig, getSetupValue, getSubnetArray, isValidHostIpv4, printScript, putFwConfig, readTextfile, writeTextfile
from IPy import IP

# read necessary values from setup.ini and other sources
serverip = getSetupValue('serverip')
domainname = getSetupValue('domainname')
gateway = getSetupValue('gateway')
firewallip = getSetupValue('firewallip')
# get boolean value
skipfw = getSetupValue('skipfw')
bitmask_setup = getSetupValue('bitmask')
network_setup = getSetupValue('network')
ipnet_setup = network_setup + '/' + bitmask_setup


# template variables

# lan gateway
gw_lan_descr = 'Interface LAN Gateway'
gw_lan_xml = """
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
gw_lan_xml = gw_lan_xml.replace('@@gw_lan@@', environment.GW_LAN).replace(
    '@@gw_lan_descr@@', gw_lan_descr)

# outbound nat rules
nat_rule_descr = 'Outbound NAT rule for subnet'
nat_rule_xml = """
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
nat_rule_xml = nat_rule_xml.replace(
    '@@nat_rule_descr@@', nat_rule_descr).replace('@@serverip@@', serverip)


# functions begin
# update static routes in netplan configuration
def updateNetplan(subnets):
    printScript('Processing netplan configuration:')
    cfgfile = environment.NETCFG
    # create backup of current configuration
    timestamp = str(datetime.datetime.now()).replace('-', '').replace(' ', '').replace(':', '').split('.')[0]
    bakfile = cfgfile + '-' + timestamp
    rc = subprocess.call('cp ' + cfgfile + ' ' + bakfile, shell=True)
    if rc != 0:
        printScript('* Failed to backup ' + cfgfile + '!')
        return False
    # read netplan config file
    with open(cfgfile) as config:
        netcfg = yaml.safe_load(config)
    iface = str(netcfg['network']['ethernets']).split('\'')[1]
    ifcfg = netcfg['network']['ethernets'][iface]
    # remove deprecated gateway4
    try:
        del ifcfg['gateway4']
        printScript('* Removed deprecated gateway4 statement.')
    except Exception as error:
        None
    # first delete the old routes if there are any
    try:
        del ifcfg['routes']
        printScript('* Removed old routes.')
    except Exception as error:
        None
    # set default route
    ifcfg['routes'] = []
    subroute = eval('{"to": \'default\', "via": \'' + gateway + '\'}')
    ifcfg['routes'].append(subroute)
    # add subnet routes if there are any beside server network
    if len(subnets) > 0:
        for item in subnets:
            # skip if subnet gateway is the default
            if servernet_router == gateway:
                continue
            subnet = item.split(':')[0]
            # tricky: concenate dict object for yaml using eval
            subroute = eval('{"to": \'' + subnet + '\', "via": \'' + servernet_router + '\'}')
            ifcfg['routes'].append(subroute)
        printScript('* Added new routes for all subnets.')
    # save netcfg
    with open(cfgfile, 'w') as config:
        config.write(yaml.dump(netcfg, default_flow_style=False))
    rc = subprocess.call('netplan apply', shell=True)
    if rc == 0:
        printScript('* Applied new netplan configuration.')
    else:
        printScript('* Failed to apply new netplan configuration. Rolling back to previous status.')
        subprocess.call('cp ' + bakfile + ' ' + cfgfile, shell=True)
        subprocess.call('netplan apply', shell=True)
        return False


# update vlan gateway on firewall
def updateFwGw(servernet_router, content):
    soup = BeautifulSoup(content, 'lxml')
    # get all gateways
    gateways = soup.findAll('gateways')[0]
    soup = BeautifulSoup(str(gateways), 'lxml')
    # remove old lan gateway from gateways
    gw_array = []
    for gw_item in soup.findAll('gateway_item'):
        if gw_lan_descr not in str(gw_item):
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


# update subnet nat rules on firewall
def updateFwNat(subnets, ipnet_setup, serverip, content):
    # create array with all nat rules
    soup = BeautifulSoup(content, 'lxml')
    out_nat = soup.findAll('outbound')[0]
    soup = BeautifulSoup(str(out_nat), 'lxml')
    # remove old subnet rules from array
    nat_rules = []
    for item in soup.findAll('rule'):
        if nat_rule_descr not in str(item):
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


# download, modify and upload firewall config
def updateFw(subnets, firewallip, ipnet_setup, serverip, servernet_router, gw_lan_xml):
    # first get config.xml
    if not getFwConfig(firewallip):
        return False
    # load configfile
    rc, content = readTextfile(environment.FWCONFLOCAL)
    if not rc:
        return rc
    changed = False
    # add vlan gateway to firewall
    rc, content = updateFwGw(servernet_router, content)
    if rc:
        changed = rc
    # add subnet nat rules to firewall
    rc, content = updateFwNat(subnets, ipnet_setup, serverip, content)
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


# add single route
def addFwRoute(subnet):
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


# delete route on firewall by uuid
def delFwRoute(uuid, subnet):
    try:
        rc = firewallApi('post', '/routes/routes/delroute/' + uuid)
        printScript('* Route ' + uuid + ' - ' + subnet + ' deleted.')
        return True
    except Exception as error:
        printScript(f'* Unable to delete route {uuid} - {subnet}: {error}')
        return False


# update firewall routes
def updateFwRoutes(subnets, ipnet_setup, servernet_router):
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
# functions end


# iterate over subnets
printScript('linuxmuster-import-subnets')
printScript('', 'begin')
printScript('Reading setup data:')
printScript('* Server address: ' + serverip)
printScript('* Server network: ' + ipnet_setup)
printScript('Processing dhcp subnets:')
servernet_router = firewallip
subnets = []
# collect subnet data and write dhcpd's subnet.conf
subnetconf = open(environment.DHCPSUBCONF, 'w')
for row in getSubnetArray():
    try:
        ipnet = row[0]
        router = row[1]
        range1 = row[2]
        range2 = row[3]
        nameserver = row[4]
    except Exception as error:
        continue
    try:
        nextserver = row[5]
    except Exception as error:
        nextserver = ''
    if ipnet[:1] == '#' or ipnet[:1] == ';' or not isValidHostIpv4(router):
        continue
    if not isValidHostIpv4(range1) or not isValidHostIpv4(range2):
        range1 = ''
        range2 = ''
    if not isValidHostIpv4(nameserver):
        nameserver = ''
    if not isValidHostIpv4(nextserver):
        nextserver = ''

    # compute network data
    try:
        n = IP(ipnet, make_net=True)
        network = IP(n).strNormal(0)
        netmask = IP(n).strNormal(2).split('/')[1]
        broadcast = IP(n).strNormal(3).split('-')[1]
    except Exception as error:
        continue
    # save servernet router address for later use
    if ipnet == ipnet_setup:
        servernet_router = router
        supp_info = 'server network'
    else:
        supp_info = ''
    subnets.append(ipnet + ':' + router)
    # write subnets.conf
    printScript('* ' + ipnet)
    subnetconf.write('# Subnet ' + ipnet + ' ' + supp_info + '\n')
    subnetconf.write('subnet ' + network + ' netmask ' + netmask + ' {\n')
    subnetconf.write('  option routers ' + router + ';\n')
    subnetconf.write('  option subnet-mask ' + netmask + ';\n')
    subnetconf.write('  option broadcast-address ' + broadcast + ';\n')
    if nameserver != '':
        subnetconf.write('  option domain-name-servers ' + nameserver + ';\n')
        nameserver = ''
    else:
        subnetconf.write('  option netbios-name-servers ' + serverip + ';\n')
    if nextserver != '':
        subnetconf.write('  next-server ' + nextserver + ';\n')
    if range1 != '':
        subnetconf.write('  range ' + range1 + ' ' + range2 + ';\n')
    subnetconf.write('  option host-name pxeclient;\n')
    subnetconf.write('}\n')

subnetconf.close()

# restart dhcp service
service = 'isc-dhcp-server'
msg = 'Restarting ' + service + ' '
printScript(msg, '', False, False, True)
subprocess.call('service ' + service + ' stop', shell=True)
subprocess.call('service ' + service + ' start', shell=True)
# wait one second before service check
time.sleep(1)
rc = subprocess.call('systemctl is-active --quiet ' + service, shell=True)
if rc == 0:
    printScript(' OK!', '', True, True, False, len(msg))
else:
    printScript(' Failed!', '', True, True, False, len(msg))

subprocess.call('systemctl restart isc-dhcp-server.service', shell=True)

# update netplan config with new routes for server (localhost)
changed = updateNetplan(subnets)

# update ntp.conf
subprocess.call('linuxmuster-update-ntpconf', shell=True)

# update firewall
if not skipfw:
    changed = updateFw(subnets, firewallip, ipnet_setup,
                       serverip, servernet_router, gw_lan_xml)
    if changed:
        changed = firewallApi('post', '/routes/routes/reconfigure')
        if changed:
            printScript('Applied new gateway.')
    changed = updateFwRoutes(subnets, ipnet_setup, servernet_router)
    if changed:
        changed = firewallApi('post', '/routes/routes/reconfigure')
        if changed:
            printScript('Applied new routes.')



def main():
    """Main entry point for CLI tool."""
    pass


if __name__ == '__main__':
    main()
