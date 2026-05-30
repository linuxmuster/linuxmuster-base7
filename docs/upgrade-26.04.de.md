# Upgrade auf linuxmuster.net 7.4 mit Ubuntu 26.04

## Voraussetzungen
- Falls OPNsense als Firewall verwendet wird, muss diese zuvor auf Version >= 26 aktualisiert werden. Außerdem müssen die bestehenden Firewallregeln ins neue Format migriert worden sein (s. https://www.thomas-krenn.com/en/wiki/OPNsense_26.1_Firewall_Rule_Migration).
- Der linuxmuster.net-7.3-Server muss vor dem Upgrade auf den aktuellen Stand gebracht werden. Falls nach dem Upgrade ein Reboot notwendig wird, diesen vorher durchführen.
- Der Server muss Verbindung zum Internet haben.

## Ablauf
- Als `root` auf der Serverkonsole einloggen. Falls per SSH eingeloggt wurde ggf. eine tmux-Session starten.
- Upgrade-Prozess starten mit `linuxmuster-release-upgrade` und die Sicherheitsabfrage mit "YES" bestätigen.
- Zu Beginn wird evtl. das Grub-Boot-Device abgefragt.
- Kaffee holen gehen.
- Nachdem das Upgrade durchgelaufen ist den Server neu starten.
- Fertig.