from threading import Thread, Event

def start_matches_thread(spotify, matches, songs_with_lyrics, save_as): # matches, songs_with_lyrics
	# matches_thread.start()
	try:
		from __main__ import socketio, themes
	except ImportError:
		from app import socketio, themes

	thread_stop_event = Event()

	theme_songs = []

	class MatchesThread(Thread):
		def __init__(self):
			self.delay = 1
			super(MatchesThread, self).__init__()
		def update_bookshelf_with_matches(self):
			# global topic_job
			# matches = topic_job.result

			print('matches:', matches)
			print('updating bookshelf (again), this time to contain only matches') #debug

			socketio.emit('finding_matches', namespace='/create-playlist', broadcast=True)

			subSongs = []
			description = []

			while not thread_stop_event.is_set():
				song_count = len(songs_with_lyrics)
				for song in songs_with_lyrics:
					# if index_page_event.is_set(): break #new #* #TODO: move to main file

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

				themes.generatePlaylist(spotify, theme_songs, save_as, description) #TODO: move to main

				socketio.emit('done', {'song_count': song_count}, namespace='/create-playlist', broadcast=True)
				thread_stop_event.set()
		def run(self):
			self.update_bookshelf_with_matches()
	
	matches_thread = MatchesThread()
	matches_thread.start() #current_app._get_current_object() 

	matches_thread.join() #?

	return theme_songs