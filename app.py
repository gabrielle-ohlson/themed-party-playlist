# backend for web app
# import eventlet
# eventlet.monkey_patch()
async_mode = None

if async_mode is None:
	# if async_mode is None:
	try:
		from gevent import monkey
		# async_mode = 'gevent'
		async_mode = 'gevent'
	except ImportError:
		pass
	
	'''
	if async_mode is None:
		try:
			import eventlet
			async_mode = 'eventlet'
		except ImportError:
			pass
	'''

	if async_mode is None:
		async_mode = 'threading'

	print('async_mode is ' + async_mode)


# monkey patching is necessary because this application uses a background
if async_mode == 'gevent':
	from gevent import monkey
	monkey.patch_all()
# elif async_mode == 'eventlet':
# 	import eventlet
# 	eventlet.monkey_patch()


from flask import Flask, session, request, redirect, render_template, url_for
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

import lyricsgenius
import spotipy

from github import Github #TODO: install

import themes
import topic
from sim import get_similar_words

# import base64
import csv #*

maxInt = sys.maxsize

while True:
	# decrease the maxInt value by factor 10 
	# as long as the OverflowError occurs.

	try:
		csv.field_size_limit(maxInt)
		break
	except OverflowError:
		maxInt = int(maxInt/10)

import gensim.downloader as gensim_api
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

# TESTING = True
# DEBUG = True
app.config['FLASK_ENV'] = 'development'
app.config['SECRET_KEY'] = environ.get('SECRET_KEY')

app.config['GENIUS_TOKEN']=environ.get('GENIUS_TOKEN')

app.config['SPOTIPY_CLIENT_ID']=environ.get('SPOTIPY_CLIENT_ID')

app.config['SPOTIPY_CLIENT_SECRET']=environ.get('SPOTIPY_CLIENT_SECRET')

app.config['GITHUB_TOKEN']=environ.get('GITHUB_TOKEN')


# app.config['SPOTIPY_REDIRECT_URI']=environ.get('SPOTIPY_REDIRECT_URI')

app.config['SPOTIPY_REDIRECT_URI']= 'http://127.0.0.1:5000/'

if (os.environ.get('PORT')):
	port = os.environ.get('PORT')
else:
	port = 5000

genius_token = os.getenv('GENIUS_TOKEN')

# genius = lyricsgenius.Genius(genius_token)  # access token
# genius = lyricsgenius.Genius(genius_token, timeout=15, sleep_time=1)  # access token
genius = lyricsgenius.Genius(genius_token, timeout=15, retries=3, remove_section_headers=True)  # access token

github_token = os.getenv('GITHUB_TOKEN')

github = Github(github_token)

repo = github.get_user().get_repo('lyrics-storage')

# query_url = f"https://api.github.com/repos/gabrielle-ohlson/lyrics-storage/contents/"
query_url = f"https://raw.githubusercontent.com/gabrielle-ohlson/lyrics-storage/main/"

def get_file(filename):
	try:
		r = requests.get(query_url+filename)
		r.raise_for_status()
		# r = requests.get(query_url+filename, headers={
		# 	'User-Agent': 'request',
		# 	'Authorization': f'token {github_token}'})

		file_content = r.text

		# print('file_content:', file_content) #remove #debug
		# r.raise_for_status()
		# data = r.json()
		# file_content = data['content']
		# file_content_encoding = data.get('encoding')
		# if file_content_encoding == 'base64': file_content = base64.b64decode(file_content).decode()

		# print('file_content:', file_content)
		# return file_content

		# print(filename, repo.get_contents())
		# file = repo.get_contents(filename)
		# print('file:', file)
	except:
		return False

	return file_content

# async_mode = 'threading' #None
# socketio = SocketIO(app, async_mode='threading')
# socketio = SocketIO(app, async_mode=async_mode)
# socketio.init_app(app, cors_allowed_origins="*")

# socketio.set('transports', ['websocket'])

# Set this variable to "threading", "eventlet" or "gevent" to test the
# different async modes, or leave it set to None for the application to choose
# the best option based on available packages.


