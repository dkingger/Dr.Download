📺 DR Downloader

En lille selv-hostet downloader til DR TV, som henter både video og lyd, fletter dem til én MP4-fil og giver dig en pæn web-grænseflade til at følge dine downloads.

Systemet kører som en Flask-server med baggrundstråde, job-liste, log-visning og automatisk oprydning af gamle job-mapper.

🚀 Funktioner

Indsæt et DR-link og start download med ét klik

Henter video + lyd separat og remuxer dem til én fil (ingen genkodning)

Visning af job-status i realtid

Automatisk oprydning af temp-filer i /tmp

Historik over tidligere downloads

Log-side + kommando-reference

Job-side hvor kun færdige downloads får aktiv download-knap

Server kan genstarte uden at miste job-status (jobs gemmes i JSON)

🖥️ Teknisk oversigt

Backend:

Python 3

Flask

yt-dlp

Baggrundstråde (threading.Thread)

Persistent job-database (JSON)

Persistent historie (JSON)

Automatisk cleanup af /tmp/job_*

Frontend:

Ren HTML/CSS/JS

Live status via /jobs-json

Animationer (shake/bob effekt)

Responsive layout

Enkelt, mørkt UI

🧩 Filstruktur
Dr.Download/
├─ server.py
├─ jobs.json
├─ history.json
├─ logs/
│  └─ app.log
├─ templates/
│  ├─ index.html
│  ├─ jobs.html
│  ├─ log.html
│  ├─ maintenance.html
│  └─ commands.html
└─ static/
   ├─ DRDownload.png
   └─ style.css (hvis tilføjet senere)

📦 Installation
1. Klon repoet
git clone https://github.com/dkingger/Dr.Download.git
cd Dr.Download

2. Opret Python-miljø
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt


(Sig til, hvis du vil have en requirements.txt genereret.)

3. Start serveren

Du kan starte manuelt:

nohup python3 server.py &


Eller bruge den medfølgende start.sh (anbefalet):

./start.sh

🌐 Brug

Gå til:
http://server-ip:5000

Indsæt et DR-link

Tryk Start download

Følg progression på /jobs

Download MP4-filen når knappen bliver grøn

Systemet rydder automatisk op

🧹 Automatisk oprydning

Alle midlertidige job-mapper i:

/tmp/job_*


bliver slettet automatisk efter 24 timer, eller når en fil er hentet.

🐞 Log og fejlsøgning

Logfil findes her:

logs/app.log


Du kan også se den i browseren:
/log

📚 Kommando-reference

Se siden /commands for en fuld liste over nyttige shell-kommandoer, fx:

df -h – Diskforbrug

du -h /tmp – Størrelser på job-mapper

watch -n 1 df -h – Live overvågning

systemctl restart yt-downloader – Genstart serveren

tail -f server.log – Live log

og flere…
