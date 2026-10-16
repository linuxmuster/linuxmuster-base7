# linuxmuster.net 7.4 – Entwicklungsstatistik

Erhebungsstand: 15.10.2026. Erfasst sind elf Repositories der Organisation
`linuxmuster` auf GitHub.

## Zahlen

| Repository | Commits | Issues | PRs | + Zeilen |
|---|---:|---:|---:|---:|
| linuxmuster-base7 | 327 | 37 | 7 | 21.952 |
| linuxmuster-tools | 277 | 17 | 12 | 26.955 |
| linuxmuster-linbo7 | 235 | 26 | 9 | 23.867 |
| linuxmuster-api | 169 | 19 | 8 | 10.919 |
| linuxmuster-webui7 | 141 | 16 | 1 | 4.114 |
| linuxmuster-cli7 | 61 | 1 | 0 | 5.655 |
| linuxmuster-common | 32 | 0 | 0 | 261 |
| linuxmuster-prepare | 22 | 1 | 0 | 819 |
| sophomorix4 | 20 | 2 | 1 | 331 |
| linuxmuster-linbo-gui | 4 | 2 | 3 | 77 |
| linuxmuster-fileserver | 3 | 0 | 0 | 77 |
| **Summe** | **1.291** | **121** | **41** | **95.027** |

Dazu 57.781 gelöschte Zeilen (netto +37.246) in 1.204 geänderten Dateien.
Die Zeilen- und Dateizahlen sind um generierte Dokumentation und mitgelieferte
Fremddateien bereinigt, siehe Einschränkungen.

## Methodik

Verglichen wird pro Repository die 7.4-Entwicklungslinie gegen die 7.3-Linie
ab deren gemeinsamem Abzweigpunkt (merge base). Ein Vergleich „ab Tag v7.4.0"
ist nicht möglich, weil

- die 7.3-Reihe parallel weitergepflegt wird (z. B. `linuxmuster-base7 v7.3.42`
  vom 09.09.2026, also nach dem Start der 7.4-Serie), und
- fünf der elf Repositories gar kein `v7.4.0`-Tag haben, sondern erst bei
  7.4.1 beginnen.

Verwendete Branch- bzw. Tag-Paare:

| Repository | Basis | 7.4-Linie | Abzweig |
|---|---|---|---|
| linuxmuster-api | `lmn73` | `lmn74` | 25.04.2026 |
| linuxmuster-base7 | `7.3` | `7.4` | 10.11.2025 |
| linuxmuster-cli7 | `v7.3.20` | `main` | 22.02.2026 |
| linuxmuster-common | `7.3` | `7.4` | 09.04.2025 |
| linuxmuster-fileserver | `lmn73` | `lmn74` | 07.04.2026 |
| linuxmuster-linbo-gui | `v7.3.3` | `master` | 04.10.2025 |
| linuxmuster-linbo7 | `4.3` | `7.4` | 28.04.2026 |
| linuxmuster-prepare | `7.3` | `7.4` | 29.07.2025 |
| linuxmuster-tools | `lmn73` | `lmn74` | 26.04.2026 |
| linuxmuster-webui7 | `lmn73` | `lmn74` | 01.04.2026 |
| sophomorix4 | `v7.3.16` | `bionic` | 11.07.2026 |

`linuxmuster-cli7`, `linuxmuster-linbo-gui` und `sophomorix4` führen keine
getrennten Versionsbranches; dort dient das letzte Tag der 7.3-Reihe als Basis.

Issues sind geschlossene Issues ohne Pull Requests, gezählt ab dem jeweiligen
Abzweigdatum; Pull Requests werden separat als gemergte PRs ausgewiesen.
Hinzugefügte Zeilen sind die Summe aller Zeilenzugänge über alle Nicht-Merge-Commits
des jeweiligen Bereichs.

## Einschränkungen

- `linuxmuster-base7`, `-common`, `-prepare` und `-linbo-gui` haben ihre
  7.4-Branches bereits 2025 abgezweigt. Deren Issue-Zahlen können vereinzelt
  Vorgänge enthalten, die inhaltlich noch zu 7.3 gehören. Commit- und
  Zeilenzahlen sind davon nicht betroffen, sie gehören zur 7.4-Linie.
- Die Zeilen- und Dateizahlen sind bereinigt. Nicht gezählt werden
  - die generierte Sphinx-Dokumentation unter `docs/` in `linuxmuster-tools`
    (43.186 Zeilen) und `linuxmuster-webui7` (64.829 Zeilen; HTML, Suchindex,
    JavaScript und CSS aus dem Sphinx-Build, die Quellen liegen in `docs_src/`),
  - das mitgelieferte Test-Framework `shunit2` in `linuxmuster-linbo7`
    (1.613 Zeilen).

  Unbereinigt wären es 204.655 hinzugefügte und 107.662 gelöschte Zeilen in
  2.163 geänderten Dateien. Weitere eingebettete Fremdbibliotheken oder
  generierte Artefakte enthält der Diff nicht.
- Die Zahlen umfassen die zum Erhebungsstand veröffentlichten Stände der
  jeweiligen 7.4-Branches.

## Reproduktion

Repositories und Standardbranches auflisten:

```sh
gh repo list linuxmuster --limit 100 --json name,isArchived \
  --jq '.[] | select(.isArchived==false) | .name'
gh api repos/linuxmuster/<repo> --jq .default_branch
```

Vorhandene 7.4-Tags je Repository:

```sh
gh api --paginate "repos/linuxmuster/<repo>/tags?per_page=100" --jq '.[].name' \
  | grep -E '^v?7\.4\.' | sed 's/^v//' | sort -V
```

Commits und Abzweigdatum (merge base) je Repository:

```sh
gh api "repos/linuxmuster/<repo>/compare/<basis>...<7.4-linie>" \
  --jq '{commits: .total_commits, abzweig: .merge_base_commit.commit.committer.date}'
```

Geschlossene Issues und gemergte Pull Requests ab dem Abzweigdatum:

```sh
gh api -X GET search/issues \
  -f q="repo:linuxmuster/<repo> is:issue is:closed closed:>=<datum>" --jq '.total_count'
gh api -X GET search/issues \
  -f q="repo:linuxmuster/<repo> is:pr is:merged merged:>=<datum>" --jq '.total_count'
```

Hinzugefügte und gelöschte Zeilen (lokaler Klon, `git clone --bare` genügt).
`<ausschluss>` ist ein Regex für nicht zu zählende Pfade, z. B. `^docs/` für
`linuxmuster-tools` und `linuxmuster-webui7` (generierte Sphinx-Doku) oder
`^tests/shell/shunit2$` für `linuxmuster-linbo7`, sonst `^$`:

```sh
git log --no-merges --numstat --pretty=tformat: <basis>..<7.4-linie> \
  | awk -v ex='<ausschluss>' '$1 ~ /^[0-9]+$/ && $3 !~ ex {plus+=$1; minus+=$2} END {print plus, minus}'
git diff --name-only <basis>..<7.4-linie> | grep -Ev '<ausschluss>' | wc -l
```

Größte Einzelbeiträge zur Zeilenzahl prüfen (Erkennung von Fremd- und
Generatdateien):

```sh
git log --no-merges --numstat --pretty=tformat: <basis>..<7.4-linie> \
  | awk '$1 ~ /^[0-9]+$/ {a[$3]+=$1} END {for (f in a) print a[f], f}' \
  | sort -rn | head -10
```

Signed-off by: thomas@linuxmuster.net
Assisted by  : Claude
