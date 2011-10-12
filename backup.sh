#!/bin/sh

DATE=$(date +%y-%m-%d) #yy-mm-dd
DIR=`dirname "$0"`/ #current directory

################################
#    CUSTOMISABLE SETTINGS     #
################################

MAX_THREADS=12

#MySQL vars
DB_USER=your_username
DB_HOST=your_host
DB_PASS=your_password

#Working directory - will be created if it doesn't already exist
#Everything in this directory will be deleted on completion
TMP_DIR=${DIR}tmp/
ZIP_NAME=dbBackup_${DATE}.zip
ZIP_PATH=${TMP_DIR}${ZIP_NAME} #Where to store temporary zip file
ZIP_TARGETS=${TMP_DIR}${DATE}_*.sql #What files are being zipped?

#Back up to somewhere on your machine
LOCAL_BACKUP=0
LOCAL_BACKUP_PATH=/home/flynsarmy/ #With trailing slash /path/to/dir/

#FTP vars
FTP=0
FTP_HOST=your_host
FTP_PORT=21
FTP_USER=your_username
FTP_PASSWORD=your_password
FTP_PATH=/path/to/ #With trailing slash /path/to/dir/

#Amazon S3 vars
S3=0 #Set to 1 to back db up to S3
S3_KEY=your_key
S3_SEC_KEY=your_secret_key
S3_BUCKET=your_bucket

#Google Docs vars
GD=0 #Set to 1 to back up to Google Docs
#WARNING: Setting this to 1 is not currently advisable due to a bug in Google Docs.
#See http://www.google.com/support/forum/p/Google+Docs/thread?tid=0240a085c9f85dd5&hl=en
GD_CHUNKIFY=0 #Split SQL dumps into 'chunks' small enough to be convertable.
GD_EMAIL=your_email
GD_PASSWORD=your_password

#Google Storage vars
GS=0
GS_BUCKET=gs://your_bucket





################################
#DANGER AHEAD. TINKERERS BEWARE#
################################

#Create working directory
mkdir -p ${TMP_DIR}

#Get list of dbs
LIST=`mysql -u${DB_USER} -p${DB_PASS} -h${DB_HOST} INFORMATION_SCHEMA -e "SELECT SCHEMA_NAME FROM SCHEMATA WHERE SCHEMA_NAME !='information_schema';"`

#Loop through list ignoring result table name
i=0;
for each in $LIST; do
	i=$((i+1))
    if [ "$each" != "SCHEMA_NAME" ]; then
		#If uploading to google docs, use separate insert lines.
		#This results in larger DB dump file so only do it if necessary
		if [ ${GD} != 0 ]; then
			mysqldump -u${DB_USER} -h${DB_HOST} -p${DB_PASS} --skip-extended-insert $each > "${TMP_DIR}${DATE}_${each}.sql" &
		else
			mysqldump -u${DB_USER} -h${DB_HOST} -p${DB_PASS} --opt --single-transaction $each > "${TMP_DIR}${DATE}_${each}.sql" &
		fi
    fi

    #Only allow up to MAX_THREADS simultaneous threads
    if [ $i = $MAX_THREADS ]; then
    	wait
    	i=0
    fi
done

#Wait for any remaining child processes to complete
wait

#Backup to local HDD
if [ ${LOCAL_BACKUP} != 0 ]; then
	#Override default zip_path so that
	# a) we do the local backup as specified and
	# b) it doesn't get deleted when we clear tmp dir
	# c) we don't need to do a potentially costly copy operation
	ZIP_PATH=${LOCAL_BACKUP_PATH}${ZIP_NAME}

	#Zip and remove SQL dumps
	zip -qj ${ZIP_PATH} ${ZIP_TARGETS}
fi

if [ ${FTP} != 0 ]; then
	#Zip and remove SQL dumps
	if [ ! -e ${ZIP_PATH} ]; then
		zip -qj ${ZIP_PATH} ${ZIP_TARGETS}
	fi

	ftp -n ${FTP_HOST} ${FTP_PORT} <<END_SCRIPT
		quote USER ${FTP_USER}
		quote PASS ${FTP_PASSWORD}
		put "${ZIP_PATH}" "${FTP_PATH}${ZIP_NAME}"
		quit
END_SCRIPT
fi

#Back up to Google Storage
if [ ${GS} != 0 ]; then
	#First time using Google Storage, run the config tool
	if [ ! -e ~/.boto ]; then
		${DIR}packages/gsutil/gsutil config
	fi

	#Zip and remove SQL dumps
	if [ ! -e ${ZIP_PATH} ]; then
		zip -qj ${ZIP_PATH} ${ZIP_TARGETS}
	fi

    ${DIR}packages/gsutil/gsutil cp "${ZIP_PATH}" ${GS_BUCKET}
fi

#Back up to Google Docs
if [ ${GD} != 0 ]; then
	#Split SQL dumps into smaller chunks and upload-convert
	if [ ${GD_CHUNKIFY} != 0 ]; then
		MAX_THREADS=3 #Max simultaneous uploads

		for each in $LIST; do
			i=0;
			#Chunk SQL dump to convertable sizes
			UPLOAD_LIST=`"${DIR}packages/flynsarmy_dbchunk/flynsarmy_dbchunk.py" --max_chunk_size=512000 --filepath="${TMP_DIR}${DATE}_${each}.sql"`

			for each_upload in $UPLOAD_LIST; do
				i=$((i+1))

				#Upload chunk
				python "${DIR}drivers/GoogleDocs/flynsarmy_gdocs_backup.py" --email=${GD_EMAIL} --password=${GD_PASSWORD} --convert --filepath=${each_upload}

				#Only allow up to MAX_THREADS simultaneous threads
				if [ $i = $MAX_THREADS ]; then
					wait
					i=0
				fi
			done

			#Wait for any remaining child processes to complete
			wait
		done

	#Don't split SQL files, just zip and upload
	else
		#Zip and remove SQL dumps
		if [ ! -e ${ZIP_PATH} ]; then
			zip -qj ${ZIP_PATH} ${ZIP_TARGETS}
		fi

		python "${DIR}drivers/GoogleDocs/flynsarmy_gdocs_backup.py" --email=${GD_EMAIL} --password=${GD_PASSWORD} --filepath=${ZIP_PATH}
	fi
fi

#Back up to Amazon S3
if [ ${S3} != 0 ]; then
	#Zip and remove SQL dumps
	if [ ! -e ${ZIP_PATH} ]; then
		zip -qj ${ZIP_PATH} ${ZIP_TARGETS}
	fi

    php5 -f "${DIR}drivers/S3/backup.php" "${S3_KEY}" "${S3_SEC_KEY}" "${S3_BUCKET}" "${ZIP_PATH}"
fi

#Remove all temporary files
rm ${TMP_DIR}*
