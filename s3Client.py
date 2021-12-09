def download(s3, bucket, file_name, save_as):
	s3.download_file(bucket, file_name, save_as)