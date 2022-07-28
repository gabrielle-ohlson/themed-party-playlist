import vecSim 


def top_lyrics(nlp, songs, terms, stopNum=None, stopCondition=None):
	print('getting top lyrics!!!!!!!!!!!!', len(songs)) #remove

	song_names = [song['name'] for song in songs]
	lyrics = [song['lyrics'] for song in songs]

	matches = []

	for i, lyric in enumerate(lyrics):
		print(song_names[i]) #remove #debug
		sentences = lyric.splitlines()

		avg_sim, top_matches = vecSim.similarity(nlp, sentences, terms)

		print(song_names[i], avg_sim) #remove #debug

		if avg_sim > 0.1:
			songs[i]['keywords'] = top_matches
			matches.append((i, songs[i], avg_sim))

	matches.sort(key=lambda x: x[2], reverse=True)

	if stopNum is not None:
		if stopCondition == 'duration':
			total_duration = 0
			for i, m in enumerate(matches):
				song_duration = songs[m[0]]['duration']
				total_duration += song_duration

				if total_duration > stopNum:
					stopNum = i
					break
		
		matches = matches[:stopNum]

	matches = [m[1] for m in matches]

	return matches