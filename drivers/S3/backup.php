<?php
	require dirname(__FILE__).'/s3.php';

	$S3_KEY = $argv[1];
	$S3_SEC_KEY = $argv[2];
	$bucket = $argv[3];
	$file = $argv[4]; //file name including path

	$s3 = new S3($S3_KEY, $S3_SEC_KEY);
	$key = basename($file);
	$contentType ="plain/text";

	//Note: the number of metadata items associated with an object is not limited to 7 by S3
	$s3->putObjectFile(
		$file,
		$bucket,
		$key,
		S3::ACL_PRIVATE,
		$metaHeaders = array(),
		$requestHeaders['Content-Disposition'] = "attachment",
		"sbnet-".date("d-m-y", time()).".sql"
	);
