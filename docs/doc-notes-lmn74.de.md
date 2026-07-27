# Anmerkungen zur Dokumentation von Setup und Linbo bzgl. lmn 7.4

## Installation

- Install-From-Scratch

  - Installation der OPNsense
    - Hinweis: Version muss mindestens 26.1 sein

## Ersteinrichtung

- Setup im Terminal
  
  - Screenshot "Welcome to lmn.net" erneuern
    - Screenshots erneuern:
      - Terminal Setup: Fortschritt des Setups
      - Terminal Setup: Abschluss des Setups

## Upgrade

- Upgrade v7.2 auf v7.3

  - Versionsnummern anpassen
  - Skriptaufruf: Pipe mit tee fällt weg, Ausgabe wird automatisch nach
    /var/log/linuxmuster/linuxmuster-release-upgrade.log geschrieben
  - school.conf-Anpassung fällt weg

## Migration auf linuxmuster 7.3

- kann ersatzlos gestrichen werden

## Clientverwaltung

- Bezeichnung LINBO4 durchgängig durch LINBO ersetzen, Hinweis, dass Versionierung
  jetzt an die lmn-Version angeglichen wird: 7.4
        
- LINBO nutzen
  - Alle Hinweise bzgl. Kernel streichen, stattdessen:
    "Ab LINBO 7.4 wird der Standardkernel von Ubuntu 26.04 verwendet (7.0.0)"
  - Hinweis: Bei der Image-Verteilung per torrent wurde ctorrent durch aria2 ersetzt.
  - Linbo-Gui hat sich nicht geändert, ggf. neue Screenshots wg. Versionsnummer
  - Änderungen in der start.conf:
    - im Abschnitt [LINBO] sind die Optionen `Server` und `SystemType` weggefallen.
            
- Linux-Kernel
  - s.o.
  - LINBO-Kernel wechseln
    Ein anderer Linbo-Kernel kann immer noch genutzt werden, indem eine Datei unter `/etc/linuxmuster/linbo/custom_kernel` bereitgestellt wird:
        ```
        ## currently active kernel image and modules used by the server
        ## path to kernel image
        KERNELPATH="/boot/vmlinuz-$(uname -r)"
        ## path to the corresponding modules directory
        MODULESPATH="/lib/modules/$(uname -r)"

        ## custom kernel image and modules
        #KERNELPATH="/path/to/my/kernelimage"
        ## path to the corresponding modules directory
        #MODULESPATH="/path/to/my/lib/modules/n.n.n"
        ```
  - Torrent
    - In `/etc/default/linbo-torrent` können jetzt die aria2-Optionen angepasst werden (s. https://aria2.github.io/manual/en/html/aria2c.html):
        ```
        # /etc/default/linbo-torrent
        #
        # aria2c options, only change that if you know exactly what you're doing.
        #
        # thomas@linuxmuster.net
        # 20260625
        #

        # used for both purposes
        ARIA2C_GLOBAL_OPTS="--enable-color=false --enable-dht=false --disable-ipv6=true"

        # used for torrent downloads
        ARIA2C_DWNLD_OPTS="-c --console-log-level=notice --show-console-readout=true --summary-interval=3 --seed-time=0"

        # used to seed torrents
        ARIA2C_SEED_OPTS="-V --seed-ratio=0.0"
        ```


Thomas Schmitt
thomas@linuxmuster.net
27.07.2026
