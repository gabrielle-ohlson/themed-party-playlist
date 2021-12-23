# backend for web app
async_mode = 'gevent'

from gevent import monkey
monkey.patch_all()

from flask import Flask, session, request, redirect, render_template, url_for, current_app #, copy_current_request_context
from flask_session import Session

from flask_socketio import SocketIO
from threading import Thread, Event

import uuid
import os
import re
import requests
import time
import sys
from io import StringIO
import json

import lyricsgenius
import spotipy

from github import Github #TODO: install
from pymagnitude import *
import boto3
# from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
# from azure.storage.blob.aio import BlobClient

from google.cloud import storage


import themes
# import topic
from sim import get_similar_words

# import base64
import csv

maxInt = sys.maxsize

while True:
	# decrease the maxInt value by factor 10 
	# as long as the OverflowError occurs.
	try:
		csv.field_size_limit(maxInt)
		break
	except OverflowError:
		maxInt = int(maxInt/10)


# import gensim.downloader as gensim_api
nlp = None

# We must now create our app, which I will store in a variable called `app`:
app = Flask(__name__, static_url_path='/static')

app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session'

from os import environ, path
from dotenv import load_dotenv

basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, '.env'))

with app.app_context():
	root_dir = current_app.root_path
	print('root_dir:', root_dir)

# TESTING = True
# DEBUG = True
app.config['FLASK_ENV'] = 'development'
app.config['SECRET_KEY'] = environ.get('SECRET_KEY')

app.config['GENIUS_TOKEN']=environ.get('GENIUS_TOKEN')

app.config['SPOTIPY_CLIENT_ID']=environ.get('SPOTIPY_CLIENT_ID')

app.config['SPOTIPY_CLIENT_SECRET']=environ.get('SPOTIPY_CLIENT_SECRET')

app.config['GITHUB_TOKEN']=environ.get('GITHUB_TOKEN')

app.config['SPOTIPY_REDIRECT_URI']= 'http://127.0.0.1:5000/'


# ------

GOOGLE_SERVICE_ACCOUNT_INFO = environ.get('GOOGLE_SERVICE_ACCOUNT_INFO')

app.config['GOOGLE_SERVICE_ACCOUNT_INFO'] = GOOGLE_SERVICE_ACCOUNT_INFO

json_acct_info = json.loads(GOOGLE_SERVICE_ACCOUNT_INFO)

client = storage.Client.from_service_account_info(
	json_acct_info
)

input_blob = None

google_input_bucket = client.get_bucket('topic-model-input')

google_output_bucket = client.get_bucket('topic-model-output')

# ------

app.config['FLASKS3_BUCKET_NAME'] = 'themed-party-playlist'
app.config['AWS_ACCESS_KEY_ID'] = environ.get('AWS_ACCESS_KEY_ID')
app.config['AWS_SECRET_ACCESS_KEY'] = environ.get('AWS_SECRET_ACCESS_KEY')

# _AZFUNC_API_URL = environ.get('_AZFUNC_API_URL')
# app.config['_AZFUNC_API_URL'] = _AZFUNC_API_URL

AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
app.config['AZURE_STORAGE_CONNECTION_STRING'] = AZURE_STORAGE_CONNECTION_STRING

# Create the BlobServiceClient object which will be used to create a container client
# blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING) #TODO: remove #?


# Create a unique name for the container
# container_name = str(uuid.uuid4())
# container_name = 'topic-data'

# Create the container
# container_client = blob_service_client.create_container(container_name)

# blob_block = ContainerClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name=container_name)


AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID')

AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')

s3 = boto3.client('s3', region_name='us-west-1')

S3_BUCKET = os.environ.get('S3_BUCKET')

if (os.environ.get('PORT')):
	port = os.environ.get('PORT')
else:
	port = 5000

genius_token = os.getenv('GENIUS_TOKEN')

genius = lyricsgenius.Genius(genius_token, timeout=15, retries=3, remove_section_headers=True)  # access token

