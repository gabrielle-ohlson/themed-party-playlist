# import os
# gpt (text generation)
# bayessian analysis (style of what people say based on words they say)
# pybayes

# import lyricsgenius

import synoynm as syn

from flask import render_template
# from simSearch import getUseableWords

# genius_token = os.getenv('GENIUS_TOKEN')

# if genius_token is None:
# 	import config
# 	genius_token = config.GENIUS_TOKEN

# genius = lyricsgenius.Genius(genius_token)  # access token

# --------
# def analyze(sp, genius, theme, topic_dictionary, method, stopCondition, stopNum):

def analyze(sp, input_info):
	# @app.route('/create-playlist')
	# def playlist_page():
	# 	return render_template('create-playlist.html')
	
	# playlist_page()

	# theme, method, playlistName, stopCondition, stopNum = input_info['theme'], input_info['method'], input_info['playlistName'], input_info['stopCondition'], input_info['stopNum']
	method, playlistName, songLimit = input_info['method'], input_info['playlistName'], input_info['stopCondition']

	# print('topic dictionary:', topic_dictionary) #remove #debug

	'''
	methods = ['playlist', 'top tracks', 'saved tracks']

	print('\n')
	for i, val in enumerate(methods):
		print(f'[{i}] {val}')

	stopConditions = ['duration', 'song count']

	print('\n')
	for i, val in enumerate(stopConditions):
		print(f'[{i}] {val}')

	stopInfo = input(
		"^ Input 1) the index of the condition for stopping the program (duration in minutes) and 2) the number associated with your chosen option (separated by a space) OR press the Enter key to skip: ").split()

	if not len(stopInfo):
		stopCondition = None
		stopNum = None
	else:
		stopCondition = stopConditions[int(stopInfo[0])]
		stopNum = int(stopInfo[1])
	'''
	# songLimit = stopCondition
	# if stopCondition == 'duration':
	# 	songLimit = round(stopNum/4) #avg song length is 3.5, but we'll make it 4 so we have extra data and don't have to  #TODO: maybe calculate avg song length of dataset from user (e.g. in playlist, top songs, etc.)
	# 	# songLimit = round(4*stopNum) #avg song length is 3.5, but we'll make it 4 so we have extra data and don't have to  #TODO: maybe calculate avg song length of dataset from user (e.g. in playlist, top songs, etc.)
	# 	stopNum *= 60000 #convert to ms (minutes is just easier for user)
	# elif stopCondition == 'song count': songLimit = stopNum
	# else: songLimit = None

	playlistOffset = 0
	# -------

	# scope = 'user-library-read playlist-read-private user-top-read playlist-modify-private playlist-modify-public'
	# sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

	sampleTracks = []


	# def getSongs(limit=songLimit, offset=0):
	def getSongs(offset=0):
		songs = []

		limit = 100 #check

		# if limit is None: limit = 100 #check

		if method == 'playlist':
			# playlistName = str(input('\nPlaylist name: '))

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

			# if songLimit is None: #TODO: test for limit > 100
			songOffset = 100

			while len(userData['items']) < userData['total']:
				addData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=songOffset)
				userData['items'].extend(addData['items'])
				songOffset += 100

			for item in userData['items']:
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
		else:
			if method == 'top tracks':
				userData = sp.current_user_top_tracks(limit=limit, offset=offset) #TODO: add option of time range (recent [short_term] vs all-time [long_term], also medium_term but ... that is probably overkill)
				
				# if songLimit is None or len(userData['items']) < limit:
				# if songLimit is None or len(userData['items']) < songLimit:
				it = 0
				time_range = 'short_term'

				stopCount = (150 if songLimit is None else limit)

				while it < 2 and len(userData['items']) < stopCount:
					it += 1
					addData = sp.current_user_top_tracks(limit=limit, time_range=time_range)
					for item in addData['items']:
						if item not in userData['items']: userData['items'].append(item)
					# userData['items'].extend(addData['items'])

					time_range = 'long_term'
				
				if len(userData['items']) < limit: print(f'only able to access {len(userData["items"])} top songs.')

				for item in userData['items']:
					song = {
						'name': item['name'],
						'artists': [artist['name'] for artist in item['artists']],
						'duration': item['duration_ms'],
						'release_date': item['album']['release_date'],
						'id': item['id'],
						'album_art': item['album']['images'][0]['url']
					}
					songs.append(song)
			elif method == 'saved tracks':
				userData = sp.current_user_saved_tracks(limit=(limit if limit < 50 else 50), offset=offset)

				# if songLimit is None or limit > 50:
				# if songLimit is None or songLimit > 50:

				songOffset = 50

				# stopCount = (userData['total'] if songLimit is None else limit)
				stopCount = userData['total']

				while len(userData['items']) < stopCount:
					addData = sp.current_user_saved_tracks(limit=50, offset=songOffset)
					userData['items'].extend(addData['items'])
					songOffset += 50

				for item in userData['items']:
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
		
		return songs


	sampleTracks = getSongs(offset=playlistOffset)

	return sampleTracks

	

