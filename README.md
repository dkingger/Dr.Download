<div style="display: flex; align-items: center; ">
  <img src="docs/logo.png" alt="DRDownloader" width="300"/>
</div>

# 🎬 DR Downloader  

En selvhostet downloader til DR TV, der henter både **video + lyd**, fletter dem til én MP4-fil og giver dig et simpelt webinterface til at styre alle downloads.

Systemet kører på **Flask + yt-dlp**, har **persistent job-database**, **historik**, **log-visning** og **automatisk oprydning** af temp-mapper.

---

## 🖥️ Systemoversigt (Arkitektur)

![Arkitektur for DR Downloader](docs/architecture-dr-downloader.svg)

---

## 🚀 Funktioner

- 🔗 Indsæt et DR-link og start download med ét klik  
- 🎧 Henter video + lyd separat og **remuxer uden genkodning** til én `.mp4`  
- 📊 Live status (I kø → Downloader video → Downloader lyd → Behandler → Klar)  
- 🗃️ Job-liste med download-knap (kun aktiv når filer er klar)  
- 📜 Log-visning direkte i browseren  
- 🕓 Historik med titel + URL + tidspunkt  
- 🧹 Automatisk oprydning af `/tmp/job_*` mapper  
- 🔄 Server kan genstarte uden at miste state (jobs gemmes i JSON)

---

## 🧩 Filstruktur

```text
Dr.Download/
├─ server.py
├─ jobs.json
├─ history.json
├─ requirements.txt
├─ install.sh
├─ start.sh
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
   └─ (CSS / grafik)
