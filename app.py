# backend for web app

from flask.wrappers import Response

from time import sleep

from flask import Flask, session, request, redirect, render_template, url_for
from flask_session import Session

from flask_socketio import SocketIO, emit
from threading import Thread, Event

import lyricsgenius

import spotipy
import uuid
import os

import themes
import synoynm as syn
from simSearch import getUseableWords

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

# app.config['SPOTIPY_REDIRECT_URI']=environ.get('SPOTIPY_REDIRECT_URI')

app.config['SPOTIPY_REDIRECT_URI']= 'http://127.0.0.1:5000/'

genius_token = os.getenv('GENIUS_TOKEN')
genius = lyricsgenius.Genius(genius_token)  # access token


async_mode = 'threading' #None
# socketio = SocketIO(app, async_mode='threading')
# socketio = SocketIO(app, async_mode=async_mode)
# socketio.init_app(app, cors_allowed_origins="*")

# socketio.set('transports', ['websocket'])

socketio = SocketIO(app, cors_allowed_origins="*")

#update_bookshelf Generator Thread
thread = Thread()
thread_stop_event = Event()

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
	'info': { 'duration': 0, 'song count': 0 }
}

userPlaylists = None

topic_dictionary = {}

albums = []
songs = []


class BookshelfThread(Thread):
	def __init__(self):
		self.delay = 1
		super(BookshelfThread, self).__init__()
	def update_bookshelf(self):
		theme_songs = []
		description = []

		while not thread_stop_event.is_set():
			for song in songs: # 1 at a time
				songs_sample = [song]

				matches, albumArt, desc = themes.parseLyrics(genius, input_info, topic_dictionary, songs_sample)
				theme_songs.extend(matches)
				description.extend(desc)

				if len(albumArt):
					album = albumArt[0]
					albums.append(album)

					socketio.emit('new_album', {'album': album, 'count': len(albums)})
					socketio.sleep(self.delay)

			themes.generatePlaylist(spotify, theme_songs, input_info['saveAs'], description)
	def run(self):
		self.update_bookshelf()


@socketio.on('connect')
def connect():
	global thread
	if not thread.isAlive():
		thread = BookshelfThread()
		thread.start()


@app.route('/create-playlist')
def create_playlist():
	if spotify: return render_template('create-playlist.html', async_mode=socketio.async_mode)
	else: return redirect('/')


@app.route('/', methods=['GET', 'POST'])
def sign_in():
	words_defs = []

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
		return f'<h2><a href="{auth_url}">Sign in</a></h2>'
	
	# Step 4. Signed in, display data
	global spotify
	spotify = spotipy.Spotify(auth_manager=auth_manager)
	
	if request.method == 'POST':
		if 'theme' in request.form:
			input_info['theme'] = request.form.get('theme')
			input_info['method'] = request.form.get('method')
			input_info['stopCondition'] = request.form.get('stopCondition')
			input_info['saveAs'] = request.form.get('saveAs')

			if input_info['stopCondition'] == 'None': input_info['stopCondition'] = None
			else: input_info['stopNum'] = int(request.form.get('stopNum'))*60000 #convert to ms (minutes is just easier for user)

			if input_info['method'] == 'playlist': input_info['playlistName'] = request.form.get('playlistName')

			useableWords = getUseableWords(input_info['theme'])
			
			for w in useableWords:
				definitions = syn.word_scorer(w)
				if len(definitions) > 1: words_defs.append([w, syn.word_scorer(w)])
				else:
					definition = definitions[0][0]
					topic_dictionary[w] = definition
			
			def_display = 'block'
		else:
			for w in request.form.keys():
				topic_dictionary[w] = request.form[w]

			global songs
			songs = themes.analyze(spotify, input_info)
			return redirect(url_for('create_playlist'))

	return render_template("index.html", count=1, words_defs=words_defs, def_display=def_display, theme=input_info['theme'])



# Run application
if __name__ == "__main__":
	socketio.run(app)
