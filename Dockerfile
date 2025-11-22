FROM python:3.12-slim

# Sæt timezone til Europe/Copenhagen inde i containeren
ENV TZ=Europe/Copenhagen
ENV DEBIAN_FRONTEND=noninteractive

# Installer ffmpeg + tzdata og sæt /etc/localtime korrekt
RUN apt-get update && \
    apt-get install -y ffmpeg tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# Installer Python-pakker
RUN pip install --no-cache-dir yt-dlp flask

WORKDIR /app

# Lav log-mappe
RUN mkdir -p /app/logs

# Kopiér app-filer
COPY server.py /app/
COPY templates /app/templates

EXPOSE 5000

CMD ["python", "server.py"]
