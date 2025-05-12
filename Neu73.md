Neuerungen in linuxmuster.net 7.3

# Zertifikatserneuerung

Zur Erneuerung der beim Setup erstellten selbstsignierten Zertifikate
gibt es das Skript  
*linuxmuster-renew-certs*:

* Usage: linuxmuster-renew-certs \[options\]*

* \[options\] may be:*

* -c \<list\>, --certs=\<list\> : Comma separated list of certificates
to be renewed*

* ("ca", "server" and/or "firewall" or "all").*

* -d \<#\>, --days=\<#\> : Set number of days (default: 7305).*

* -f, --force : Skip security prompt.*

* -n, --dry-run : Test only if the firewall certs can be renewed.*

* -r, --reboot : Reboot server and firewall finally.*

* -h, --help : Print this help.*

**Es wird empfohlen, vor der Erneuerung des Firewallzertifikats zu
überprüfen, ob die ursprünglich beim Setup erzeugte Zertifikatskette
noch gültig ist und das Zertifikat erneuert werden kann (Option *-n*).**

**Nach erfolgter Zertifikatserneuerung müssen Server und/oder Firewall
neu gestartet werden, damit Änderungen wirksam werden.**

**CA-, Server- und Firewallzertifikate könne unabhängig voneinander mit
unterschiedlicher Gültigkeitsdauer erneuert werden (Option** *-c*).**

**Wenn das CA-Zertifikat erneuert wird, müssen zwingend auch Server- und
Firewallzertifikat**e** erneuert werden, da diese auf der CA basieren.**

**Gültigkeitsdauer überprüfen:**

- **auf dem Server:**

* openssl x509 -in \<pem-Datei\> -noout -text*

* *

- **auf **der** Firewall:**

  - System: Sicherheit: Zertifikate

  - System: Zugang: Tester

    Dienste: Squid: Einmalige Anmeldung: Kerberos-Authentifizierung

- <https://github.com/linuxmuster/linuxmuster-base7/issues/158>
- <https://github.com/linuxmuster/linuxmuster-base7/blob/master/Renew_certs.md>

# Automatisches Image seeding

Während des Linbo-Bootvorganges werden automatisch
Torrent-Seeder-Prozesse für alle im Cache liegenden Images gestartet.

- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/127>

# Linbo-Konfiguration (start.conf)

Syntax der Linbo-start.conf wurde konsolidiert und obsolete Optionen
entfernt:

Server \| SystemType \| Version \| Image \| Boot \| Hidden

Aktuelle Beispiel-start.conf:

\[LINBO\]

Group = ubuntu

Cache = /dev/disk0p3

RootTimeout = 600

AutoPartition = no

AutoFormat = no

AutoInitCache = no

DownloadType = torrent

BackgroundFontColor = white

ConsoleFontColorStdout = lightgreen

ConsoleFontColorStderr = orange

KernelOptions = quiet splash

Locale = de-DE

\[Partition\]

Dev = /dev/disk0p1

Label = EFI

Size = 200M

Id = ef

FSType = vfat

Bootable = yes

\[Partition\]

Dev = /dev/disk0p2

Label = UBUNTU

Size = 30G

Id = 83

FSType = ext4

\[Partition\]

Dev = /dev/disk0p3

Label = CACHE

Size =

Id = 83

FSType = ext4

\[OS\]

Name = Ubuntu

Description = Ubuntu 24.04

IconName = ubuntu.svg

BaseImage = noble.qcow2

Root = /dev/disk0p1

Kernel = vmlinuz

Initrd = initrd.img

Append = ro splash

StartEnabled = yes

SyncEnabled = yes

NewEnabled = yes

Autostart = no

AutostartTimeout = 5

DefaultAction = sync

- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/132>
- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/131>

# Hardware-Info / verbessertes Logging

Mit dem Tool *hwinfo* kann die Hardware-Information des Clients
ausgelesen werden. Linbo erstellt pro Client einmalig eine gzippte
hwinfo-Datei und lädt sie nach */srv/linbo/log/\<hostname\>\_hwinfo.gz*
auf den Server.

