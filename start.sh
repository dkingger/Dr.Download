pkill -f server.py
cd /opt/yt-downloader
source venv/bin/activate
nohup python3 server.py > server.log 2>&1 &