github_token = os.getenv('GITHUB_TOKEN')

github = Github(github_token)

repo = github.get_user().get_repo('lyrics-storage')

query_url = f"https://raw.githubusercontent.com/gabrielle-ohlson/lyrics-storage/main/"

def get_file(filename):
	try:
		r = requests.get(query_url+filename)
		r.raise_for_status()

		file_content = r.text
	except:
		return False

	return file_content


# socketio = SocketIO(app, async_mode=None, cors_allowed_origins="*")
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins=[
	'http://localhost:5000', 'https://localhost:5000',
	'https://themed-party-playlist.herokuapp.com', 'https://themed-party-playlist.herokuapp.com/',
	'http://themed-party-playlist.herokuapp.com', 'http://themed-party-playlist.herokuapp.com/',
	'https://themed-party-playlist.herokuapp.com/create-playlist',
	'http://themed-party-playlist.herokuapp.com/create-playlist',
	'http://127.0.0.1:5000', 'http://127.0.0.1:5000/create-playlist', 
	'https://127.0.0.1:5000', 'https://127.0.0.1:5000/create-playlist',
	'http://0.0.0.0:5000', 'http://0.0.0.0:5000/create-playlist', 'http://127.0.0.1:5000/'])

connected_clients = []

#update_bookshelf Generator Thread
bookshelf_thread = None

bookshelf_thread_stop_event = Event()
matches_thread_stop_event = Event()
songs_thread_stop_event = Event()
index_page_event = Event()

matches_thread = None
get_matches_thread = None

Session(app)

caches_folder = './.spotify_caches/'

if not os.path.exists(caches_folder):
	os.makedirs(caches_folder)

def session_cache_path():
	return caches_folder + session.get('uuid')

spotify = None

input_info = {
	'theme': None,
	'method': None,
	'stopCondition': None,
	'stopNum': None,
	'playlistName': None,
	'saveAs': None,
	'trainTime': None
}

userPlaylists = []

# topic_dictionary = {}
terms = []

albums = []
songs = []
relevant_lyrics = []
songs_with_lyrics = []
matches = None

info = { 'duration': 0, 'song count': 0 }

def_display = 'none'

sim_words = []

def reachedLimit():
	'''
	function to check whether the playlist is at the max length (aka met stop condition)
	'''
	if input_info['stopNum'] is None or abs(input_info['stopNum']-info[input_info['stopCondition']]) >= 60000 or info[input_info['stopCondition']] < input_info['stopNum']: return False
	else: return True #break if within 1 minute of stopNum or exceeded stopNum


class RestartException(Exception):
	pass


@socketio.on('connect')
def register_client():
	if request.namespace not in connected_clients: connected_clients.append(request.namespace)
	print(f'connected: {request.sid}. Namespace: {request.namespace}. (total connections: {len(connected_clients)})')


@socketio.on('connect', namespace='/create-playlist')
def register_client():
	if request.namespace not in connected_clients: connected_clients.append(request.namespace)
	print(f'connected: {request.sid}. Namespace: {request.namespace} (total connections: {len(connected_clients)}).')


@socketio.on('disconnect')
def unregister_client():
	print(f'disconnected: {request.sid}. Namespace: {request.namespace} (total connections: {len(connected_clients)}).')
	if request.namespace in connected_clients: connected_clients.remove(request.namespace)


@socketio.on('disconnect', namespace='/create-playlist')
def unregister_client():
	print('disconnected:', request.sid, request.namespace)
	if request.namespace in connected_clients: connected_clients.remove(request.namespace)


def await_connection(ns, cb=None):
	while True:
		if ns in connected_clients: break
		print(f'namespace: {ns} not yet connected...') #debug
		socketio.sleep(1)
	
	if cb is not None: cb()

	print(f'namespace: {ns} is now connected!') #debug


