#!/bin/sh

DATE=$(date +%y-%m-%d) #yy-mm-dd
DIR=`dirname "$0"`/ #current directory
MAX_THREADS=2

#MySQL vars
DB_USER=<your db user>
DB_HOST=<your db host>
DB_PASS=<your db password>

#Backup directory vars - Only used in S3 for now
BACKUP_DIR=${DIR}backups/

#S3 vars
S3=0 #Set to 1 to back db up to S3
S3_KEY=<your s3 key>
S3_SEC_KEY=<your sec key>
S3_BUCKET=<your bucket name>

#Google Docs vars
GD=1 #Set to 1 to back up to Google Docs
GD_EMAIL=<your google docs email address>
GD_PASSWORD=<your google docs password>


#Get list of dbs
LIST=`mysql -u${DB_USER} -p${DB_PASS} -h${DB_HOST} INFORMATION_SCHEMA -e "SELECT SCHEMA_NAME FROM SCHEMATA WHERE SCHEMA_NAME !='information_schema';"`

#Loop through list ignoring result table name
i=0;
for each in $LIST; do
	i=$((i+1))
    if [ "$each" != "SCHEMA_NAME" ]; then
        mysqldump -u${DB_USER} -p${DB_PASS} -h${DB_HOST} --opt --single-transaction $each > ${BACKUP_DIR}${DATE}_${each}.sql &
    fi

    #Only allow up to MAX_THREADS simultaneous threads
    if [ $i = $MAX_THREADS ]; then
    	wait
    	i=0
    fi
done

#Wait for any remaining child processes to complete
wait

#Zip and remove SQL dumps
zip -qj ${BACKUP_DIR}dbBackup_${DATE} ${BACKUP_DIR}${DATE}_*.sql
rm ${BACKUP_DIR}${DATE}_*.sql

#Back up to Google Docs
if [ ${GD} != 0 ]; then
    python "${DIR}drivers/GoogleDocs/flynsarmy_gdocs_backup.py" --email=${GD_EMAIL} --password=${GD_PASSWORD} --filepath=${BACKUP_DIR}dbBackup_${DATE}.zip
fi

#Back up to S3
if [ ${S3} != 0 ]; then
    php5 -f "${DIR}drivers/S3/backup.php" "${S3_KEY}" "${S3_SEC_KEY}" "${S3_BUCKET}" "${BACKUP_DIR}dbBackup_${DATE}.zip"
fi
