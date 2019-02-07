FROM postgres:9.4

# add backup scripts
ADD autopsqlbackup.sh /etc/cron.daily/autopsqlbackup
ADD backup.sh /usr/local/bin/backup
ADD restore.sh /usr/local/bin/restore
ADD list-backups.sh /usr/local/bin/list-backups
COPY conf.sql /docker-entrypoint-initdb.d/

# make them executable
RUN chmod +x /etc/cron.daily/autopsqlbackup
RUN chmod +x /usr/local/bin/restore
RUN chmod +x /usr/local/bin/list-backups
RUN chmod +x /usr/local/bin/backup
RUN chmod a+r /docker-entrypoint-initdb.d/conf.sql