def start_matches_thread():
	global matches_thread
	print('start_matches_thread....') #remove #debug
	matches_thread = MatchesThread()
	matches_thread.start() #current_app._get_current_object() #disconnect #is_connected


# @socketio.on('find_matches', namespace='/create-playlist')
def get_matches():
	while True:
		if index_page_event.is_set():
			print('index page event is set.') #debug
			break #new #*

		global matches_thread
		global matches

		print('client requested "find_matches". finding matches...', matches_thread, matches) #remove #debug

		google_output_blob = google_output_bucket.get_blob('data.json')

		print('1:', google_output_blob)

		socketio.sleep(30)

		print('after 30 sleep:', google_output_blob) #remove #debug

		blob_tries = 1
		while google_output_blob is None:
			if blob_tries > 6: break #?
			google_output_blob = google_output_bucket.get_blob('data.json')
			print(google_output_blob is not None) #remove #debug
			blob_tries += 1
			socketio.sleep(10)

		print('now:', google_output_blob) #remove #debug

		'''
		blob = BlobClient.from_connection_string(conn_str=AZURE_STORAGE_CONNECTION_STRING, container_name="song-data", blob_name="data.json")

		print('sending request to azure backend...') #debug

		socketio.sleep(30)

		blob_tries = 1
		while not blob.exists():
			if index_page_event.is_set():
				print('index page event is set.') #debug
				return #new #*
			if blob_tries > 6: break
			print(f'blob exists: {blob.exists()} (try #{blob_tries}).') #remove #debug
			blob_tries += 1 #remove #debug
			socketio.sleep(20)
			continue

		print('now, blob exists:', blob.exists()) #remove #debug

		if blob.exists():
			blob_content = blob.download_blob().readall()

			print('blob:', blob, 'blob_content:', blob_content) #remove #debug
			blob.delete_blob()

			matches = json.loads(blob_content)
		'''
		if google_output_blob is not None:
			global input_blob #new
			input_blob.delete()

			blob_content = google_output_blob.download_as_string()

			print('blob_content:', blob_content) #remove #debug

			matches = json.loads(blob_content)

			google_output_blob.delete()
		else:
			# import papermill as pm

			# pm.execute_notebook(
			# 	'input.ipynb',
			# 	'output.ipynb',
			# 	parameters= {'songs': songs_with_lyrics, 'terms': terms, 'stopNum': input_info['stopNum'], 'stopCondition': input_info['stopCondition'], 'relevant_lyrics': relevant_lyrics, 'threshold': 0.05}
			# )


			matches = []
			thresh = 0.5

			import synoynm as syn

			topic_dictionary = {}

			for term in terms:
				definitions = syn.word_scorer(term)
				print('definitions:', definitions) #remove #debug
				topic_dictionary[term] = definitions[0][0]

			print('topic_dictionary:', topic_dictionary) #remove #debug

			for song in songs_with_lyrics:
				songLyrics = song['lyrics']

				words = syn.prep_phrase(songLyrics)

				matches_theme = False

				for term in terms:
					if matches_theme: break
					# vector_dists = nlp.distance(term, words)
					# .sort() #sorts from lowest to highest

					# print("vector_dists:", vector_dists) #remove #debug
					word_matches = []
					for word in words:
						sim_score = nlp.similarity(term, word)
						if sim_score >= thresh:
							word_matches.append(word)
							print(f"\nAdding '{song['name']}' by {song['artists'][0]} to playlist because it passes the similarity threshold with a score of {sim_score} and contains the keyword: '{word}'\n")
							matches.append(song)
							matches_theme = True
							break

					similarity_scores = nlp.similarity(term, words)
					similarity_scores.sort(reverse=True)
					print(f'top 3 similarity_scores for "{song["name"]}" with term "{term}":', similarity_scores[:3]) #remove #debug

					if similarity_scores[0] >= thresh: print('\n!', song['name'], similarity_scores[0])

		print('got matches.') #remove #debug

		with app.test_request_context():
			connect_create_playlist = Thread(target=await_connection, kwargs={'ns': '/create-playlist', 'cb': start_matches_thread})

			connect_create_playlist.start()
    
		break #finally, exit thread

