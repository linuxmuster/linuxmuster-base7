<?xml version="1.0"?>
<opnsense>
  <version>11.2</version>
  <theme>opnsense</theme>
  @@sysctl@@
  <system>
    <optimization>normal</optimization>
    <hostname>firewall</hostname>
    <domain>@@domainname@@</domain>
    <dnsallowoverride/>
    <group>
      <name>admins</name>
      <description>System Administrators</description>
      <scope>system</scope>
      <gid>1999</gid>
      <member>0</member>
      <priv>user-shell-access</priv>
      <priv>page-all</priv>
    </group>
    <user>
      <name>root</name>
      <descr>System Administrator</descr>
      <scope>system</scope>
      <groupname>admins</groupname>
      <password>@@fwrootpw_hashed@@</password>
      <uid>0</uid>
      <authorizedkeys>@@authorizedkey@@</authorizedkeys>
      <apikeys>
        <item>
          <key>@@apikey@@</key>
          <secret>@@apisecret_hashed@@</secret>
        </item>
      </apikeys>
    </user>
    <nextuid>2000</nextuid>
    <nextgid>2000</nextgid>
    <timezone>@@timezone@@</timezone>
    <time-update-interval>300</time-update-interval>
    <timeservers>pool.ntp.org</timeservers>
    <webgui>
      <protocol>https</protocol>
      <ssl-certref>598edde7a20b2</ssl-certref>
      <port/>
      <ssl-ciphers/>
      <compression/>
    </webgui>
    <disablenatreflection>yes</disablenatreflection>
    <usevirtualterminal>1</usevirtualterminal>
    <disableconsolemenu>1</disableconsolemenu>
    <disablechecksumoffloading>1</disablechecksumoffloading>
    <disablesegmentationoffloading>1</disablesegmentationoffloading>
    <disablelargereceiveoffloading>1</disablelargereceiveoffloading>
    <powerd_ac_mode>hadp</powerd_ac_mode>
    <powerd_battery_mode>hadp</powerd_battery_mode>
    <powerd_normal_mode>hadp</powerd_normal_mode>
    <bogons>
      <interval>monthly</interval>
    </bogons>
    <kill_states>1</kill_states>
    <backupcount>60</backupcount>
    <crypto_hardware>aesni</crypto_hardware>
    @@language@@
    <rulesetoptimization>basic</rulesetoptimization>
    <maximumstates/>
    <maximumfrags/>
    <aliasesresolveinterval/>
    <maximumtableentries/>
    <authserver>
      <refid>598c54fd2197e</refid>
      <type>ldap</type>
      <name>linuxmuster</name>
      <ldap_caref>598c5487e6d54</ldap_caref>
      <host>@@servername@@.@@domainname@@</host>
      <ldap_port>636</ldap_port>
      <ldap_urltype>SSL - Encrypted</ldap_urltype>
      <ldap_protver>3</ldap_protver>
      <ldap_scope>subtree</ldap_scope>
      <ldap_basedn>@@basedn@@</ldap_basedn>
      <ldap_authcn>OU=GLOBAL,@@basedn@@;OU=SCHOOLS,@@basedn@@</ldap_authcn>
      <ldap_extended_query>&amp;(objectClass=organizationalPerson)(memberOf=CN=internet,OU=Management,OU=default-school,OU=SCHOOLS,@@basedn@@)</ldap_extended_query>
      <ldap_attr_user>sAMAccountName</ldap_attr_user>
      <ldap_binddn>CN=global-binduser,OU=Management,OU=GLOBAL,@@basedn@@</ldap_binddn>
      <ldap_bindpw>@@binduserpw@@</ldap_bindpw>
    </authserver>
    <serialspeed>115200</serialspeed>
    <primaryconsole>video</primaryconsole>
    <ssh>
      <enabled>enabled</enabled>
      <passwordauth>1</passwordauth>
      <permitrootlogin>1</permitrootlogin>
    </ssh>
    @@dnsconfig@@
    <secondaryconsole>serial</secondaryconsole>
  </system>
  @@interfaces@@
  <dhcpd>
    <lan>
      <range>
        <from/>
        <to/>
      </range>
    </lan>
  </dhcpd>
  <unbound>
    <enable>1</enable>
    <dnssec>1</dnssec>
    <dnssecstripped>1</dnssecstripped>
    <domainoverrides>
      <domain>@@domainname@@</domain>
      <ip>@@serverip@@</ip>
      <descr>linuxmuster</descr>
    </domainoverrides>
    <hosts>
      <host>@@servername@@</host>
      <domain>@@domainname@@</domain>
      <rr>A</rr>
      <ip>@@serverip@@</ip>
      <mxprio/>
      <mx/>
      <descr>Server</descr>
    </hosts>
  </unbound>
  <snmpd>
    <syslocation/>
    <syscontact/>
    <rocommunity>public</rocommunity>
  </snmpd>
  <syslog>
    <reverse/>
  </syslog>
  <nat>
    <outbound>
      <mode>hybrid</mode>
    </outbound>
    <rule>
      <protocol>tcp</protocol>
      <interface>wan</interface>
      <ipprotocol>inet</ipprotocol>
      <descr>SSH -&gt; Server</descr>
      <tag/>
      <tagged/>
      <poolopts/>
      <associated-rule-id>pass</associated-rule-id>
      <target>@@serverip@@</target>
      <local-port>22</local-port>
      <source>
        <any>1</any>
      </source>
      <destination>
        <any>1</any>
        <port>22</port>
      </destination>
      <updated>
        <username>@@serverip@@</username>
        <time>1543615437.6122</time>
        <description>/firewall_nat_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1543615418.5415</time>
        <description>/firewall_nat_edit.php made changes</description>
      </created>
      <disabled>1</disabled>
    </rule>
    <rule>
      <protocol>tcp</protocol>
      <interface>wan</interface>
      <ipprotocol>inet</ipprotocol>
      <descr>LDAPS -&gt; Server</descr>
      <tag/>
      <tagged/>
      <poolopts/>
      <associated-rule-id>pass</associated-rule-id>
      <disabled>1</disabled>
      <target>@@serverip@@</target>
      <local-port>636</local-port>
      <source>
        <any>1</any>
      </source>
      <destination>
        <any>1</any>
        <port>636</port>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543615569.0833</time>
        <description>/firewall_nat_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1543615569.0833</time>
        <description>/firewall_nat_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <protocol>tcp</protocol>
      <interface>wan</interface>
      <ipprotocol>inet</ipprotocol>
      <descr>SMTP -&gt; Docker</descr>
      <tag/>
      <tagged/>
      <poolopts/>
      <associated-rule-id>pass</associated-rule-id>
      <disabled>1</disabled>
      <target>@@dockerip@@</target>
      <local-port>25</local-port>
      <source>
        <any>1</any>
      </source>
      <destination>
        <any>1</any>
        <port>25</port>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543615644.9298</time>
        <description>/firewall_nat_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1543615644.9298</time>
        <description>/firewall_nat_edit.php made changes</description>
      </created>
    </rule>
  </nat>
  <filter>
    <rule>
      <type>pass</type>
      <interface>lan</interface>
      <ipprotocol>inet</ipprotocol>
      <statetype>keep state</statetype>
      <descr>Allow Web-Proxy-Access</descr>
      <protocol>tcp</protocol>
      <source>
        <any>1</any>
      </source>
      <destination>
        <network>lanip</network>
        <port>3128</port>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543334054.0884</time>
        <description>/firewall_rules_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1502370804,8546</time>
        <description>/firewall_rules_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <type>pass</type>
      <interface>lan</interface>
      <ipprotocol>inet</ipprotocol>
      <statetype>keep state</statetype>
      <descr>Allow Radius Authentication</descr>
      <protocol>tcp</protocol>
      <source>
        <any>1</any>
      </source>
      <destination>
        <network>lanip</network>
        <port>1812</port>
      </destination>
      <created>
        <username>linuxmuster</username>
        <time>1502370804,8546</time>
        <description>/firewall_rules_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <type>pass</type>
      <interface>lan</interface>
      <ipprotocol>inet</ipprotocol>
      <statetype>keep state</statetype>
      <descr>Allow NoProxy-Group</descr>
      <source>
        <address>NoProxy</address>
      </source>
      <destination>
        <any>1</any>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543334093.1302</time>
        <description>/firewall_rules_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1502136054,2013</time>
        <description>/firewall_rules_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <type>pass</type>
      <interface>lan</interface>
      <ipprotocol>inet</ipprotocol>
      <statetype>keep state</statetype>
      <descr>Allow entire LAN</descr>
      <disabled>1</disabled>
      <source>
        <address>@@network@@/@@bitmask@@</address>
      </source>
      <destination>
        <any>1</any>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543334283.4894</time>
        <description>/firewall_rules_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1543255595.3165</time>
        <description>/firewall_rules_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <type>block</type>
      <interface>lan</interface>
      <ipprotocol>inet</ipprotocol>
      <statetype>keep state</statetype>
      <descr>Default deny LAN</descr>
      <source>
        <network>lan</network>
      </source>
      <destination>
        <network>wan</network>
      </destination>
      <updated>
        <username>linuxmuster</username>
        <time>1543334378.8434</time>
        <description>/firewall_rules_edit.php made changes</description>
      </updated>
      <created>
        <username>linuxmuster</username>
        <time>1502135862,7289</time>
        <description>/firewall_rules_edit.php made changes</description>
      </created>
    </rule>
    <rule>
      <type>pass</type>
      <ipprotocol>inet</ipprotocol>
      <descr>Default allow LAN to any rule</descr>
      <interface>lan</interface>
      <source>
        <network>lan</network>
      </source>
      <destination>
        <any/>
      </destination>
      <disabled>1</disabled>
    </rule>
    <rule>
      <type>pass</type>
      <ipprotocol>inet6</ipprotocol>
      <descr>Default allow LAN IPv6 to any rule</descr>
      <interface>lan</interface>
      <source>
        <network>lan</network>
      </source>
      <destination>
        <any/>
      </destination>
      <disabled>1</disabled>
    </rule>
  </filter>
  <rrd>
    <enable/>
  </rrd>
  <load_balancer>
    <monitor_type>
      <name>ICMP</name>
      <type>icmp</type>
      <descr>ICMP</descr>
      <options/>
    </monitor_type>
    <monitor_type>
      <name>TCP</name>
      <type>tcp</type>
      <descr>Generic TCP</descr>
      <options/>
    </monitor_type>
    <monitor_type>
      <name>HTTP</name>
      <type>http</type>
      <descr>Generic HTTP</descr>
      <options>
        <path>/</path>
        <host/>
        <code>200</code>
      </options>
    </monitor_type>
    <monitor_type>
      <name>HTTPS</name>
      <type>https</type>
      <descr>Generic HTTPS</descr>
      <options>
        <path>/</path>
        <host/>
        <code>200</code>
      </options>
    </monitor_type>
    <monitor_type>
      <name>SMTP</name>
      <type>send</type>
      <descr>Generic SMTP</descr>
      <options>
        <send/>
        <expect>220 *</expect>
      </options>
    </monitor_type>
  </load_balancer>
  <widgets>
    <sequence>system_information-container:00000000-col3:show,services_status-container:00000001-col4:show,gateways-container:00000002-col4:show,interface_list-container:00000003-col4:show</sequence>
    <column_count>2</column_count>
  </widgets>
  <revision>
    <username>linuxmuster</username>
    <time>1525283871.4696</time>
    <description>/firewall_rules_edit.php made changes</description>
  </revision>
  <OPNsense>
    <captiveportal version="1.0.0">
      <zones/>
      <templates/>
    </captiveportal>
    <cron version="1.0.0">
      <jobs/>
    </cron>
    <Netflow version="1.0.0">
      <capture>
        <interfaces/>
        <egress_only>wan</egress_only>
        <version>v9</version>
        <targets/>
      </capture>
      <collect>
        <enable>0</enable>
      </collect>
    </Netflow>
    <TrafficShaper version="1.0.1">
      <pipes/>
      <queues/>
      <rules/>
    </TrafficShaper>
    <IDS version="1.0.1">
      <rules/>
      <userDefinedRules/>
      <files/>
      <fileTags/>
      <general>
        <enabled>0</enabled>
        <ips>0</ips>
        <promisc>0</promisc>
        <interfaces>wan</interfaces>
        <homenet>192.168.0.0/16,10.0.0.0/8,172.16.0.0/12</homenet>
        <defaultPacketSize/>
        <UpdateCron/>
        <AlertLogrotate>W0D23</AlertLogrotate>
        <AlertSaveLogs>4</AlertSaveLogs>
        <MPMAlgo>ac</MPMAlgo>
        <syslog>0</syslog>
        <LogPayload>0</LogPayload>
      </general>
    </IDS>
    <proxy version="1.0.0">
      <general>
        <enabled>1</enabled>
        <icpPort/>
        <logging>
          <enable>
            <accessLog>1</accessLog>
            <storeLog>1</storeLog>
          </enable>
          <ignoreLogACL/>
          <target/>
        </logging>
        <alternateDNSservers/>
        <dnsV4First>0</dnsV4First>
        <forwardedForHandling>on</forwardedForHandling>
        <uriWhitespaceHandling>strip</uriWhitespaceHandling>
        <useViaHeader>1</useViaHeader>
        <suppressVersion>0</suppressVersion>
        <VisibleEmail>administrator@@@domainname@@</VisibleEmail>
        <VisibleHostname>firewall</VisibleHostname>
        <cache>
          <local>
            <enabled>0</enabled>
            <directory>/var/squid/cache</directory>
            <cache_mem>256</cache_mem>
            <maximum_object_size/>
            <size>100</size>
            <l1>16</l1>
            <l2>256</l2>
            <cache_linux_packages>0</cache_linux_packages>
            <cache_windows_updates>0</cache_windows_updates>
          </local>
        </cache>
        <traffic>
          <enabled>0</enabled>
          <maxDownloadSize>2048</maxDownloadSize>
          <maxUploadSize>1024</maxUploadSize>
          <OverallBandwidthTrotteling>1024</OverallBandwidthTrotteling>
          <perHostTrotteling>256</perHostTrotteling>
        </traffic>
      </general>
      <forward>
        <interfaces>lan</interfaces>
        <port>3128</port>
        <sslbumpport>3129</sslbumpport>
        <sslbump>0</sslbump>
        <sslurlonly>0</sslurlonly>
        <sslcertificate>598c5487e6d54</sslcertificate>
        <sslnobumpsites/>
        <ssl_crtd_storage_max_size>4</ssl_crtd_storage_max_size>
        <sslcrtd_children>5</sslcrtd_children>
        <ftpInterfaces/>
        <ftpPort>2121</ftpPort>
        <ftpTransparentMode>0</ftpTransparentMode>
        <addACLforInterfaceSubnets>1</addACLforInterfaceSubnets>
        <transparentMode>0</transparentMode>
        <acl>
          <allowedSubnets/>
          <unrestricted/>
          <bannedHosts/>
          <whiteList/>
          <blackList/>
          <browser/>
          <mimeType/>
          <safePorts>80:http,21:ftp,443:https,70:gopher,210:wais,1025-65535:unregistered ports,280:http-mgmt,488:gss-http,591:filemaker,777:multiling http</safePorts>
          <sslPorts>443:https</sslPorts>
          <remoteACLs>
            <blacklists/>
            <UpdateCron/>
          </remoteACLs>
        </acl>
        <icap>
          <enable>0</enable>
          <RequestURL>icap://127.0.0.1/reqmod</RequestURL>
          <ResponseURL>icap://127.0.0.1/respmod</ResponseURL>
          <SendClientIP>1</SendClientIP>
          <SendUsername>0</SendUsername>
          <EncodeUsername>0</EncodeUsername>
          <UsernameHeader>X-Username</UsernameHeader>
          <EnablePreview>1</EnablePreview>
          <PreviewSize>1024</PreviewSize>
          <OptionsTTL>60</OptionsTTL>
          <exclude/>
        </icap>
        <authentication>
          <method>linuxmuster</method>
          <realm>OPNsense proxy authentication</realm>
          <credentialsttl>2</credentialsttl>
          <children>5</children>
        </authentication>
      </forward>
    </proxy>
    <ProxyUserACL version="1.0.0">
      <general>
        <ACLs/>
      </general>
    </ProxyUserACL>
    <ProxySSO version="0.0.0">
      <EnableSSO>1</EnableSSO>
      <ADKerberosImplementation>W2008</ADKerberosImplementation>
      <KerberosHostName>FIREWALL-K</KerberosHostName>
    </ProxySSO>
    <freeradius>
      <user version="1.0.2">
        <users/>
      </user>
      <dhcp version="1.0.0">
        <dhcps/>
      </dhcp>
      <lease version="1.0.0">
        <leases/>
      </lease>
      <general version="1.0.0">
        <enabled>1</enabled>
        <vlanassign>0</vlanassign>
        <ldap_enabled>1</ldap_enabled>
        <wispr>0</wispr>
        <chillispot>0</chillispot>
        <mikrotik>0</mikrotik>
        <sqlite>0</sqlite>
        <sessionlimit>0</sessionlimit>
        <log_destination>files</log_destination>
        <log_authentication_request>0</log_authentication_request>
        <log_authbadpass>0</log_authbadpass>
        <log_authgoodpass>0</log_authgoodpass>
        <dhcpenabled>0</dhcpenabled>
        <dhcplistenip/>
        <mysql>0</mysql>
        <mysqlserver>127.0.0.1</mysqlserver>
        <mysqlport>3306</mysqlport>
        <mysqluser>radius</mysqluser>
        <mysqlpassword>radpass</mysqlpassword>
        <mysqldb>radius</mysqldb>
      </general>
      <eap version="1.0.0">
        <default_eap_type>mschapv2</default_eap_type>
        <enable_client_cert>1</enable_client_cert>
        <ca>598c5487e6d54</ca>
        <certificate>598edde7a20b2</certificate>
        <crl/>
      </eap>
      <client version="1.0.0">
        <clients>
          <client uuid="5db2f1d3-4097-4d0f-afe4-1b513d22548b">
            <enabled>1</enabled>
            <name>servernet</name>
            <secret>@@radiussecret@@</secret>
            <ip>@@network@@/@@bitmask@@</ip>
          </client>
        </clients>
      </client>
      <ldap version="1.0.0">
        <protocol>LDAPS</protocol>
        <server>@@servername@@.@@domainname@@</server>
        <identity>CN=global-binduser,OU=Management,OU=GLOBAL,@@basedn@@</identity>
        <password>@@binduserpw@@</password>
        <base_dn>OU=SCHOOLS,@@basedn@@</base_dn>
        <user_filter>(&amp;(objectClass=person)(sAMAccountName=%{%{Stripped-User-Name}:-%{User-Name}})(memberOf=CN=wifi,OU=Management,OU=*))</user_filter>
        <group_filter>(objectClass=group)</group_filter>
      </ldap>
    </freeradius>
  </OPNsense>
  <ppps/>
  <ca>
    <refid>598c5487e6d54</refid>
    <descr>linuxmuster</descr>
    <crt>@@cacertb64@@</crt>
  </ca>
  <cert>
    <refid>598edde7a20b2</refid>
    <descr>linuxmuster - firewall</descr>
    <crt>@@fwcertb64@@</crt>
    <prv>@@fwkeyb64@@</prv>
    <caref>598c5487e6d54</caref>
  </cert>
  <ntpd>
    <interface>lan</interface>
  </ntpd>
  <gateways>
    @@gwconfig@@
    <gateway_item>
      <interface>lan</interface>
      <gateway>@@firewallip@@</gateway>
      <name>@@gw_lan@@</name>
      <weight>1</weight>
      <ipprotocol>inet</ipprotocol>
      <interval/>
      <descr>Interface LAN Gateway</descr>
      <avg_delay_samples/>
      <avg_loss_samples/>
      <avg_loss_delay_samples/>
      <monitor_disable>1</monitor_disable>
    </gateway_item>
  </gateways>
  <staticroutes/>
  <aliases>
    <alias>
      <name>NoProxy</name>
      <type>host</type>
      <descr>NoProxy group</descr>
      <address>@@aliascontent@@</address>
      <detail/>
    </alias>
  </aliases>
</opnsense>
