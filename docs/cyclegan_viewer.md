# Visuelle CycleGAN-QC

Aus dem Repository-Verzeichnis (Python 3.8+, keine zusätzlichen Pakete):

```bash
python build_cyclegan_viewer.py \
  --results-dir /home/vogg/pytorch-CycleGAN-and-pix2pix/results/cyclegan_fixed_nl2/test_latest/images \
  --output-dir /home/vogg/pytorch-CycleGAN-and-pix2pix/results/cyclegan_fixed_nl2/test_latest/viewer

hallo

python build_cyclegan_viewer.py   --results-dir /home/vogg/pytorch-CycleGAN-and-pix2pix/checkpoints/cyclegan_fixed_nl2/web/images   --output-dir /home/vogg/pytorch-CycleGAN-and-pix2pix/checkpoints/cyclegan_fixed_nl2/web/viewer

```

`--title "Mein Experiment"` setzt den Titel. `--recursive` durchsucht Unterordner;
gleichnamige Fälle in verschiedenen Unterordnern bleiben getrennt. Eingabe und
Ausgabe müssen getrennte, nicht ineinander verschachtelte Ordner sein.
PNG, JPEG, WebP, BMP und GIF werden unterstützt. Andere Dateien werden ignoriert.
Mehrere Dateien für denselben Fall und Bildtyp führen zu einer verständlichen
Fehlermeldung, statt willkürlich ein Bild auszuwählen.

Die Ausgabe enthält `index.html`, `viewer_manifest.csv`, `missing_files.csv` und
bytegetreue Bildkopien unter `images/`. Das benötigt zusätzlichen Speicherplatz;
Quelldateien bleiben unverändert. Das Manifest enthält absolute Quellpfade,
der Viewer verwendet relative Pfade zu seinen Kopien. Der komplette Ausgabeordner
kann daher verschoben werden. Bei erneutem Generieren werden HTML, Reports und
zugehörige Bildkopien aktualisiert; nicht mehr verwendete Kopien werden nicht gelöscht.

`index.html` direkt im Browser öffnen oder alternativ:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory /home/vogg/pytorch-CycleGAN-and-pix2pix/checkpoints/cyclegan_fixed_nl2/web/viewer


python -m http.server 8000 --bind 127.0.0.1 --directory /home/vogg/pytorch-CycleGAN-and-pix2pix/results/cyclegan_fixed_nl2/test_latest/viewer
```

Dann `http://localhost:8000` öffnen. Der Viewer benötigt weder Internet noch einen
Backend-Dienst. Auf Desktop stehen die Bilder in dieser Reihenfolge:

```text
real_A | fake_B | rec_A | idt_B
real_B | fake_A | rec_B | idt_A
```

Previous/Next, Pfeiltasten, First/Last oder die Fallnummer navigieren innerhalb
der gefilterten Fälle. Bilder öffnen sich per Klick in einer Lightbox;
„Original (1:1)“ zeigt die natürliche Auflösung in CSS-Pixeln mit Scrollbalken.
Escape oder ein Klick auf den Hintergrund schließt die Lightbox. Es gibt keine
Normalisierung, Kontraständerung oder neu gespeicherte Skalierung. Die normale
Ansicht wird ausschließlich durch den Browser passend skaliert.

Overall und sieben Teilaspekte können unabhängig mit PASS, SUSPICIOUS oder FAIL
bewertet werden. Erneutes Anklicken entfernt die Bewertung. Die Filter verwenden
Overall, ohne eine Gesamtbewertung aus Teilbewertungen abzuleiten. Missing-Panels
und der Missing-Report dokumentieren alle fehlenden Bildtypen.

Bewertungen liegen in localStorage, getrennt nach absolutem Quellordner.
Sie bleiben bei Neugenerierung für denselben Quellpfad erhalten. localStorage ist
browser- und adressabhängig, bei `file://` browserabhängig und im privaten Modus
möglicherweise nur temporär. Speicherfehler werden sichtbar gemeldet. Regelmäßig
„Export QC ratings (JSON)“ verwenden: exportiert werden alle Fälle, auch gerade
ausgefilterte und unbewertete, samt Metadaten und Missing-Typen. Ein Reimport ist
nicht implementiert.

Vollständig erkannte Namen wie `subject018_OS_bscan_0043` werden nach numerischem
Subject, Eye und numerischem B-Scan sortiert. Bei anderen oder gemischten Namen
gilt eine deterministische natürliche Sortierung. Metadaten sind optional.

CycleGAN ist unpaired: real_B ist keine pixelweise Ground Truth für fake_B,
real_A keine für fake_A. Diese Galerie dient ausschließlich visueller QC von
Anatomie, Domain-Erscheinung, Identity und Cycle-Konsistenz; sie berechnet keine
quantitativen Metriken. Fehlende Identity-Ausgaben werden als missing angezeigt;
Trainings- und Testcode werden nicht verändert.