thread_joined = False
def start_get_matches_thread():
	global thread_joined
	
	global get_matches_thread
	print('start_get_matches_thread....') #remove #debug

	# if get_matches_thread is None:
	if not thread_joined:
		thread_joined = True

		print('start_get_matches_thread:', get_matches_thread, thread_joined) #remove
		matches_thread_stop_event.clear() #?

		r_params = {'songs': songs_with_lyrics, 'terms': terms, 'stopNum': input_info['stopNum'], 'stopCondition': input_info['stopCondition'], 'relevant_lyrics': relevant_lyrics, 'threshold': 0.05}

		# blob_name = 'blob_data.json' #remove #*
		blob_data = json.dumps(r_params, ensure_ascii=False)
		# blob_block.upload_blob(name=blob_name, data=blob_data, overwrite=True, encoding='utf-8') #remove #*

		global input_blob

		input_blob = google_input_bucket.blob('input-data.json') #new #*

		input_blob.upload_from_string(blob_data) #new #*

		get_matches_thread = Thread(target=get_matches)
		get_matches_thread.start() #current_app._get_current_object() #disconnect #is_connected

		get_matches_thread.join() #new #*
		print('thread is done.')

		thread_joined = False #new #check


class BookshelfThread(Thread):
	def __init__(self):
		self.delay = 1
		super(BookshelfThread, self).__init__()
	def update_bookshelf(self):
		print('updating bookshelf') #debug

		global albums
		albums = [] #reset
		global songs_with_lyrics
		songs_with_lyrics = [] #reset

		while not bookshelf_thread_stop_event.is_set():
			song_count = len(songs)
			for song in songs:
				if index_page_event.is_set(): break #new #*

				song_result = genius.search_song(song['name'], song['artists'][0])

				if song_result is not None:
					song['lyrics'] = f'{song["name"]}\n' + song_result.lyrics
					songs_with_lyrics.append(song)

					album = song['album_art']

					albums.append(album)

					socketio.emit('new_album', {'album': album, 'count': len(albums), 'description': song['name'], 'lyrics': song['lyrics']}, namespace='/create-playlist', broadcast=True)
					socketio.sleep(self.delay)
				else:
					song_count -= 1
					socketio.emit('skip_song', {'song_count': song_count}, namespace='/create-playlist', broadcast=True)
			
			print('done parsing songs.') #remove #debug

			socketio.emit('got_lyrics', {'status': 'Generating jointly embedded topic/doc vectors'}, namespace='/create-playlist', callback=start_get_matches_thread, broadcast=True)
			# socketio.emit('got_lyrics', {'status': 'Generating jointly embedded topic/doc vectors'}, namespace='/create-playlist', broadcast=True)

			bookshelf_thread_stop_event.set()
	def run(self):
		self.update_bookshelf()


class MatchesThread(Thread):
	def __init__(self):
		self.delay = 1
		super(MatchesThread, self).__init__()
	def update_bookshelf_with_matches(self):
		print('updating bookshelf (again), this time to contain only matches') #debug

		socketio.emit('finding_matches', namespace='/create-playlist', broadcast=True)

		theme_songs = []
		subSongs = []
		description = []

		while not matches_thread_stop_event.is_set():
			song_count = len(songs_with_lyrics)
			for song in songs_with_lyrics:				
				if index_page_event.is_set(): break #new #*

				if song in matches:
					print(f'song {song["name"]} is a match.')
					subSongs.append(song['id'])

					if len(subSongs) == 100:
						theme_songs.append(subSongs)
						subSongs = []
				else:
					song_count -= 1
					print('removing:', song['name'], song_count) #debug
					el_id = song['name'].replace(' ', '-')
					socketio.emit('remove_album', {'id': el_id, 'name': song['name'], 'song_count': song_count}, namespace='/create-playlist', broadcast=True)

					socketio.sleep(2)

			if len(subSongs): theme_songs.append(subSongs)

			themes.generatePlaylist(spotify, theme_songs, input_info['saveAs'], description)

			socketio.emit('done', {'song_count': song_count}, namespace='/create-playlist', broadcast=True)
			matches_thread_stop_event.set()
	def run(self):
		self.update_bookshelf_with_matches()