# socketio = SocketIO(app, async_mode=None, cors_allowed_origins="*")
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins=[
	'http://localhost:5000', 'https://localhost:5000',
	'https://themed-party-playlist.herokuapp.com', 'https://themed-party-playlist.herokuapp.com/create-playlist',
	'http://themed-party-playlist.herokuapp.com', 'http://themed-party-playlist.herokuapp.com/create-playlist',
	'http://127.0.0.1:5000', 'http://127.0.0.1:5000/create-playlist', 
	'https://127.0.0.1:5000', 'https://127.0.0.1:5000/create-playlist',
	'http://0.0.0.0:5000', 'http://0.0.0.0:5000/create-playlist'])

#update_bookshelf Generator Thread
bookshelf_thread = None

thread_stop_event = Event()

songs_thread_stop_event = Event()

matches_thread = None

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

userPlaylists = None

topic_dictionary = {}
terms = []

albums = []
songs = []
relevant_lyrics = []
songs_with_lyrics = []
matches = None

info = { 'duration': 0, 'song count': 0 }

def reachedLimit():
	'''
	function to check whether the playlist is at the max length (aka met stop condition)
	'''
	if input_info['stopNum'] is None or abs(input_info['stopNum']-info[input_info['stopCondition']]) >= 60000 or info[input_info['stopCondition']] < input_info['stopNum']: return False
	else: return True #break if within 1 minute of stopNum or exceeded stopNum
	# if abs(stopNum-info[stopCondition]) < 60000 or info[stopCondition] > stopNum: return False #break if within 1 minute of stopNum or exceeded stopNum
	# else: return True


class BookshelfThread(Thread):
	def __init__(self):
		self.delay = 1
		super(BookshelfThread, self).__init__()
	def update_bookshelf(self):
		print('updating bookshelf')

		# songs_with_lyrics = []
		global albums
		albums = [] #reset
		global songs_with_lyrics

		while not thread_stop_event.is_set():
			song_count = len(songs)
			for song in songs:
				song_result = genius.search_song(song['name'], song['artists'][0])

				if song_result is not None:
					song['lyrics'] = f'{song["name"]}\n' + song_result.lyrics
					songs_with_lyrics.append(song)

					album = song['album_art']

					albums.append(album)

					socketio.emit('new_album', {'album': album, 'count': len(albums), 'description': song['name']}, broadcast=True)
					socketio.sleep(self.delay)
				else:
					song_count -= 1
					socketio.emit('skip_song', {'song_count': song_count}, broadcast=True)
			socketio.emit('got_lyrics', broadcast=True)
			
			# matches = topic.top_lyrics(songs_with_lyrics, terms, stopNum=((input_info['stopNum']//210000) if input_info['stopCondition'] == 'duration' else input_info['stopNum']), relevant_lyrics=relevant_lyrics) # 210000 = 3.5 minutes (average song length)

			# not_matches = [song for song in songs in song not in matches]

			# for song in not_matches:

			thread_stop_event.set()
	def run(self):
		self.update_bookshelf()


class MatchesThread(Thread):
	def __init__(self):
		self.delay = 1
		super(MatchesThread, self).__init__()
	def update_bookshelf(self):
		print('updating bookshelf (again)')

		socketio.emit('finding_matches', broadcast=True)

		theme_songs = []
		subSongs = []
		description = []

		while not thread_stop_event.is_set():
			song_count = len(songs_with_lyrics)
			for song in songs_with_lyrics:
				if song in matches:
					subSongs.append(song['id'])

					if len(subSongs) == 100:
						theme_songs.append(subSongs)
						subSongs = []
				else:
					song_count -= 1
					print('removing:', song['name'], song_count)
					el_id = song['name'].replace(' ', '-')
					socketio.emit('remove_album', {'id': el_id, 'name': song['name'], 'song_count': song_count}, broadcast=True)
					# socketio.sleep(2000)
					socketio.sleep(2)

			if len(subSongs): theme_songs.append(subSongs)

			themes.generatePlaylist(spotify, theme_songs, input_info['saveAs'], description)

			socketio.emit('done', {'song_count': song_count}, broadcast=True)
			thread_stop_event.set()
	def run(self):
		self.update_bookshelf()