Die Konsolen-Ausgaben des Linbo-Clients werden jetzt übersichtlicher in
eine Datei geloggt: */srv/linbo/log/\<hostname\>\_linbo.log.*

- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/117>
- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/123>

# Einheitliche Partitionsnamen

Unabhängig vom verbauten Festplattentyp (SATA, NVME etc.) können die
Partitionen jetzt mit einheitlichen Namen angesprochen werden.

Namensschema:

- 1\. Platte: */dev/disk0*
- 2\. Platte: */dev/disk1*
- ...
- 1\. Partition: */dev/disk0p1*
- 2\. Partition: */dev/disk0p2*
- …

Linbo legt beim Bootvorgang entsprechende Symlinks zu den tatsächlichen
Devices an.

Eine NVME-Disk wird immer als erste Platte (*disk0*) definiert.

Eine USB-Platte wird immer als letzte Platte definiert.

Aktuelles start.conf-Beispiel siehe oben.

- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/126>

# VNC-Server

Bei Verwendung des Linbo-Kernel-Parameters* vncserver *wird während des
Bootvorgangs ein VNC-Server gestartet. Der Dienst akzeptiert nur
Verbindungen von der Server-IP ausgehend auf Port 9999.

Legt man von seinem PC ausgehend einen SSH-Tunnel über den Server an  
*ssh -L 9999:\<Client-IP\>:9999 root@\<Server-IP\>*  
kann man danach direkt per *vncviewer localhost:9999* auf die
Linbo-Clientoberfläche zugreifen.

- <https://github.com/linuxmuster/linuxmuster-linbo7/issues/104>

<!-- -->

- <https://github.com/linuxmuster/linuxmuster-linbo7#linbo-kernel-parameters>

# Live-System von ISO booten

Stellt man eine ISO-Datei von einem Linux-Live-System als Imagedatei
bereit, kann diese bei entsprechender Konfiguration von der
Linbo-Clientoberfläche aus gestartet werden.

Vorgehensweise:

- ISO-Datei unter */srv/linbo/images* bereitstellen.

  - Beispiel: *ubuntu-24.04.2-desktop-amd64.iso*
  - auf dem Server unter  
    */srv/linbo/images/ubuntu-24.04.2-desktop-amd64/ubuntu-24.04.2-desktop-amd64.iso  
    *ablegen.
  - Torrent- und Info-Datei erzeugen mit  
    *linbo-torrent create ubuntu-24.04.2-desktop-amd64.iso*

- ISO-Datei auf dem PC mounten und

  - Pfade von Kernel und Initrd herausfinden (liegen in der obigen
    Beispiel-ISO im Verzeichnis *casper)*.
  - Kernel-Append-Parameter herausfinden (unter *boot/grub/grub.cfg*
    oder *isolinux.cfg*). Die Parameter *splash*, *quiet*, *findiso* und
    *iso-scan* können weggelassen werden, da sie automatisch erzeugt
    werden.

- OS-Abschnitt in die start.conf eintragen, bei *Root* die
  Cachepartition verwenden:

\[OS\]

Name = Ubuntu (Live)

Description = Ubuntu 24.04.2 Desktop Live

IconName = ubuntu.svg

BaseImage = ubuntu-24.04.2-desktop-amd64.iso

Root = /dev/disk0p3

Kernel = casper/vmlinuz

Initrd = casper/initrd

Append = locales=de_DE.UTF-8

StartEnabled = yes

SyncEnabled = no

NewEnabled = no

Autostart = no

AutostartTimeout = 5

DefaultAction = start

- Abschließend auf dem Server *linuxmuster-import-devices* aufrufen.

# Sonstiges

## Firmware

Firmware ist in Ubuntu 24.04 zst-komprimiert. Firmware-Dateien können in
*/etc/linuxmuster/linbo/firmware* aber wie bisher ohne .zst-Extension
angegeben werden.

## Kernel

Aktuelle Linbo-Kernelversionen:

- legacy: 6.1.\*
- longterm: 6.12.\*
- stable: 6.14.\*

## OPNsense-Firewall

Version 25 ist jetzt Installationsvoraussetzung.
