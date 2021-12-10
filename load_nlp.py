from pymagnitude import *
import boto3

s3 = boto3.client('s3', region_name='us-west-1')

def download_glove():
	print('downloading nlp...') #debug
	# global nlp
	# while True:
	# 	if nlp is not None: break
	# 	# socketio.sleep(1)

	s3.download_file('themed-party-playlist', 'glove_nlp', 'glove.6B.300d.magnitude')

	print('download...')

	nlp = Magnitude('glove.6B.300d.magnitude')

	print('done loading nlp.') #debug

	return nlp