@socketio.on('bookshelf')
def connect():
	print('connecting...')
	global bookshelf_thread

	if bookshelf_thread is None and spotify is not None:
		print('starting BookshelfThread...')
		bookshelf_thread = BookshelfThread()
		bookshelf_thread.start()


@socketio.on('find_matches')
def get_matches():
	global matches_thread

	if matches_thread is None:
		thread_stop_event.clear()

		global matches
		matches = topic.top_lyrics(songs_with_lyrics, terms, stopNum=((input_info['stopNum']//210000) if input_info['stopCondition'] == 'duration' else input_info['stopNum']), relevant_lyrics=relevant_lyrics) # 210000 = 3.5 minutes (average song length)

		print('starting MatchesThread...')
		matches_thread = MatchesThread()
		matches_thread.start()


@app.route('/create-playlist')
def create_playlist():
	if spotify: return render_template('create-playlist.html', song_count=len(songs), async_mode=socketio.async_mode)
	else: return redirect('/')


status = 'Loading NLP model'
nlpThread = None
songsThread = None

def load_nlp():
	print('loading nlp...')
	global nlp
	while True:
		if nlp is not None: break
		socketio.sleep(1)
		nlp = gensim_api.load("glove-wiki-gigaword-300")
	
	print('done loading nlp.')
	global status
	status = 'Getting songs'


#do this right away
# if nlpThread is None:
# 	nlpThread = socketio.start_background_task(target=load_nlp)
	# nlpThread = Thread(target=load_nlp)
	# nlpThread.start()


@app.route('/', methods=['GET', 'POST'])
def sign_in():
	print('back to index page') #remove #debug
	global bookshelf_thread
	global matches_thread

	bookshelf_thread = None #reset
	matches_thread = None #reset

	thread_stop_event.clear() #unset it
	songs_thread_stop_event.clear() #unset it

	global status

	global nlpThread
	
	if nlpThread is None:
		nlpThread = Thread(target=load_nlp)
		nlpThread.start()

	sim_words = []

	def_display = 'none'

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

		return render_template('sign-in.html', auth_url=auth_url) #new
		# return f'<h2><a href="{auth_url}">Sign in</a></h2>'
	
	# Step 4. Signed in, display data
	global spotify
	spotify = spotipy.Spotify(auth_manager=auth_manager)
	
	if request.method == 'POST':
		if 'theme' in request.form: #TODO: and 'stopCondition' and request.form
			status = 'Training model'

			input_info['theme'] = request.form.get('theme')

			terms.append(input_info['theme'])

			input_info['method'] = request.form.get('method')
			input_info['stopCondition'] = request.form.get('stopCondition')
			input_info['saveAs'] = request.form.get('saveAs')
			input_info['trainTime'] = int(request.form.get('trainTime'))*60 #convert to seconds

			if input_info['stopCondition'] == 'None': input_info['stopCondition'] = None
			elif input_info['stopCondition'] == 'duration': input_info['stopNum'] = int(request.form.get('stopNum'))*60000 #convert to ms (minutes is just easier for user)
			else: input_info['stopNum'] = int(request.form.get('stopNum'))

			if input_info['method'] == 'playlist': input_info['playlistName'] = request.form.get('playlistName')

			sim_words = get_similar_words(nlp, [input_info['theme']], top=6)
			
			def_display = 'block'

			def getSongs():
				global songs

				songs = [] #reset

				# while True:
				while not songs_thread_stop_event.is_set(): #new
					if len(songs): break
					socketio.sleep(1)
					if input_info['method'] != 'genius': songs = themes.get_songs(spotify, input_info)

					global relevant_lyrics

					theme = input_info["theme"]

					csv_file = get_file(f'{theme}.csv')

					if csv_file: # import io # io.StringIO(csv_file) #StringIo
						# csv_reader = csv.DictReader(csv_file.splitlines(), fieldnames=['name', 'artist', 'lyrics'])
						csv_reader = csv.DictReader(StringIO(csv_file), fieldnames=['name', 'artist', 'lyrics'])

						for row in csv_reader:
							# print('row:', row['lyrics']) #remove #debug
							# file_content = row['lyrics']
							# file_content_encoding = data.get('encoding')
							# if file_content_encoding == 'base64': file_content = base64.b64decode(file_content).decode()
							# file_content_encoding = row.get('encoding')

							# print(file_content_encoding, 'z1')
							# if file_content_encoding == 'base64': file_content = base64.b64decode(file_content).decode()

							# print(file_content_encoding, 'z1dfgs')


							relevant_lyrics.append(row)
					else:
						timeout_start = time.time()

						f = 'name,artist,lyrics'

						page = 1
						while True:
							if time.time() > (timeout_start + input_info['trainTime']) or len(relevant_lyrics) >= 1000: break #new limit (1000)

							print('page:', page, len(relevant_lyrics)) #remove #debug
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

			# global songs
			# songs = [] #reset

			global songsThread
		
			# if songsThread is None and input_info['method'] != 'genius':
			songsThread = Thread(target=getSongs)
			songsThread = socketio.start_background_task(target=getSongs)
		else:
			songsThread.join()
			
			status = 'Ready to create playlist'
			# if input_info['method'] != 'genius': songsThread.join()

			# global relevant_lyrics
			# for w in request.form.keys():
			# 	if request.form[w] != 'None':
			# 		terms.append(w)

			# 		csv_file = get_file(f'{w}.csv')

			# 		if csv_file:
			# 			# with open(f'/static/lyrics/{w}.csv', newline='') as csv_file:
			# 			csv_reader = csv.DictReader(csv_file)

			# 			for row in csv_reader:
			# 				relevant_lyrics.append(row)
			# 					# relevant_lyrics.append(
			# 					# 	{
			# 					# 		'name': row['name'],
			# 					# 		'artist': row['artist'],
			# 					# 		'lyrics': row['lyrics']
			# 					# 	}
			# 					# )
			# 		else:
			# 			f = 'name,artist,lyrics'
			# 			# with open(f'{w}.csv', 'w', newline='') as csv_file:
			# 			# csv_writer = csv.DictWriter(csv_file, fieldnames=['name', 'artist', 'lyrics'])

			# 			# csv_writer.writeheader()

			# 			page = 1
			# 			while True:
			# 				print('page:', page, len(relevant_lyrics)) #remove #debug
			# 				term_lyrics = genius.search_lyrics(w, per_page=20, page=page)

			# 				if not len(term_lyrics['sections'][0]['hits']): break

			# 				for hit in term_lyrics['sections'][0]['hits']:
			# 					song_name = hit['result']['title']
			# 					url = hit['result']['url']

			# 					song_lyrics = genius.lyrics(song_url=url)

			# 					if song_lyrics is not None:
			# 						song_lyrics = re.sub(r'[\d+]?EmbedShare URLCopyEmbedCopy|"', '', song_lyrics)
			# 						song_info = {
			# 							'name': song_name,
			# 							'artist': hit['result']['primary_artist']['name'],
			# 							'lyrics': song_lyrics
			# 						}

			# 						relevant_lyrics.append(song_info)

			# 						f += f'\n{song_info["name"]},{song_info["artist"]},"{song_info["lyrics"]}"'
			# 						# csv_writer.writerow(song_info)

			# 				page += 1

			# 			# github_file = repo.create_file(f'{w}.csv', 'create_file via PyGithub', csv_file.read())
			# 			github_file = repo.create_file(f'{w}.csv', 'create_file via PyGithub', f)


			# 		print('len of rel lyrics:', len(relevant_lyrics))

			# 		# term_lyrics = genius.search_lyrics(w, per_page=50)

			# 		# for hit in term_lyrics['sections'][0]['hits']:
			# 		# 	# print(hit['result'].keys())
			# 		# 	song_name = hit['result']['title']
			# 		# 	url = hit['result']['url']

			# 		# 	song_lyrics = genius.lyrics(song_url=url)

			# 		# 	# if song_lyrics is not None: relevant_lyrics.append(song_lyrics)
			# 		# 	if song_lyrics is not None:
			# 		# 		relevant_lyrics.append(
			# 		# 			{
			# 		# 				'name': song_name,
			# 		# 				'artist': hit['result']['primary_artist']['name'],
			# 		# 				'lyrics': song_lyrics
			# 		# 			}
			# 		# 		)
			# 		# 		# relevant_lyrics[song_name] = song_lyrics

			# if input_info['method'] == 'genius':
			# 	global songs
			# 	for song in relevant_lyrics:
			# 		# item = spotify.search(song['name'], type='track', limit=1) #TODO: search with artist
			# 		results = spotify.search(q=f"artist:{song['artist']} track:{song['name']}", type='track', limit=1)['tracks'] #TODO: search with artist
			# 		if results['total'] > 0:
			# 			item = results['items'][0]
			# 			songs.append(
			# 				{
			# 					'name': item['name'],
			# 					'artists': [artist['name'] for artist in item['artists']],
			# 					'duration': item['duration_ms'],
			# 					'release_date': item['album']['release_date'],
			# 					'id': item['id'],
			# 					'album_art': item['album']['images'][0]['url'],
			# 					'lyrics': song['lyrics']
			# 				}
			# 			)
			# 	# songs = relevant_lyrics.copy()
			# 	# relevant_lyrics = []
			
			print('terms:', terms) #remove #debug

			# import topic
			# topic.top_lyrics(songs, terms, stopNum=((input_info['stopNum']//210000) if input_info['stopCondition'] == 'duration' else input_info['stopNum']), relevant_lyrics=relevant_lyrics) # 210000 = 3.5 minutes (average song length)

			return redirect(url_for('create_playlist'))

	return render_template("index.html", status=status, sim_words=sim_words, def_display=def_display, theme=input_info['theme'])



# Run application
if __name__ == "__main__":
	# socketio.run(app)
	socketio.run(app, port=port)
		# socketio.run(app, port=port, debug=True)

	# socketio.run(app,  port=int(os.environ.get('PORT', 5000)), debug=True)


# Installing collected packages: protobuf, tensorflow-hub, libclang, tensorflow-estimator, google-pasta, astunparse, opt-einsum, oauthlib, requests-oauthlib, pyasn1, rsa, pyasn1-modules, cachetools, google-auth, google-auth-oauthlib, tensorboard-data-server, absl-py, tensorboard-plugin-wit, grpcio, zipp, importlib-metadata, markdown, tensorboard, termcolor, wrapt, keras, keras-preprocessing, flatbuffers, h5py, tensorflow-io-gcs-filesystem, gast, tensorflow, tensorflow-text

# Successfully installed absl-py-1.0.0 astunparse-1.6.3 cachetools-4.2.4 flatbuffers-2.0 gast-0.4.0 google-auth-2.3.3 google-auth-oauthlib-0.4.6 google-pasta-0.2.0 grpcio-1.42.0 h5py-3.6.0 importlib-metadata-4.8.2 keras-2.7.0 keras-preprocessing-1.1.2 libclang-12.0.0 markdown-3.3.6 oauthlib-3.1.1 opt-einsum-3.3.0 protobuf-3.19.1 pyasn1-0.4.8 pyasn1-modules-0.2.8 requests-oauthlib-1.3.0 rsa-4.8 tensorboard-2.7.0 tensorboard-data-server-0.6.1 tensorboard-plugin-wit-1.8.0 tensorflow-2.7.0 tensorflow-estimator-2.7.0 tensorflow-hub-0.12.0 tensorflow-io-gcs-filesystem-0.22.0 tensorflow-text-2.7.3 termcolor-1.1.0 wrapt-1.13.3 zipp-3.6.0