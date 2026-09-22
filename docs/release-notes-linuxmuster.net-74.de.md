Nach rund netto 32.000 neuen Zeilen Code in 1034 geänderten Dateien, verarbeitet in 1090 Commits, 93 Issues und 29 Pull Requests ist es endlich soweit: linuxmuster.net 7.4 ist released!

# linuxmuster.net 7.4

ist ein großes Wartungs- und Modernisierungsrelease: Die gesamte Software-Basis wurde auf Ubuntu 26.04 umgestellt, zentrale Komponenten wurden neu geschrieben und dabei zugleich robuster und sicherer gemacht. Die Änderungen gliedern sich in drei Bereiche – Setup und Servermanagement, Imaging und Clientmanagement und WebUI & Tools.

## Setup und Servermanagement

### Neues Fundament

Der komplette Python-Code des Pakets linuxmuster-base7 wurde unter Beachtung der Debian Python Policy neu strukturiert. Dabei wurden mehrere sicherheitsrelevante Schwachstellen geschlossen, unter anderem im Umgang mit Passwörtern und Shell-Befehlen. Die Anbindung der OPNsense-Firewall erfolgt seither über deren REST-API statt über SSH-Kommandos, was die Kommunikation robuster macht.

### Zuverlässigere Installation und Updates

Die Ersteinrichtung der Appliance und das anschließende Distributions-Update
wurden abgesichert: Das Update-Werkzeug löst jetzt auch Paketkonflikte
zuverlässig auf, die durch neue Abhängigkeiten entstehen. Die Quotaverwaltung wurde auf die moderne, ins Dateisystem integrierte Quota-Funktion von ext4 umgestellt.

### Zertifikate

Bei der Erzeugung und Erneuerung von Zertifikaten wurden Fehler behoben. Neu erzeugte Zertifikate enthalten jetzt den von modernen Browsern und Betriebssystemen erwarteten Subject Alternative Name.

### Stabiler Betrieb

Darüber hinaus wurden zahlreiche kleinere Fehler behoben, die im laufenden Betrieb auftreten konnten – bei der Firewall-Einrichtung, beim Single-Sign-On des Webproxys, bei der Quota- und Dateisystemverwaltung sowie beim Netzwerk-Setup.

## Imaging und Clientmanagement

### Modernisierte Basis

Bei LINBO, der Boot- und Imaging-Umgebung für die Clients, wurde der Bauprozess auf reguläre Ubuntu-Pakete und -Komponenten umgestellt: Clients starten jetzt mit dem Standard-Ubuntu-Kernel statt einem selbst kompilierten, und für die Imageverteilung per Torrent kommt statt des bisherigen `ctorrent` das etablierte `aria2c` zum Einsatz. Das macht Wartung und Absicherung deutlich einfacher.

### Windows-Treiberprofile

