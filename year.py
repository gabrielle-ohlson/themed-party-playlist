import os
# from distutils import util

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# -------

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-s", "--split_by_year", action='store_true', help="Whether to split the provided date range up into separate playlists by year.")

parser.add_argument("-p", "--private", action='store_true', help="Whether to make the created playlist private.")


# parser.add_argument("-s", "--split-by-year", default=False, help="Whether to split the provided date range up into separate playlists by year.", type=bool)

args = parser.parse_args()


# -------

print("\n(if nothing pops up, you're a repeat user and good to go)\nFIRST TIME USERS: authorize this program to access your spotify account in the browser window that pops up by clicking 'AGREE', and then, once redirected to edgygrandma.com...")

os.environ['SPOTIPY_CLIENT_ID'] = 'ba535fe733624d7488c8863e31c05ba2'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'd2440fdc18b448e78bb0980df57f0237'
os.environ['SPOTIPY_REDIRECT_URI'] = 'https://www.edgygrandma.com/'

scope = 'user-library-read playlist-read-private user-top-read playlist-modify-private playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

currentUser = sp.me()
userId = currentUser['id']

# ------
# def query_yes_no(question, default=None):
# 	if default is None:
# 		prompt = " [y/n] "
# 	elif default == 'yes':
# 		prompt = " [Y/n] "
# 	elif default == 'no':
# 		prompt = " [y/N] "
# 	else:
# 		raise ValueError(f"Unknown setting '{default}' for default.")

# 	while True:
# 		try:
# 			resp = input(question + prompt).strip().lower()
# 			if default is not None and resp == '':
# 				return default == 'yes'
# 			else:
# 				return util.strtobool(resp)
# 		except ValueError:
# 			print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


# print('e.g. `2000-2010` or `2003`')
print('e.g. `2000 - 2010`, `2003`, or `8-10-2020 - 10-2021`')
years = str(input('\nWhat year range? ')) #TODO: add option of doing full date e.g. 08.07.2020

year_range = list(map(lambda y: list(map(int, y.split('-'))), years.split(' - ')))

# year_range = years.split(' - ')
# year_range = list(map(lambda y: y.split('-'), years.split(' - ')))

# year_range = list(map(lambda d: list(map(int, d)), year_range))

# year_range = list(map(int, year_range))

split_by_year = False

if len(year_range) < 2: year_range.append(year_range[0])
else:
	if args.split_by_year:
		split_by_year = {}
		for y in range(year_range[0][-1], year_range[1][-1]+1):
			split_by_year[y] = []


methods = ['playlist', 'top tracks', 'saved tracks']

print('\n')
for i, val in enumerate(methods):
	print(f'[{i}] {val}')

method = methods[int(
	input("^ Enter the index of the method you'd like to use to find songs: "))]

stopConditions = ['duration', 'song count', None]

print('\n')
for i, val in enumerate(stopConditions):
	print(f'[{i}] {val}')

stopInfo = input(
	"^ Enter 1) the index of the condition to for stopping the program (duration in minutes) and 2) the number associated with your chosen option (separated by a space): ").split()

stopCondition = stopConditions[int(stopInfo[0])]
if len(stopInfo) > 1: stopNum = int(stopInfo[1])

# stopCondition, stopNum = input(
# 	"^ Enter 1) the index of the condition to for stopping the program (duration in minutes) and 2) the number associated with your chosen option (separated by a space): ").split()

# stopCondition = stopConditions[int(stopCondition)]
# stopNum = int(stopNum)

if stopCondition == 'duration':
	songLimit = round(4*stopNum) #avg song length is 3.5, but we'll make it 4 so we have extra data and don't have to  #TODO: maybe calculate avg song length of dataset from user (e.g. in playlist, top songs, etc.)
	stopNum *= 60000 #convert to ms (minutes is just easier for user)
elif stopCondition == 'song count': songLimit = stopNum
else: songLimit = None

playlistOffset = 0

# ------

"""
return self._get(
            "me/top/tracks", time_range=time_range, limit=limit, offset=offset
        )
"""

def releasedInRange(release_date, date_range):
	if release_date[0] < date_range[0][-1]: return False
	if release_date[0] > date_range[1][-1]: return False

	if len(release_date) > 1:
		if (release_date[0] == date_range[0][-1]) and len(date_range[0]) > 1:
			if release_date[1] < date_range[0][0]: return False
			if len(release_date) > 2 and len(date_range[0]) > 2:
				if release_date[-1] < date_range[0][1]: return False
		
		if (release_date[0] == date_range[1][-1]) and len(date_range[1]) > 1:
			if release_date[1] > date_range[1][0]: return False
			if len(release_date) > 2 and len(date_range[1]) > 2:
				if release_date[-1] > date_range[1][1]: return False
		
	return True


