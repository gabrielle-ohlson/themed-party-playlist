from top2vec import Top2Vec

import warnings

import gc

gc.collect()
#TODO: try using tensorflow-gpu ?

def handle_warning(w):
	warnings.warn(f'warning: {w}', UserWarning)

def top_lyrics(songs, terms, stopNum=None, stopCondition=None, relevant_lyrics=[]):
	song_names = [song['name'] for song in songs]
	lyrics = [song['lyrics'] for song in songs]

	lyrics_ct = len(lyrics)
	
	leftover_space = max(0, 250-lyrics_ct)

	relevant_lyrics = relevant_lyrics[:leftover_space]

	relevant_lyrics_ct = len(relevant_lyrics)

	print('relevant_lyrics_ct:', relevant_lyrics_ct) #debug
	print('lyrics_ct:', lyrics_ct) #debug

	if relevant_lyrics_ct:
		relevant_song_lyrics = [song['lyrics'] for song in relevant_lyrics]
		lyrics.extend(relevant_song_lyrics)

	if stopNum is not None: print(stopNum/60000, 'mins')
	gc.collect()

	retries = 0

	while retries < 3:
		print('trying...')
		try:
			model = Top2Vec(lyrics, min_count=1, embedding_model='universal-sentence-encoder', use_embedding_model_tokenizer=True)

			print(f'successful! (after {retries} retries)')

			break
		except MemoryError as e:

			print('some exception occured.', e)
			if len(lyrics) - 100 >= lyrics_ct: lyrics = lyrics[:-100]

			retries += 1
			continue

	print(len(model.documents)) #debug

	training_ids = [doc_id for doc_id in model.document_ids if doc_id >= lyrics_ct]

	if len(training_ids): model.delete_documents(training_ids)

	print(len(model.documents)) #debug

	num_docs = len(model.documents)
	if stopNum is None: stopNum = num_docs #TODO: have option of passing length (so if stopNum[0] (type) == 'duration', multiple by 5 [so extra], then, go backwards )

	if stopCondition == 'duration':
		num_docs = min(num_docs, stopNum//120000) # 120000 = 2 minutes (average song length == 3.5 mins aka 210000 ms, so get a few extra songs incase they are short)

	vocab = model.vocab

	valid_terms = []
	for term in terms:
		print(term, term in vocab) #remove #debug
		if term in vocab and term not in valid_terms: valid_terms.append(term)

	print('valid terms:', valid_terms) #remove #debug

	document_scores, document_ids = model.search_documents_by_keywords(keywords=valid_terms, num_docs=num_docs, return_documents=False)

	if relevant_lyrics_ct > 0: document_ids = [doc_id for doc_id in document_ids if doc_id < lyrics_ct]

	matches = []

	total_duration = 0
	for idx, doc_id in enumerate(document_ids):
		score = document_scores[idx]
		if score > 0:
			song = songs[doc_id]
			matches.append(song)
			print(f'song match: {song_names[doc_id]} (with score: {score})')

			if stopCondition == 'duration':
				song_duration = song['duration']
				print(song_duration, type(song_duration)) #remove #debug
				total_duration += song_duration
				if total_duration >= stopNum:
					print(f'breaking with total duration of {total_duration} because stopNum is {stopNum}.') #new #test
					break

	words, word_scores = model.similar_words(keywords=valid_terms, num_words=10) #*

	avg_sim = sum(word_scores) / len(word_scores)

	print('avg word score for top 10:', avg_sim)
	for word, score in zip(words, word_scores):
		print(f"{word} {score}")

	return matches