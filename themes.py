# import os
# gpt (text generation)
# bayessian analysis (style of what people say based on words they say)
# pybayes

# import lyricsgenius

# import synoynm as syn

# import topic

# from simSearch import getUseableWords

# genius_token = os.getenv('GENIUS_TOKEN')

# if genius_token is None:
# 	import config
# 	genius_token = config.GENIUS_TOKEN

# genius = lyricsgenius.Genius(genius_token)  # access token

# --------
# def analyze(sp, genius, theme, topic_dictionary, method, stopCondition, stopNum):


def get_songs(sp, input_info):
	method, playlistName, songLimit = input_info['method'], input_info['playlistName'], input_info['stopCondition']
	# -------

	songs = []

	offset = 0

	limit = 100 #check

	if method == 'playlist':
		userPlaylists = sp.current_user_playlists(limit=50)

		# TODO: remove emojis, etc
		playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

		playlists_offset = 50

		while len(userPlaylists['items']) == 50 and playlist is None:
			print('checking again...')
			userPlaylists = sp.current_user_playlists(limit=50, offset=playlists_offset)

			playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

			playlists_offset += 50
		
		if playlist is not None: print('found it!')
		else:
			print('playlist not found.')
			return

		userData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=offset)

		songOffset = 100

		while len(userData['items']) < userData['total']:
			addData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=songOffset)
			userData['items'].extend(addData['items'])
			songOffset += 100
		
		song_count = len(userData['items'])
		i = 1

		for item in userData['items']:
			print(f'song {i}/{song_count}')

			track = item['track']

			song = {
				'name': track['name'],
				'artists': [artist['name'] for artist in track['artists']],
				'duration': track['duration_ms'],
				'release_date': track['album']['release_date'],
				'id': track['id'],
				'album_art': item['album']['images'][0]['url']
			}

			songs.append(song)
			i += 1
	else:
		if method == 'top tracks':
			userData = sp.current_user_top_tracks(limit=limit, offset=offset) #TODO: add option of time range (recent [short_term] vs all-time [long_term], also medium_term but ... that is probably overkill)
			
			it = 0
			time_range = 'short_term'

			stopCount = (150 if songLimit is None else limit)


			while it < 2 and len(userData['items']) < stopCount:
				it += 1
				addData = sp.current_user_top_tracks(limit=limit, time_range=time_range)
				for item in addData['items']:
					if item not in userData['items']: userData['items'].append(item)

				time_range = 'long_term'
			
			if len(userData['items']) < limit: print(f'only able to access {len(userData["items"])} top songs.')

			song_count = len(userData['items'])

			i = 1
			for item in userData['items']:
				print(f'song {i}/{song_count}')

				song = {
					'name': item['name'],
					'artists': [artist['name'] for artist in item['artists']],
					'duration': item['duration_ms'],
					'release_date': item['album']['release_date'],
					'id': item['id'],
					'album_art': item['album']['images'][0]['url']
				}

				songs.append(song)
				i += 1
		elif method == 'saved tracks':
			userData = sp.current_user_saved_tracks(limit=(limit if limit < 50 else 50), offset=offset)

			songOffset = 50

			stopCount = userData['total']

			while len(userData['items']) < stopCount:
				addData = sp.current_user_saved_tracks(limit=50, offset=songOffset)
				userData['items'].extend(addData['items'])
				songOffset += 50

			song_count = len(userData['items'])
			i = 1

			for item in userData['items']:
				print(f'song {i}/{song_count}')

				track = item['track']

				song = {
					'name': track['name'],
					'artists': [artist['name'] for artist in track['artists']],
					'duration': track['duration_ms'],
					'release_date': track['album']['release_date'],
					'id': track['id'],
					'album_art': item['album']['images'][0]['url']
				}

				# words = getSongLyrics(song['name'], song['artists'][0])

				songs.append(song)
				i += 1
	
	return songs


def get_song_lyrics(genius, songs):
	songs_with_lyrics = []
	for song in songs:
		song_result = genius.search_song(song['name'], song['artists'][0])

		if song_result is not None:
			song['lyrics'] = f'{song["name"]}\n' + song_result.lyrics
			songs_with_lyrics.append(song)

	return songs_with_lyrics


	# sampleTracks = getSongs(offset=playlistOffset)

	# print('!', len(sampleTracks)) #remove #debug

	# return sampleTracks

