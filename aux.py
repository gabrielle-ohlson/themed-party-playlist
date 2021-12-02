import os

from distutils import util

import random
import math

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# -------

print("\n(if nothing pops up, you're a repeat user and good to go)\nFIRST TIME USERS: authorize this program to access your spotify account in the browser window that pops up by clicking 'AGREE', and then, once redirected to edgygrandma.com...")

os.environ['SPOTIPY_CLIENT_ID'] = 'ba535fe733624d7488c8863e31c05ba2'
os.environ['SPOTIPY_CLIENT_SECRET'] = 'd2440fdc18b448e78bb0980df57f0237'
os.environ['SPOTIPY_REDIRECT_URI'] = 'https://www.edgygrandma.com/'

scope = 'user-library-read playlist-read-private playlist-read-collaborative user-top-read playlist-modify-private playlist-modify-public'
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

currentUser = sp.me()
userId = currentUser['id']

# ------
def query_yes_no(question, default=None):
	if default is None:
		prompt = " [y/n] "
	elif default == 'yes':
		prompt = " [Y/n] "
	elif default == 'no':
		prompt = " [y/N] "
	else:
		raise ValueError(f"Unknown setting '{default}' for default.")

	while True:
		try:
			resp = input(question + prompt).strip().lower()
			if default is not None and resp == '':
				return default == 'yes'
			else:
				return util.strtobool(resp)
		except ValueError:
			print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

collabs = int(input('\nHow many playlists? '))

playlist_names = []

for i in range(0, collabs):
	playlist_names.append(str(input(f'\nPlaylist #{i+1} name: ')))


shuffle = query_yes_no('Would you like to shuffle the song selections from each playlist?')

print('shuffle: ', shuffle) #remove #debug


stopConditions = ['duration', 'song count', None]

print('\n')
for i, val in enumerate(stopConditions):
	print(f'[{i}] {val}')

stopInfo = input(
	"^ Enter 1) the index of the condition for stopping the program (duration in minutes) and 2) the number associated with your chosen option (separated by a space): ").split()

stopCondition = stopConditions[int(stopInfo[0])]
if len(stopInfo) > 1: stopNum = int(stopInfo[1])

# stopCondition, stopNum = input(
# 	"^ Enter 1) the index of the condition to for stopping the program (duration in minutes) and 2) the number associated with your chosen option (separated by a space): ").split()

# stopCondition = stopConditions[int(stopCondition)]
# stopNum = int(stopNum)

if stopCondition == 'duration':
	songLimit = round(stopNum/4) #avg song length is 3.5, but we'll make it 4 so we have extra data and don't have to  #TODO: maybe calculate avg song length of dataset from user (e.g. in playlist, top songs, etc.)
	# songLimit = round(4*stopNum) #avg song length is 3.5, but we'll make it 4 so we have extra data and don't have to  #TODO: maybe calculate avg song length of dataset from user (e.g. in playlist, top songs, etc.)
	stopNum *= 60000 #convert to ms (minutes is just easier for user)
elif stopCondition == 'song count': songLimit = stopNum
else: songLimit = None

perUserLimit = (None if songLimit is None else round(songLimit/len(collabs)))

playlistOffset = 0

# ------

"""
return self._get(
            "me/top/tracks", time_range=time_range, limit=limit, offset=offset
        )
"""

def getSongs(limit=songLimit, offset=0):
	playlists = []

	for playlistName in playlist_names:
		print(playlistName) #debug
		playlist = None
		userPlaylists = sp.current_user_playlists(limit=50)
		playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

		playlists_offset = 50

		while len(userPlaylists['items']) == 50 and playlist is None:
			print('checking again...')
			userPlaylists = sp.current_user_playlists(limit=50, offset=playlists_offset)

			playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

			playlists_offset += 50

		if playlist is not None:
			print('found it!')
			playlists.append(playlist)
		else:
			print('playlist not found.')
			continue

	songSets = []
	songs = []

	if limit is None: limit = 100 #check

	playlistsData = []
	maxSongs = None

	for playlist in playlists:
		userData = sp.user_playlist_tracks(playlist_id=playlist['id'], limit=perUserLimit, offset=offset)
		playlistsData.append(userData)

		ct = userData['total']

		if maxSongs is None or ct < maxSongs: maxSongs = ct

	print('maxSongs:', maxSongs) #remove #debug

	if songLimit is None: #TODO: test for limit > 100
		for idx, userData in enumerate(playlistsData):
			songOffset = 100

			while len(userData['items']) < maxSongs:
				addData = sp.user_playlist_tracks(playlist_id=playlists[idx]['id'], limit=(limit), offset=songOffset)

				add = (len(addData['items']) + len(userData['items'])) - maxSongs
				if add > 0: userData['items'].extend(addData['items'][:(add+1)]) #check +1
				else: userData['items'].extend(addData['items'])
				songOffset += 100

		# TODO: remove emojis, etc
		# playlist = next((p for p in userPlaylists['items'] if p['name'] == playlistName), None)

		# if limit == None: limit = playlist['tracks']['total'] #check
		# print(limit, type(limit))

	total_songs = 0
	
	if len(playlistsData) == 1: #just one collaborative playlist
		users = []
		usersData = []
		for item in playlistsData[0]['items']:
			user = item['added_by']['id']
			if user not in users:
				users.append(user)
				usersData.append({'items': []})
			usersData[users.index(user)]['items'].append(item)

		maxSongs = len(min(usersData, key=lambda u: len(u['items'])))

		playlistsData = usersData

	if shuffle:
		for userData in playlistsData:
			random.shuffle(userData['items']) #TODO: check
			# print('now:', userData['items'][0]['added_by']['id'])

	for i in range(0, maxSongs):
		# for idx, userData in enumerate(playlistsData):
		for userData in playlistsData:
			track = userData['items'][i]['track']

			if (len(songs) == 100):
				songSets.append(songs)
				songs = []
			songs.append(track['id'])

			total_songs += 1
					# if (len(songs) < 100): songs.append(track['id'])
					# else:
					# 	songSets.append(songs)
					# 	songs = []
			
	if len(songs) and (not len(songSets) or songSets[-1] != songs): songSets.append(songs)

	print(f'added {total_songs} total songs.') #remove #debug
	
	return songSets

# ------
playlistSongs = getSongs()

# ------
if len(playlistSongs):
	newPlaylistName = str(input('What would you like to name the playlist?: '))
	print(f"\nCreating playlist...")
	createdPlaylist = sp.user_playlist_create(user=userId, name=newPlaylistName)

	for songs in playlistSongs:
		sp.playlist_add_items(playlist_id=createdPlaylist['id'], items=songs)
