# linuxmuster.net 7.4 Workshop (Slidev)

Fertige Fassung als PDF: [linuxmuster-74-workshop.pdf](linuxmuster-74-workshop.pdf)

    npm install
    npm run dev        # Präsentation, Presenter-Ansicht mit /presenter
    npm run build      # statische Version nach dist/
    npm run export     # PDF (benötigt playwright-chromium)

Folien mit "DEMO" im Titel werden live gezeigt. Vor dem Workshop auf dem Testserver
mit Snapshot ausprobieren, vor allem `lmncli passwd`, `linuxmuster-renew-certs -c`
und `linbo-remote -i <host> -c reboot --dry-run`.