def getSongs(limit=songLimit, offset=0):
	songSets = []
	songs = []

	if limit is None: limit = 100 #check

	if method == 'playlist':
		playlistName = str(input('\nPlaylist name: '))

		userPlaylists = sp.current_user_playlists(limit=50)
		playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

		playlists_offset = 50

		while len(userPlaylists['items']) == 50 and playlist is None:
			print('checking again...')
			userPlaylists = sp.current_user_playlists(limit=50, offset=playlists_offset)

			playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

			playlists_offset += 50

		if playlist is not None: print('found it!\n')
		else:
			print('playlist not found.')
			return

		# userPlaylists = sp.current_user_playlists(limit=1000)

		# TODO: remove emojis, etc
		# playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

		# if limit == None: limit = playlist['tracks']['total'] #check
		# print(limit, type(limit))

		userData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=offset)

		if songLimit is None: #TODO: test for limit > 100
			songOffset = 100

			while len(userData['items']) < userData['total']:
				addData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=limit, offset=songOffset)
				userData['items'].extend(addData['items'])
				songOffset += 100
		
		total_songs = 0

		for item in userData['items']:
			track = item['track']
			release_date = list(map(int, track['album']['release_date'].split('-')))
			# release_date = track['album']['release_date'].split('-')
			# release_month, release_day, release_year = list(map(int, release_date))
			# release_month, release_day, release_year = int(release_date[0]), int(release_date[1]), int(release_date[2])
			# release_date = int(track['album']['release_date'].split('-')[0])

			if releasedInRange(release_date, year_range):
			# if release_date >= year_range[0] and release_date <= year_range[1]:
				total_songs += 1
				print(f"adding {track['name']}, released {track['album']['release_date']}.")

				if split_by_year:
					split_by_year[release_date[0]].append(track['id']) #new #check
					# playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)
				if (len(songs) == 100):
					songSets.append(songs)
					songs = []
				songs.append(track['id'])
				# if (len(songs) < 100): songs.append(track['id'])
				# else:
				# 	songSets.append(songs)
				# 	songs = []
		
		if len(songs) and (not len(songSets) or songSets[-1] != songs): songSets.append(songs)

		print(f'found {total_songs} total songs.') #remove #debug
	else:
		if method == 'top tracks':
			userData = sp.current_user_top_tracks(limit=limit, offset=offset) #TODO: add option of time range (recent [short_term] vs all-time [long_term], also medium_term but ... that is probably overkill)

			if songLimit is None or len(userData['items']) < limit:
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
			total_songs = 0

			for track in userData['items']:
				# release_date = int(item['album']['release_date'].split('-')[0]) #beep
				release_date = list(map(int, track['album']['release_date'].split('-')))
				if releasedInRange(release_date, year_range):
				# if release_date >= year_range[0] and release_date <= year_range[1]:
					total_songs += 1
					print(f"adding {track['name']}, released {track['album']['release_date']}.")
					# print(f'adding {track["name"]}, released {"-".join(release_date)}.')
					# print(f'adding {item["name"]}, released in {release_date}.')

					if split_by_year:
						split_by_year[release_date[0]].append(track['id']) #new #check

					if (len(songs) == 100):
						songSets.append(songs)
						songs = []
					songs.append(track['id'])
			
			if len(songs) and (not len(songSets) or songSets[-1] != songs): songSets.append(songs)

			print(f'found {total_songs} total songs.') #remove #debug
		elif method == 'saved tracks':
			userData = sp.current_user_saved_tracks(limit=(limit if limit < 50 else 50), offset=offset)

			if songLimit is None or limit > 50: # if limit is None: limit = 100 #check

				songOffset = 50

				stopCount = (userData['total'] if songLimit is None else limit)

				while len(userData['items']) < stopCount:
					addData = sp.current_user_saved_tracks(limit=50, offset=songOffset)
					userData['items'].extend(addData['items'])
					songOffset += 50

			total_songs = 0

			for item in userData['items']:
				track = item['track']
				# release_date = int(track['album']['release_date'].split('-')[0])
				release_date = list(map(int, track['album']['release_date'].split('-')))
				if releasedInRange(release_date, year_range):
				# if release_date >= year_range[0] and release_date <= year_range[1]:
					total_songs += 1
					print(f"adding {track['name']}, released {track['album']['release_date']}.")
					# print(f'adding {track["name"]}, released {"-".join(release_date)}.')
					# print(f'adding {track["name"]}, released in {release_date}.')
					
					if split_by_year:
						split_by_year[release_date[0]].append(track['id']) #new #check

					if (len(songs) == 100):
						songSets.append(songs)
						songs = []
					songs.append(track['id'])
			
			if len(songs) and (not len(songSets) or songSets[-1] != songs): songSets.append(songs)

			print(f'found {total_songs} total songs.') #remove #debug

	return songSets

# ------
playlistSongs = getSongs()

# ------
if len(playlistSongs):
	if split_by_year:
		empty_years = list(filter(lambda y: not len(split_by_year[y]), split_by_year))
		print('empty years:', empty_years)
		for y in empty_years:
			print(f"WARNING: no songs found for year {y}.")

		for y in split_by_year:
			year_song_count = len(split_by_year[y])
			if year_song_count:
				print(f"\n{year_song_count} songs found for year {y}.")
				createdPlaylist = sp.user_playlist_create(user=userId, name=f'year {y}', public=(not args.private), description=f'Songs from the year {y}.')

				sp.playlist_add_items(playlist_id=createdPlaylist['id'], items=split_by_year[y])
			else: print(f"\nWARNING: no songs found for year {y}.")
	else:
		print(f"\nCreating playlist with songs from {years}...")
		createdPlaylist = sp.user_playlist_create(user=userId, name=f'songs from {years}', public=(not args.private), description=f'Songs from {years}.')

		for songs in playlistSongs:
			sp.playlist_add_items(playlist_id=createdPlaylist['id'], items=songs)
else: print(f'sorry, no songs match the date ({years}).')