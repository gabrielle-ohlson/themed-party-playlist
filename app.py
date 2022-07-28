# backend for web app
# import asyncio

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
import time


import lyricsgenius
import spotipy

from pymagnitude import *

from os import environ, path
from dotenv import load_dotenv

import themes
import topic
from sim import get_similar_words

# ------------------

nlp = None
nlp_task = None

# We must now create our app, which I will store in a variable called `app`:
app = Flask(__name__, static_url_path='/static')

app.config['SECRET_KEY'] = os.urandom(64)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session'


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

app.config['SPOTIPY_REDIRECT_URI']= 'http://127.0.0.1:5000/'

app.config['FLASKS3_BUCKET_NAME'] = 'themed-party-playlist'


if (os.environ.get('PORT')):
	port = os.environ.get('PORT')
else:
	port = 5000

genius_token = os.getenv('GENIUS_TOKEN')

genius = lyricsgenius.Genius(genius_token, timeout=15, retries=3, remove_section_headers=True)  # access token


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

thread_stop_event = Event()

songs_thread_stop_event = Event()

index_page_event = Event()

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

userPlaylists = {}

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


@socketio.on('connect')
def register_client():
	if request.namespace not in connected_clients: connected_clients.append(request.namespace)
	print(f'connected: {request.sid}. Namespace: {request.namespace}. (total connections: {len(connected_clients)})')


@socketio.on('connect', namespace='/create-playlist')
def register_client():
	if request.namespace not in connected_clients: connected_clients.append(request.namespace)
	print(f'connected: {request.sid}. Namespace: {request.namespace}. (total connections: {len(connected_clients)})')


@socketio.on('disconnect')
def unregister_client():
	print('disconnected:', request.sid, request.namespace)
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

		while not thread_stop_event.is_set():
			song_count = len(songs)
			for song in songs:
				if index_page_event.is_set(): break #new #*

				song_result = genius.search_song(song['name'], song['artists'][0])

				if song_result is not None:
					lyrics = re.sub(r'\d+(Embed)', '', song_result.lyrics)
					song['lyrics'] = f'{song["name"]}\n' + lyrics
					songs_with_lyrics.append(song)

					album = song['album_art']

					albums.append(album)

					socketio.emit('new_album', {'album': album, 'count': len(albums), 'description': song['name'], 'lyrics': song['lyrics']}, namespace='/create-playlist', broadcast=True)
					socketio.sleep(self.delay)
				else:
					song_count -= 1
					socketio.emit('skip_song', {'song_count': song_count}, namespace='/create-playlist', broadcast=True)
			
			def get_matches():
				global matches_thread

				if matches_thread is None:
					thread_stop_event.clear()

					global matches
					matches = topic.top_lyrics(nlp, songs_with_lyrics, terms, stopNum=input_info['stopNum'], stopCondition=input_info['stopCondition']) # 210000 = 3.5 minutes (average song length)

					print('got matches.') #remove #debug
					
					def start_matches_thread():
						print('start_matches_thread....') #remove #debug
						matches_thread = MatchesThread()
						matches_thread.start() #current_app._get_current_object() #disconnect #is_connected

					with app.test_request_context():
						connect_create_playlist = Thread(target=await_connection, kwargs={'ns': '/create-playlist', 'cb': start_matches_thread})

						connect_create_playlist.start()


			socketio.emit('got_lyrics', {'status': 'Generating jointly embedded topic/doc vectors'}, namespace='/create-playlist', callback=get_matches, broadcast=True)

			thread_stop_event.set()
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

		while not thread_stop_event.is_set():
			song_count = len(songs_with_lyrics)
			for song in songs_with_lyrics:
				print(index_page_event.is_set()) #remove #debug
				
				if index_page_event.is_set(): break #new #*

				if song in matches:
					el_id = song['name'].replace(' ', '-')
					socketio.emit('keep_album', {'id': el_id, 'name': song['name'], 'keywords': song['keywords']}, namespace='/create-playlist', broadcast=True)

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
			thread_stop_event.set()
	def run(self):
		self.update_bookshelf_with_matches()


@socketio.on('bookshelf', namespace='/create-playlist')
def bookshelf_start():
	index_page_event.clear() #reset

	global bookshelf_thread

	print('restarting bookshelf...\nbookshelf_thread is:', bookshelf_thread, 'namespace is:', request.namespace) #remove #debug

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

	# nlp = Magnitude('static/GoogleNews-vectors-negative300.magnitude') #TODO: maybe switch back to lite #TODO: convert '_' to '-'
	nlp = Magnitude('http://magnitude.plasticity.ai/word2vec/medium/GoogleNews-vectors-negative300.magnitude', stream=True) #TODO: maybe switch back to lite #TODO: convert '_' to '-'
	
	print('done loading nlp.') #debug
	global status
	
	# status = 'Getting songs'
	status = 'Ready'
	socketio.emit('new_status', {'status': status}, broadcast=True)


def_display = 'none'

@socketio.on('load_index') #TODO: change this to 'load-index' or something
def load_index():
	print('loaded index page')
	global def_display

	def_display = 'none'

	global sim_words
	sim_words = []

	index_page_event.set() #set it to stop any threads that might be running



@app.route('/', methods=['GET', 'POST'])
def sign_in():
	print('rendering index page.') #remove #debug
	
	global nlp_task
	if nlp is None:
		nlp_task = socketio.start_background_task(target=load_nlp)

	global bookshelf_thread
	global matches_thread

	bookshelf_thread = None #reset
	matches_thread = None #reset

	thread_stop_event.clear() #unset it
	songs_thread_stop_event.clear() #unset it

	global status

	global sim_words

	sim_words = []

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

	userPlaylists = spotify.current_user_playlists(limit=50)['items']
	
	if request.method == 'POST':
		if nlp is None: nlp_task.join() #new #*
		status = 'Getting songs' #new *
		socketio.emit('new_status', {'status': status}, broadcast=True) #new #*

		if 'theme' in request.form: #TODO: and 'stopCondition' and request.form
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
			
			global def_display

			def_display = 'block'

			def getSongs():
				global songs

				songs = [] #reset

				while not songs_thread_stop_event.is_set():
					if len(songs): break
					socketio.sleep(1)
					if input_info['method'] != 'genius': songs = themes.get_songs(spotify, input_info)

					global relevant_lyrics

					theme = input_info["theme"]

					if input_info['method'] == 'genius': #TODO: limit this to like... 100 or something
						timeout_start = time.time()

						# max_songs = 250
						max_songs = 0 # TODO: edit and have this for method of genius

						# f = 'name,artist,lyrics'

						page = 1
						while True:
							current_time = time.time()
							if current_time > (timeout_start + input_info['trainTime']) or len(relevant_lyrics) >= max_songs: break #new limit (1000)

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

							print(f'page: {page}. so far, retrieved ({len(relevant_lyrics)}/{max_songs}) lyrics ({current_time-timeout_start} elapsed)') #remove #debug

							page += 1

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
		else:
			songsThread.join()
			
			status = 'Ready to create playlist'

			return redirect(url_for('create_playlist'))

	current_time = time.localtime()

	return render_template("index.html", status=status, sim_words=sim_words, def_display=def_display, theme=input_info['theme'], playlists=userPlaylists, current_time=f'{current_time.tm_hour}:{current_time.tm_min}', async_mode=socketio.async_mode)


# Run application
if __name__ == "__main__":
	socketio.run(app, port=port)