@socketio.on('bookshelf', namespace='/create-playlist')
def bookshelf_start():
	index_page_event.clear() #reset

	global bookshelf_thread

	global def_display

	def_display = 'none'

	print('restarting bookshelf...') #remove #debug

	if bookshelf_thread is None and spotify is not None and nlp is not None:
		print('starting BookshelfThread...') #debug
		bookshelf_thread = BookshelfThread()
		bookshelf_thread.start()


@app.route('/create-playlist')
def create_playlist():
	print('rendering create-playlist page.') #remove #debug
	
	if spotify: return render_template('create-playlist.html', song_count=len(songs), async_mode=socketio.async_mode)
	else: return redirect('/')


status = 'Loading NLP model'
nlpThread = None
songsThread = None


def load_nlp():
	print('loading nlp...') #debug
	global nlp
	while True:
		if nlp is not None: break
		socketio.sleep(1)

		s3.download_file('themed-party-playlist', 'glove_nlp', 'glove.6B.300d.magnitude')

		nlp = Magnitude('glove.6B.300d.magnitude')

	
	print('done loading nlp.') #debug
	global status
	
	status = 'Getting songs'
	socketio.emit('new_status', {'status': status}, broadcast=True)


@socketio.on('load_index') #TODO: change this to 'load-index' or something
def load_index():
	print('loaded index page')
	# os._exit(0)

	# socketio.stop()

	print('loaded index page')
	global def_display

	def_display = 'none' #remove #?

	# global sim_words #go back! #? #v
	# sim_words = [] #^

	index_page_event.set() #set it to stop any threads that might be running

	# if index_page_event.is_set(): break #new #*

	global matches
	matches = None #for now

	global get_matches_thread
	get_matches_thread = None #reset #remove #?
	# index_page_event.clear() #unset it

	# raise RestartException('a message')