Linbo kann Windows-Treiber jetzt eigenständig anhand der Hardware-Kennung jedes Clients automatisch zuordnen und verteilen – ohne zusätzlichen Dienst oder Netzwerk-Port.
Hinweis: Das ist bisher nur grundlegend implementiert und die Bedienung ist aber noch spartanisch: Profile werden über die API oder direkt im Dateisystem angelegt und den Images zugewiesen, Oberflächen in WebUI und Kommandozeile fehlen bislang. Eine Schritt-für-Schritt-Anleitung gibt es [hier](https://github.com/linuxmuster/linuxmuster-linbo7/blob/main/docs/windows-treiberprofile-einrichten.de.md).

### Linbo-Fernsteuerung überarbeitet

`linbo-remote` wurde neu in Python geschrieben und um die Option `--dry-run` erweitert, die anzeigt, was ein Befehl auf dem Client bewirken würde, ohne ihn tatsächlich auszuführen.

### Zuverlässigkeit im laufenden Betrieb

Zahlreiche Korrekturen und Verbesserungen wurden umgesetzt in den Bereichen Integration von WLAN-Firmware, Unterstützung von USB-Netzwerkadaptern, Imageverteilung, Logging, Wake-on-LAN und Linbo-Fernsteuerung.

### Versionsschema angeglichen

Mit diesem Release wechselt Linbo von seiner bisherigen eigenen Versionsnummer (zuletzt 4.3.x) auf die linuxmuster.net-Versionierung 7.4.x.

## WebUI, API, Tools & Sophomorix

### Gemeinsame Bibliothek statt Insellösungen

Passwortverwaltung, LINBO-Steuerung, Drucker- und Gruppenmitgliedschaften sowie der Dateizugriff waren bisher mehrfach vorhanden – je einmal in der WebUI, in der Kommandozeile und in der API. Diese Implementierungen sind in der gemeinsamen Bibliothek linuxmuster-tools7 zusammengeführt worden; WebUI und CLI arbeiten jetzt über linuxmuster-api beziehungsweise direkt mit der Bibliothek.
Damit verschwindet eine Reihe von Verhaltensunterschieden, die je nach verwendetem Werkzeug zu unterschiedlichen Ergebnissen geführt haben.

### Passwortverwaltung

Die Passwortrichtlinien – Mindestlänge, Komplexität, Mindestalter – lassen sich jetzt in der WebUI pflegen, getrennt nach Schule und nach Rolle, und werden bei jeder Vergabe geprüft. Erst- und aktuelle Passwörter werden nicht mehr über sophomorix-Aufrufe auf der Shell gesetzt, sondern über die API. Mit `lmncli passwd` steht dieselbe Funktion auch auf der Kommandozeile zur Verfügung.

### LINBO in WebUI und API

Images und start.conf-Dateien lassen sich vollständig über die API verwalten: auflisten, umbenennen, duplizieren, löschen, Sicherungen zurückspielen sowie start.conf-Backups und die mitgelieferten Beispielkonfigurationen lesen. Beim Umbenennen oder Duplizieren eines Images werden Torrent- und Prüfsummendatei neu erzeugt – bisher blieben sie mit dem alten Dateinamen zurück, womit die Verteilung per Torrent nicht mehr funktionierte. Der Bootzustand der Clients (aus, LINBO, Linux, Windows) wird ohne nmap ermittelt, und die LINBO-Funktionen stehen jetzt auch Schuladministratoren offen, die sie über die Schulkonsole ohnehin schon hatten.

Der Bericht `lmncli linbo lastsync` zeigt zusätzlich, welchen Stand eines Images ein Rechner tatsächlich einsetzt – ein Client kann frisch synchronisiert sein und trotzdem eine alte Version fahren –, lässt sich auf auffällige Geräte filtern und benennt die Hardwareklasse in Tabelle und Export.

### Rechtetrennung und Sicherheit

Mehrere Endpunkte der API waren nicht sauber auf die Schule des Aufrufers begrenzt; ein Schuladministrator konnte unter anderem die Verwaltungslisten einer anderen Schule lesen und überschreiben. Diese Prüfungen sind nachgezogen worden. Zugriffsschlüssel (API-Keys) lassen sich auf eine Liste von Endpunkten einschränken, und die Begrenzung der Anmeldeversuche ist konfigurierbar – inklusive Ausnahmeliste für Portale, die alle ihre Benutzer von einer Adresse aus anmelden. Mit Ajenti 2.2.17 sind drei ohne Anmeldung erreichbare Schwachstellen des WebUI-Frameworks geschlossen, in der Kommandozeile wurde eine Shell-Injection behoben.

### Drucker, Gruppen und Klassen

Das gleichzeitige Eintragen mehrerer Benutzer oder Gruppen in einen Drucker blieb bisher ohne sichtbare Wirkung, und eine Änderung an der Mitgliederliste
konnte nebenbei die Schule oder die Sichtbarkeit des Druckers zurücksetzen. Mitgliedschaften werden jetzt in einem einzigen gezielten Schreibvorgang
gesetzt, so dass sich zwei gleichzeitige Änderungen nicht mehr gegenseitig überschreiben. Die Untergruppen einer Klasse (-teachers, -students, -parents)
werden durchgängig gepflegt und beim Löschen einer Klasse mit aufgeräumt; übrig gebliebene Reste lassen sich mit einem neuen Kommando finden. Für die LMNGroups gibt es einen eigenen Befehlssatz in der Kommandozeile.

### Zuverlässigkeit im laufenden Betrieb

Fehlgeschlagene LDAP-Schreibvorgänge werden gemeldet statt verschluckt: ein ungültiger Eintrag lässt den Rest eines Stapels nicht mehr unbemerkt liegen.
Kontingente werden auch dann korrekt angezeigt, wenn die Heimatverzeichnisse auf einem eigenen Fileserver liegen – bisher erschien dort „UNLIMITED“. Die
benutzerdefinierten Felder werden vollständig und für die richtige Schule gelesen. Dazu kommen zahlreiche kleinere Korrekturen in WebUI und Kommandozeile.

### Paketierung und Python-Umstellung

Die Laufzeitabhängigkeiten werden jetzt als Debian-Pakete installiert statt per pip. Die gemeinsame Python-Umgebung wird nach einem Distributionsupgrade
automatisch neu aufgebaut – sie merkt sich ihre Python-Version und wäre nach dem Wechsel auf Ubuntu 26.04 sonst funktionslos geblieben –, und ein neuer
dpkg-Trigger sorgt dafür, dass API, WebUI und CLI ihre eigenen Abhängigkeiten anschließend selbst wieder einspielen. Ein manueller Eingriff ist nicht nötig.

### sophomorix

Bei sophomorix selbst fiel der Zyklus bewusst klein aus, weil die Arbeit in den darüber liegenden Schichten stattgefunden hat: `sophomorix-class` räumt beim Löschen einer Klasse deren Untergruppen mit auf, das Format der Anmeldenamen (Trennzeichen, Muster, Maximallänge) ist konfigurierbar, und die Würfelpasswörter nutzen das Debian-Paket diceware statt einer Installation per pip.

## Ausführliche Release Notes

Für die Pakete von WebUI und Tools gibt es zusätzlich ausführliche Release
Notes mit allen Änderungen des 7.4-Zyklus:

- [linuxmuster-prepare](https://github.com/linuxmuster/linuxmuster-prepare/blob/master/docs/release-notes-74.de.md)
- [linuxmuster-common](https://github.com/linuxmuster/linuxmuster-common/blob/main/docs/release-notes-74.de.md)
- [linuxmuster-base7](https://github.com/linuxmuster/linuxmuster-base7/blob/master/docs/release-notes-74.de.md)
- [linuxmuster-linbo7](https://github.com/linuxmuster/linuxmuster-linbo7/blob/main/docs/release-notes-74.de.md)
- [linuxmuster-tools7 7.4](https://github.com/linuxmuster/linuxmuster-tools/blob/lmn74/release-notes-74.md)
- [linuxmuster-api 7.4](https://github.com/linuxmuster/linuxmuster-api/blob/lmn74/release-notes-74.md)
- [linuxmuster-webui7 7.4](https://github.com/linuxmuster/linuxmuster-webui7/blob/lmn74/release-notes-74.md)
- [linuxmuster-cli7 7.4](https://github.com/linuxmuster/linuxmuster-cli7/blob/main/release-notes-74.md)
- [sophomorix 7.4](https://github.com/linuxmuster/sophomorix4/blob/bionic/release-notes-74.md)

## Changelogs

Detaillierte Infos zu den Änderungen:

- [linuxmuster-prepare](https://github.com/linuxmuster/linuxmuster-prepare/compare/v7.4.0...master)
- [linuxmuster-common](https://github.com/linuxmuster/linuxmuster-common/compare/v7.4.0...main)
- [linuxmuster-base7](https://github.com/linuxmuster/linuxmuster-base7/compare/v7.4.0...master)
- [linuxmuster-linbo7](https://github.com/linuxmuster/linuxmuster-linbo7/compare/v7.4.0...main)
- [linuxmuster-tools7](https://github.com/linuxmuster/linuxmuster-tools/compare/v7.4.1...lmn74)
- [linuxmuster-api](https://github.com/linuxmuster/linuxmuster-api/compare/v7.4.1...lmn74)
- [linuxmuster-webui7](https://github.com/linuxmuster/linuxmuster-webui7/compare/v7.4.1...lmn74)
- [linuxmuster-cli7](https://github.com/linuxmuster/linuxmuster-cli7/compare/v7.4.1...main)
- [sophomorix](https://github.com/linuxmuster/sophomorix4/compare/v7.4.1...bionic)
- [ajenti](https://github.com/ajenti/ajenti/blob/master/CHANGELOG.txt)

(Erstellt mit Hilfe von Claude)