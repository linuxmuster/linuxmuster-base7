# linuxmuster-base7 7.4.21

linuxmuster-base7 ist das zentrale Werkzeugpaket für die Einrichtung und
Verwaltung des Schulservers – Ersteinrichtung, Geräte- und Netzwerkverwaltung,
Zertifikate sowie die Anbindung der OPNsense-Firewall.

## Grundlegende Überarbeitung für Ubuntu 26.04

Mit 7.4.0 wurde der gesamte Python-Code neu strukturiert und auf ein reguläres
Python-Paket umgestellt. Dabei wurden mehrere sicherheitsrelevante Schwachstellen
geschlossen, unter anderem im Umgang mit Passwörtern und Shell-Befehlen. Die
Anbindung an die OPNsense-Firewall erfolgt seither über deren REST-API statt
über SSH-Kommandos.

## Zertifikatsverwaltung überarbeitet

Die Erneuerung des CA-Zertifikats war zeitweise fehlerhaft: Sie schlug beim
Aufruf fehl oder installierte das neue Zertifikat nicht korrekt im System.
Mit 7.4.21 wurde die Zertifikatserzeugung überarbeitet, die Erneuerung
funktioniert nun wieder zuverlässig. Neu erzeugte Zertifikate enthalten
außerdem die von modernen Browsern und Betriebssystemen erwartete
Zusatzangabe (Subject Alternative Name).

## Stabilität von Firewall, Netzwerk und Systemstart

In den Folgeversionen wurden zahlreiche kleinere Fehler behoben, die im
laufenden Betrieb auftreten konnten – bei der Firewall-Einrichtung (etwa beim
Zurücksetzen der Konfiguration und beim Single-Sign-On des Webproxys), bei
der Quota- und Dateisystemverwaltung sowie beim Netzwerk-Setup. Der
Systemstart läuft dadurch insgesamt zuverlässiger.

## Upgrade-Hinweis

Wegen der grundlegend geänderten Paketstruktur ist ein Umstieg vom Branch 7.3
nur gemeinsam mit dem Upgrade auf Ubuntu 26.04 möglich. Bestehende
Konfigurationsdateien bleiben davon unberührt.

Signed-off by: thomas@linuxmuster.net
Assisted by  : Claude
