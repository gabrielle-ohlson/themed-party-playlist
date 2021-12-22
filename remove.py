def getPlaylists(sp):
	userPlaylists = []

	playlists_sample = sp.current_user_playlists(limit=50)

	print('type:', type(playlists_sample['items'])) #remove #debug

	if len(playlists_sample['items']): userPlaylists.extend(playlists_sample['items']) #TODO: see type

	playlists_offset = 50

	while len(playlists_sample['items']):
		playlists_sample = sp.current_user_playlists(limit=50, offset=playlists_offset)

		if len(playlists_sample['items']): userPlaylists.extend(playlists_sample['items']) #TODO: see type

		playlists_offset += 50
	
	return userPlaylists


'''
def delete_playlists(sp, playlist_names, playlists):
	for playlistName in playlist_names:
		playlist_occurences = list(filter(lambda p: p['name'] == playlistName, playlists))

		if len(playlist_occurences):
			if len(playlist_occurences) > 1:
				delete_all = query_yes_no(f"Would you like to delete all occurences of playlists by the name of '{playlistName}'?")

				if delete_all:
					for p in playlist_occurences:
						sp.current_user_unfollow_playlist(p['id'])
				else: sp.current_user_unfollow_playlist(playlist_occurences[0]['id'])
		else:
			print(f"no playlists by the name of '{playlistName}' found.")
			continue
'''

# -----
# userPlaylists = getPlaylists()

# delete_playlists(userPlaylists)