@app.route('/', methods=['GET', 'POST'])
def sign_in():
	print('rendering index page.') #remove #debug

	global def_display
	# def_display = 'none'

	global nlpThread

	if nlpThread is None:
		nlpThread = Thread(target=load_nlp)
		nlpThread.start()

	global bookshelf_thread
	global matches_thread

	bookshelf_thread = None #reset
	matches_thread = None #reset

	# index_page_event.set() #set it to stop any threads that might be running

	# index_page_event.clear() #unset it

	bookshelf_thread_stop_event.clear() #unset it
	matches_thread_stop_event.clear() #unset it
	songs_thread_stop_event.clear() #unset it

	global status

	global sim_words

	# sim_words = []

	if not session.get('uuid'):
		# Step 1. Visitor is unknown, give random ID
		session['uuid'] = str(uuid.uuid4())
	
	cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=session_cache_path())

	auth_manager = spotipy.oauth2.SpotifyOAuth(scope='user-library-read playlist-read-private user-top-read playlist-modify-private playlist-modify-public', cache_handler=cache_handler, show_dialog=True)

	if request.args.get("code"):
		# Step 3. Being redirected from Spotify auth page
		auth_manager.get_access_token(request.args.get("code"))
		return redirect('/')
	
	if not auth_manager.validate_token(cache_handler.get_cached_token()):
		# Step 2. Display sign in link when no token
		auth_url = auth_manager.get_authorize_url()

		return render_template('sign-in.html', auth_url=auth_url)
	
	# Step 4. Signed in, display data
	global spotify
	spotify = spotipy.Spotify(auth_manager=auth_manager)

	global userPlaylists #new #*

	userPlaylists = spotify.current_user_playlists(limit=50)['items']
	
	if request.method == 'POST':
		if nlpThread is not None and nlpThread.is_alive(): nlpThread.join() #*

		if 'theme' in request.form: #TODO: and 'stopCondition' and request.form
			sim_words = []

			print('!', request.form.keys(), request.form.get('theme')) #remove #debug

			status = 'Training model'

			input_info['theme'] = request.form.get('theme')

			terms.append(input_info['theme'])

			input_info['method'] = request.form.get('method')
			input_info['stopCondition'] = request.form.get('stopCondition')
			input_info['saveAs'] = request.form.get('saveAs')

			current_time = time.mktime(time.localtime())
			print('current_time:', current_time) #remove #debug
			print(time.localtime()) #remove #debug

			input_info['trainTime'] = int(request.form.get('trainTime'))*60 #convert to seconds

			if input_info['stopCondition'] == 'None': input_info['stopCondition'] = None
			elif input_info['stopCondition'] == 'duration': input_info['stopNum'] = int(request.form.get('stopNum'))*60000 #convert to ms (minutes is just easier for user)
			else: input_info['stopNum'] = int(request.form.get('stopNum'))

			if input_info['method'] == 'playlist': input_info['playlistName'] = request.form.get('playlistName')

			sim_words = get_similar_words(nlp, input_info['theme'], top=6)
			
			# global def_display

			def_display = 'block'

			print('!')

			socketio.emit('reload', {'def_display': 'block'})

			def getSongs():
				global songs

				songs = [] #reset

				while not songs_thread_stop_event.is_set():
					if len(songs): break
					socketio.sleep(1)
					if input_info['method'] != 'genius': songs = themes.get_songs(spotify, input_info)

					global relevant_lyrics

					theme = input_info["theme"]

					csv_file = get_file(f'{theme}.csv')

					if csv_file: # import io # io.StringIO(csv_file) #StringIo
						csv_reader = csv.DictReader(StringIO(csv_file), fieldnames=['name', 'artist', 'lyrics'])

						for row in csv_reader:
							relevant_lyrics.append(row)
					else:
						timeout_start = time.time()

						f = 'name,artist,lyrics'

						page = 1
						while True:
							if time.time() > (timeout_start + input_info['trainTime']) or len(relevant_lyrics) >= 250: break #new limit (1000)

							print('page:', page, 'so far, retrieved', len(relevant_lyrics), 'lyrics') #remove #debug
							term_lyrics = genius.search_lyrics(theme, per_page=20, page=page)

							if not len(term_lyrics['sections'][0]['hits']): break

							for hit in term_lyrics['sections'][0]['hits']:
								song_name = hit['result']['title']
								url = hit['result']['url']

								song_lyrics = genius.lyrics(song_url=url)

								if song_lyrics is not None:
									song_lyrics = re.sub(r'[\d+]?EmbedShare URLCopyEmbedCopy|"', '', song_lyrics)
									song_info = {
										'name': song_name,
										'artist': hit['result']['primary_artist']['name'],
										'lyrics': song_lyrics
									}

									relevant_lyrics.append(song_info)

									f += f'\n{song_info["name"]},{song_info["artist"]},"{song_info["lyrics"]}"'

							page += 1

						github_file = repo.create_file(f'{theme}.csv', 'create_file via PyGithub', f)

					if input_info['method'] == 'genius': #TODO: limit this to like... 100 or something
						for song in relevant_lyrics[:100]:
							results = spotify.search(q=f"artist:{song['artist']} track:{song['name']}", type='track', limit=1)['tracks']

							if results['total'] > 0:
								item = results['items'][0]
								songs.append(
									{
										'name': item['name'],
										'artists': [artist['name'] for artist in item['artists']],
										'duration': item['duration_ms'],
										'release_date': item['album']['release_date'],
										'id': item['id'],
										'album_art': item['album']['images'][0]['url'],
										'lyrics': song['lyrics']
									}
								)
					songs_thread_stop_event.set()

			global songsThread
		
			songsThread = Thread(target=getSongs)
			songsThread = socketio.start_background_task(target=getSongs)

			print('redirecting to "end" the form.')
			return redirect(url_for('sign_in')) #redirect to "end" the form
		else:
			songsThread.join()
			
			status = 'Ready to create playlist'

			for w in request.form.keys():
				print(request.form[w], request.form.keys()) #remove #debug
				if request.form[w] != 'None':
					# topic_dictionary[w] = request.form[w]
					terms.append(w)

			additional_terms = request.form.keys()

			print('terms:', terms) #remove #debug
			sim_words = [] #new #check

			return redirect(url_for('create_playlist'))

	current_time = time.localtime()

	print('def_display:', def_display)

	return render_template("index.html", status=status, sim_words=sim_words, def_display=def_display, theme=input_info['theme'], playlists=userPlaylists, current_time=f'{current_time.tm_hour}:{current_time.tm_min}', async_mode=socketio.async_mode)