#--- MAIN FUNCTION ---
def parseLyrics(genius, input_info, topic_dictionary, songs):
	'''
	Retreives lyrics from genius & goes through them to see if they match the provided theme

	Parameters:
	----------
		* songs (list): contains dicts with song info (returned from `getSongs` func)
	'''
	# info = { 'duration': 0, 'song count': 0 }
	playlistSongs = []
	# subSongs = []
	description = []
	albumArt = []
	
	stopCondition, stopNum, info = input_info['stopCondition'], input_info['stopNum'], input_info['info']

	def reachedLimit():
		'''
		function to check whether the playlist is at the max length (aka met stop condition)
		'''
		if stopNum is None or abs(stopNum-info[stopCondition]) >= 60000 or info[stopCondition] <= stopNum: return False
		else: return True #break if within 1 minute of stopNum or exceeded stopNum
		# if abs(stopNum-info[stopCondition]) < 60000 or info[stopCondition] > stopNum: return False #break if within 1 minute of stopNum or exceeded stopNum
		# else: return True


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

	subSongs = []

	for song in songs:
		songName = song['name']
		primaryArtist = song['artists'][0]
		songLyrics = getSongLyrics(title=songName, artist=primaryArtist)

		print('song:', songName)

		if songLyrics is not None:
			lyricMatches = syn.multi_topic_scorer(songLyrics, topic_dictionary, sim_thresh=0.8, return_hits=True) #TODO: find good sim_thresh
			# lyricMatches = syn.multi_topic_scorer(songLyrics, topic_dictionary, sim_thresh=0.75, return_hits=True) #TODO: find good sim_thresh
			# keywords = lyricMatches[theme][1]
			
			matches_theme = False

			top_sim = 0

			# print('lyricMatches:', lyricMatches) #remove #debug
			for match in lyricMatches.values():
				if match[0] > 0:
					keywords = match[1]
					print(f"Adding {songName} by {primaryArtist} to playlist because it passes the similarity threshold with a score of {match[0]} and contains the keywords: {keywords}\n")
					matches_theme = True
					break

			# if lyricMatches[theme][0] > 0:
			if matches_theme:
				# print(f"Adding {songName} by {primaryArtist} to playlist because it contains the keywords: {keywords}\n")

				if (len(subSongs) == 100):
					playlistSongs.append(subSongs)
					subSongs = []

				subSongs.append(song['id'])

				albumArt.append(song['album_art'])
				# playlistSongs.append(song['id'])
				description.append(f"{songName}: {keywords}")

				info['song count'] += 1
				info['duration'] += song['duration']
			else: print(f"SKIPPING: {songName} by {primaryArtist} does not match.")

			if reachedLimit(): break


	if len(subSongs) and (not len(playlistSongs) or playlistSongs[-1] != subSongs): playlistSongs.append(subSongs)

	return playlistSongs, albumArt, description


# parseLyrics(sampleTracks)

# while not reachedLimit(): #keep collecting and then parsing songs until we reach the limit indicated by user
# 	sampleTracks = getSongs(offset=playlistOffset)

# 	print(len(sampleTracks))
# 	parseLyrics(sampleTracks)
# 	playlistOffset += songLimit #TODO: make sure this starts *after* last song


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
