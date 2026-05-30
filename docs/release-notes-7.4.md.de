# Release Notes – linuxmuster-base7 7.4

**Codename:** Beacon
**Zieldistribution:** Ubuntu 26.04 (Noble)
**Paketversion:** 7.4.x

---

## Übersicht

Version 7.4 ist eine umfangreiche Wartungs- und Refactoring-Version. Der gesamte
Python-Code wurde auf die Debian Python Policy (PEP 517/518) umgestellt, kritische
Sicherheitslücken wurden geschlossen und die OPNsense-Anbindung wurde auf die
REST-API migriert. Daneben wurden zahlreiche Fehler behoben und die Testinfrastruktur
grundlegend neu aufgebaut.

---

## Wichtige Änderungen

### Neue Python-Paketstruktur (Debian Python Policy)

Der gesamte Python-Code wurde in ein reguläres Python-Paket überführt und folgt nun
der Debian Python Policy:

- Neues Paket-Layout unter `src/linuxmuster_base7/` mit den Untermodulen `cli/` und
  `setup/`
- Alle CLI-Werkzeuge (`import_devices`, `import_subnets`, `setup`, `renew_certs`,
  `opnsense_reset`, `modini`, `update_ntpconf`, `holiday`, `holiday_generate`) sind
  jetzt reguläre Python-Module im Paket
- `pyproject.toml` (PEP 621) als zentrale Projektkonfiguration
- Die alten monolithischen Skripte unter `sbin/` und `lib/` wurden entfernt
- Alle Skripte werden nun nach `/usr/sbin/` statt `/usr/bin/` installiert

### Sicherheitsfixes

Mehrere kritische Sicherheitslücken wurden geschlossen:

- **Shell-Injection in SSH-Funktionen** beseitigt: Argumente werden nicht mehr als
  Shell-String zusammengesetzt, sondern als Liste an `subprocess.run()` übergeben
- **Passwort-Leak in `opnsense_reset.py`** behoben: Passwörter werden nicht mehr
  in Logausgaben geschrieben
- **Shell-Injection in `catFiles()`** behoben
- Alle verbleibenden `os.popen()`-, `os.system()`- und `subProc()`-Aufrufe wurden
  durch sicheres `subprocess.run()` ersetzt

### OPNsense-Anbindung auf REST-API migriert

`import_subnets.py` verwaltet statische Routen in der OPNsense-Firewall jetzt
ausschließlich über die REST-API (HTTP/HTTPS) statt über SSH-Kommandos. Dadurch
entfällt die Abhängigkeit von SSH-Zugangsdaten für diese Operation und die
Anbindung ist robuster und wartbarer.

### Verbesserter Ablauf bei `linuxmuster-import-devices`

Vor dem eigentlichen `sophomorix-device --sync` wird jetzt zwingend
`sophomorix-device --dry-run` ausgeführt. Nur wenn der Dry-run fehlerfrei
durchläuft, wird mit dem Sync fortgefahren. Schlägt der Dry-run fehl, bricht das
Skript mit einer Fehlermeldung ab.

### Setup-Verbesserungen

- Hostname-Änderungen werden bei der Samba-Provisionierung jetzt korrekt
  übernommen (bisher wurde ein geänderter Hostname ignoriert)
- `isc-dhcp-server6.service` wird während des Setups deaktiviert, um Konflikte
  zu vermeiden
- Keytab-Erstellung wird übersprungen, wenn das Firewall-Setup deaktiviert ist
  (`skipfw = True`)
- NTP wird nur dann deaktiviert, wenn es tatsächlich aktiv ist
- Versionsnummer in der Setup-Dialoganzeige korrigiert

### Verbesserungen an einzelnen Werkzeugen

- **`import_subnets.py`**: Gateway-Berechnung bei Subnetz-Import korrigiert
- **`holiday_generate.py`**: Datumsparsung robuster – beide möglichen
  API-Antwortformate werden jetzt korrekt verarbeitet
- **`import_devices.py`**: Umfangreiches Logging in `import-devices.log`
- **`renew_certs.py`**: Gemeinsame Zertifikatsoperationen aus `g_ssl.py`
  herausgezogen und in `functions.py` konsolidiert
- **`opnsense_reset.py`**: Rückgabewert-Logik bei Keytab-Operationen korrigiert

---

## Abhängigkeiten

### Neu hinzugekommen

| Paket | Grund |
|---|---|
| `python3-paramiko` | SSH-Verbindungen zur Firewall |
| `python3-urllib3` | HTTPS-Verbindungen zur OPNsense-REST-API |
| `python3-setproctitle` | Prozessname in der Prozessliste |

### Entfernt

| Paket | Grund |
|---|---|
| `ntp` | Veraltet; `ntpsec` wird ausschließlich verwendet |
| `python3-pip` | Nicht mehr benötigt bei korrekter Paketierung |

---

## Ubuntu 26.04 (Noble) Unterstützung

- Postinstallations-Skript (`debian/postinst`) erkennt Ubuntu 26.04 korrekt
- Build-System-Kompatibilität für Ubuntu 26.04 hergestellt
- Upgrade-Dokumentation unter `docs/upgrade-26.04.md`

---

## Neue Dokumentation

Der neue Ordner `docs/` ist Bestandteil des Debian-Pakets und enthält:

- `docs/import_subnets.md` – Dokumentation zur Subnetz-Verwaltung
- `docs/upgrade-26.04.md` – Upgrade-Anleitung für Ubuntu 26.04
- `docs/refactoring-phase-1.md` / `refactoring-phase-2.md` – interne
  Entwicklungsdokumentation zum Refactoring

---

## Testinfrastruktur

Eine vollständige Testinfrastruktur wurde neu aufgebaut:

- `tests/test_setup_cli.sh` – Tests für die Setup-CLI
- `tests/test_setup_integration.sh` – Integrationstests mit Snapshot/Restore
  (KVM-basiert)
- Unterstützung für Einzel- und Gesamtläufe, optionale Firewall-Tests (`-s`)
- Automatische Benutzeranlegung nach jedem Setup-Test
- `tests/README.md` – Ausführliche Dokumentation der Testumgebung

---

## CI/CD

- GitHub Actions Workflow auf `ubuntu-24.04` aktualisiert, veraltete Actions
  entfernt
- Eigene Build-Umgebung `lmndev-runner` für den Paketbau
- `debhelper-compat` Level auf 13 angehoben

---

## Upgrade-Hinweise

Da sich die interne Paketstruktur grundlegend geändert hat, ist ein direktes
Upgrade vom Branch 7.3 nur mit gleichzeitigem Upgrade auf Ubuntu 26.04 sinnvoll.
Bitte die Anleitung `docs/upgrade-26.04.md` beachten.

Konfigurationsdateien unter `/etc/linuxmuster/` und `/var/lib/linuxmuster/` werden
durch das Upgrade nicht verändert.