def await_response():
	while True:
		socketio.on_event('response', namespace='/remove')
		socketio.sleep()



def delete_playlists(playlists):
	for playlist in playlists:
		spotify.current_user_unfollow_playlist(playlist['id'])



@app.route('/remove', methods=['GET', 'POST'])
def remove_playlists():
	if request.method == 'POST':
		playlist_names = []

		for p in request.form.keys():
			print('p:', p) #remove #debug
			playlist_names.append(p)

		import remove

		all_playlists = remove.getPlaylists(spotify)

		for playlistName in playlist_names:
			playlist_occurences = list(filter(lambda p: p['name'] == playlistName, all_playlists))

			if len(playlist_occurences):
				if len(playlist_occurences) > 1:
					socketio.emit('query_delete_all', {'p_name': playlistName, 'playlists': playlist_occurences}, namespace='/remove', callback=delete_playlists, broadcast=True)

					# await_response_thread = Thread(target=await_response)

					# await_response_thread.start()


					# await_response_thread.join()

					# delete_all = query_yes_no(f"Would you like to delete all occurences of playlists by the name of '{playlistName}'?")

					# if delete_all:
					# 	for p in playlist_occurences:
					# 		spotify.current_user_unfollow_playlist(p['id'])
					# else: spotify.current_user_unfollow_playlist(playlist_occurences[0]['id'])
				else: delete_playlists(playlist_occurences)
			else:
				print(f"no playlists by the name of '{playlistName}' found.")
				continue



	if spotify is None: return redirect('/')
	else: return render_template("remove.html", status=status, playlists=userPlaylists, async_mode=socketio.async_mode)



@socketio.on_error_default
def error_handler(e):
	print('an error has occurred: ' + str(e))
	print(isinstance(e, RestartException))

	# if isinstance(e, RestartException): socketio.emit('reload', {'def_display': 'none'})

	# global def_display

	# def_display = 'none'

	return render_template("index.html", status='redirected', sim_words=sim_words, def_display='none', theme=input_info['theme'], playlists=userPlaylists, current_time=f'', async_mode=socketio.async_mode)
	# pass

# @app.errorhandler(Exception)
# def handle_exception(e):
# 	if isinstance(e, RestartException):
# 		print('restart exception!')
# 		# return redirect('/')

# 	return

@app.errorhandler(Exception)
def handle_exception(e):
	if isinstance(e, RestartException):
		print('restart exception!')
		# return redirect('/')

	return render_template("index.html", status=status, sim_words=sim_words, def_display=def_display, theme=input_info['theme'], playlists=userPlaylists, current_time=f'', async_mode=socketio.async_mode)

# Run application
if __name__ == "__main__":
	# socketio.run(app)
	socketio.run(app, port=port)
	# socketio.run(app, port=port, use_reloader=True)
	# socketio.run(app, port=int(os.environ.get('PORT', 5000)), debug=True)