def analyze(sp, genius, input_info):
	method, playlistName, songLimit = input_info['method'], input_info['playlistName'], input_info['stopCondition']

	def getSongLyrics(title, artist):
		song = genius.search_song(title, artist)
		# while True:
		# 	try:
		# 		song = genius.search_song(title, artist)
		# 		break
		# 	except: pass
		
		# from requests.exceptions import Timeout
		# retries = 0
		# while retries < 3:
		# 	try:
		# 		song = genius.search_song(title, artist)
		# 	except Timeout as e:
		# 		retries += 1
		# 		continue
		# 	if song is not None: return f'{title}\n' + song.lyrics
		# 	else: return None

		if song is not None: return f'{title}\n' + song.lyrics
		else: return None

	playlistOffset = 0
	# -------

	sampleTracks = []

	def getSongs(offset=0):
		songs = []

		limit = 100 #check

		if method == 'playlist':
			userPlaylists = sp.current_user_playlists(limit=50)

			# TODO: remove emojis, etc
			playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

			playlists_offset = 50

			while len(userPlaylists['items']) == 50 and playlist is None:
				print('checking again...')
				userPlaylists = sp.current_user_playlists(limit=50, offset=playlists_offset)

				playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

				playlists_offset += 50
			
			if playlist is not None: print('found it!')
			else:
				print('playlist not found.')
				return

			userData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=offset)

			songOffset = 100

			while len(userData['items']) < userData['total']:
				addData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=songOffset)
				userData['items'].extend(addData['items'])
				songOffset += 100
			
			song_count = len(userData['items'])
			i = 1

			for item in userData['items']:
				print(f'song {i}/{song_count}')

				track = item['track']

				song = {
					'name': track['name'],
					'artists': [artist['name'] for artist in track['artists']],
					'duration': track['duration_ms'],
					'release_date': track['album']['release_date'],
					'id': track['id'],
					'album_art': item['album']['images'][0]['url']
				}

				song['lyrics'] = getSongLyrics(song['name'], song['artists'][0])

				if song['lyrics'] is not None: songs.append(song)
				i += 1
		else:
			if method == 'top tracks':
				userData = sp.current_user_top_tracks(limit=limit, offset=offset) #TODO: add option of time range (recent [short_term] vs all-time [long_term], also medium_term but ... that is probably overkill)
				
				it = 0
				time_range = 'short_term'

				stopCount = (150 if songLimit is None else limit)


				while it < 2 and len(userData['items']) < stopCount:
					it += 1
					addData = sp.current_user_top_tracks(limit=limit, time_range=time_range)
					for item in addData['items']:
						if item not in userData['items']: userData['items'].append(item)

					time_range = 'long_term'
				
				if len(userData['items']) < limit: print(f'only able to access {len(userData["items"])} top songs.')

				song_count = len(userData['items'])

				i = 1
				for item in userData['items']:
					print(f'song {i}/{song_count}')

					song = {
						'name': item['name'],
						'artists': [artist['name'] for artist in item['artists']],
						'duration': item['duration_ms'],
						'release_date': item['album']['release_date'],
						'id': item['id'],
						'album_art': item['album']['images'][0]['url']
					}

					song['lyrics'] = getSongLyrics(song['name'], song['artists'][0])

					if song['lyrics'] is not None: songs.append(song)
					i += 1
			elif method == 'saved tracks':
				userData = sp.current_user_saved_tracks(limit=(limit if limit < 50 else 50), offset=offset)

				songOffset = 50

				stopCount = userData['total']

				while len(userData['items']) < stopCount:
					addData = sp.current_user_saved_tracks(limit=50, offset=songOffset)
					userData['items'].extend(addData['items'])
					songOffset += 50

				song_count = len(userData['items'])
				i = 1

				for item in userData['items']:
					print(f'song {i}/{song_count}')

					track = item['track']

					song = {
						'name': track['name'],
						'artists': [artist['name'] for artist in track['artists']],
						'duration': track['duration_ms'],
						'release_date': track['album']['release_date'],
						'id': track['id'],
						'album_art': item['album']['images'][0]['url']
					}

					# words = getSongLyrics(song['name'], song['artists'][0])

					song['lyrics'] = getSongLyrics(song['name'], song['artists'][0])
					# if words is not None: lyrics.append(words)
					# getSongLyrics(song['name'], song['artists'][0])

					if song['lyrics'] is not None: songs.append(song)
					i += 1
		
		return songs


	sampleTracks = getSongs(offset=playlistOffset)

	print('!', len(sampleTracks)) #remove #debug

	return sampleTracks



	

# #--- MAIN FUNCTION ---
# # def parseLyrics(genius, topic_dictionary, song):
# def matches(terms, song):
# # def parseLyrics(genius, terms, song):
# 	'''
# 	Retreives lyrics from genius & goes through them to see if they match the provided theme

# 	Parameters:
# 	----------
# 		* TODO
# 	'''

# 	songMatch = None
# 	description = None

# 	songName = song['name']
# 	primaryArtist = song['artists'][0]
# 	songLyrics = song['lyrics'] #new

# 	if songLyrics is not None:
# 		sim_score, word_matches = topic.similarity(songLyrics, terms)

# 		if sim_score is not None:
# 			print(f"Adding {songName} by {primaryArtist} to playlist because it passes the similarity threshold with a score of {sim_score} and contains the keywords: {word_matches}\n")

# 			songMatch = song
# 			description = f"{songName}: {word_matches}"
# 		else: print(f"SKIPPING: {songName} by {primaryArtist} does not match.")

# 	return songMatch, description


def generatePlaylist(sp, playlistSongs, saveAs, description=''):
	currentUser = sp.me()
	userId = currentUser['id']

	if len(playlistSongs):
		print(f"\nCreating playlist '{saveAs}'...")
		themePlaylist = sp.user_playlist_create(user=userId, name=saveAs, description='\n'.join(description))

		for songs in playlistSongs:
			sp.playlist_add_items(playlist_id=themePlaylist['id'], items=songs)

		# sp.playlist_add_items(playlist_id=themePlaylist['id'], items=playlistSongs)
	else: print(f'sorry, no songs match the theme.')


	# ----------------



	'''
	playlist_cover_image
	recommendation_genre_seeds()
	genre
	'''
