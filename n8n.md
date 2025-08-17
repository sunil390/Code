# n8n for POC

## Setup

1. docker volume create n8n_data
2. docker run -it --rm --name n8n -p 5678:5678 -e N8N_SECURE_COOKIE="false" -e TZ="Asia/Kolkata" \
   -v n8n_data:/home/node/.n8n --add-host=awx.znext.com:192.168.2.226 docker.n8n.io/n8nio/n8n
3. in Mac ensure that local network access is enabled in systems settings for docker desktop
4. docker exec -it --user root n8n /bin/sh
