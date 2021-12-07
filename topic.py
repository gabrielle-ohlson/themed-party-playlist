from top2vec import Top2Vec

# import tensorflow as tf

# print(tf.test.is_gpu_available())

# print(tf.config.list_physical_devices('GPU'))

# from tensorflow.python.client import device_lib
# print(device_lib.list_local_devices())

import warnings

import gc

gc.collect()
#TODO: try using tensorflow-gpu ?

def handle_warning(w):
	warnings.warn(f'warning: {w}', UserWarning)

def top_lyrics(songs, terms, stopNum=None, stopCondition=None, relevant_lyrics=[]):


	# import os
	# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

	# tf.config.
	# tf.config.threading.set_intra_op_parallelism_threads(2)
	# tf.config.threading.set_inter_op_parallelism_threads(2)
	# tf.config.gpu_options
	print('relevant_lyrics:', len(relevant_lyrics))
	print('songs:', len(songs))
	song_names = [song['name'] for song in songs]
	lyrics = [song['lyrics'] for song in songs]

	lyrics_ct = len(lyrics)
	
	relevant_lyrics_ct = len(relevant_lyrics)

	if relevant_lyrics_ct:
		relevant_song_lyrics = [song['lyrics'] for song in relevant_lyrics]
		lyrics.extend(relevant_song_lyrics)

	print('stopNum:', stopNum)
	if stopNum is not None: print(stopNum/60000, 'mins')
	# while True:
	# 	try:
		# from requests.exceptions import Timeout
	# resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

	# with warnings.catch_warnings() as w:
	# 	print('!!!', w)

	# warnings.filterwarnings("error")
	gc.collect()

	retries = 0
	# with warnings.catch_warnings() as w:
	# 	warnings.simplefilter("error")
	# 	handle_warning(w)

	while retries < 3:
		print('trying...')
		try:
			# model = Top2Vec(lyrics, min_count=1, embedding_model='universal-sentence-encoder', workers=5)
			model = Top2Vec(lyrics, min_count=1, embedding_model='universal-sentence-encoder')
			print(f'successful! (after {retries} retries)')
			break
		# catch
		# except RuntimeError: #RuntimeWarning
		# except tf.errors.ResourceExhaustedError as e:
		except MemoryError as e:
		# except RuntimeWarning as e:
		# except w:
			print('some exception occured.', e)
			if len(lyrics) - 100 >= lyrics_ct: lyrics = lyrics[:-100]
			# else: lyrics = lyrics[:lyrics_ct]
			# except Timeout as e:
			retries += 1
			continue
		# 268435456
		# 34133760

	# model = Top2Vec(lyrics, min_count=1, embedding_model='universal-sentence-encoder', workers=5)

	print(len(model.documents), lyrics_ct) #remove #debug

	# model.add_documents(lyrics)
	# model.save('static/models/saved_model.pb') #saved_model.pbtxt

	training_ids = [doc_id for doc_id in model.document_ids if doc_id >= lyrics_ct]

	print(model.document_ids) #remove #debug
	print(training_ids) #remove #debug

	if len(training_ids): model.delete_documents(training_ids)

	print(len(model.documents)) #remove #debug

	print(model.document_ids) #remove #debug

	num_docs = len(model.documents)
	if stopNum is None: stopNum = num_docs #TODO: have option of passing length (so if stopNum[0] (type) == 'duration', multiple by 5 [so extra], then, go backwards )

	if stopCondition == 'duration': num_docs = min(num_docs, stopNum//120000) # 120000 = 2 minutes (average song length == 3.5 mins aka 210000 ms, so get a few extra songs incase they are short)
	# num_docs = stopNum//210000
	# stopNum=((input_info['stopNum']//210000) if input_info['stopCondition'] == 'duration' else input_info['stopNum']

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


def similarity(lyrics, terms, thresh=0.8):
	lyrics = lyrics.split('\n')
	terms = [term.lower() for term in terms]

	# model = Top2Vec(lyrics, min_count=1, embedding_model='distiluse-base-multilingual-cased') #TODO: remove pip installations in requirements that are associated with this
	model = Top2Vec(lyrics, min_count=1, embedding_model='universal-sentence-encoder') #TODO: remove pip installations in requirements that are associated with this


	model.get_num_topics()

	vocab = model.vocab

	valid_terms = []
	for term in terms:
		print(term, term in vocab)
		if term in vocab and term not in valid_terms: valid_terms.append(term)

	print('valid terms:', valid_terms) #remove #debug

	if not len(valid_terms): return None, None

	# topic_sizes, topic_nums = model.get_topic_sizes()

	# topic_count = len(topic_sizes)
	# print(len(topic_sizes), topic_nums)

	# topic_words, word_scores, topic_nums = model.get_topics(topic_count)

	# print('\n', topic_words, word_scores, topic_nums)

	topic_words, word_scores, topic_scores, topic_nums = model.search_topics(keywords=valid_terms, num_topics=len(valid_terms)) #*


	print(topic_scores)

	for idx, t in enumerate(valid_terms):
		print(t, topic_scores[idx])

	# print('\n', topic_words, word_scores, topic_scores, topic_nums)

	# for topic in topic_nums:
	# 	model.generate_topic_wordcloud(topic)

	words, word_scores = model.similar_words(keywords=valid_terms, num_words=3) #*

	avg_sim = sum(word_scores) / len(word_scores)

	print('avg word score for top 3:', sum(word_scores) / len(word_scores))
	for word, score in zip(words, word_scores):
		print(f"{word} {score}")
	
	if avg_sim >= thresh: return avg_sim, words
	else: return None, None

	# words, word_scores = model.similar_words(keywords=valid_terms, num_words=20) #*
	# for word, score in zip(words, word_scores):
	# 	print(f"{word} {score}")


# Successfully installed cycler-0.11.0 cython-0.29.24 fonttools-4.28.3 gensim-3.8.3 hdbscan-0.8.27 kiwisolver-1.3.2 llvmlite-0.37.0 matplotlib-3.5.0 numba-0.54.1 pynndescent-0.5.5 setuptools-scm-6.3.2 tomli-1.2.2 top2vec-1.0.26 umap-learn-0.5.2 wordcloud-1.8.1
# numpy==1.20.0




# Installing collected packages: protobuf, tensorflow-hub, libclang, tensorflow-estimator, google-pasta, astunparse, opt-einsum, oauthlib, requests-oauthlib, pyasn1, rsa, pyasn1-modules, cachetools, google-auth, google-auth-oauthlib, tensorboard-data-server, absl-py, tensorboard-plugin-wit, grpcio, zipp, importlib-metadata, markdown, tensorboard, termcolor, wrapt, keras, keras-preprocessing, flatbuffers, h5py, tensorflow-io-gcs-filesystem, gast, tensorflow, tensorflow-text

# Successfully installed absl-py-1.0.0 astunparse-1.6.3 cachetools-4.2.4 flatbuffers-2.0 gast-0.4.0 google-auth-2.3.3 google-auth-oauthlib-0.4.6 google-pasta-0.2.0 grpcio-1.42.0 h5py-3.6.0 importlib-metadata-4.8.2 keras-2.7.0 keras-preprocessing-1.1.2 libclang-12.0.0 markdown-3.3.6 oauthlib-3.1.1 opt-einsum-3.3.0 protobuf-3.19.1 pyasn1-0.4.8 pyasn1-modules-0.2.8 requests-oauthlib-1.3.0 rsa-4.8 tensorboard-2.7.0 tensorboard-data-server-0.6.1 tensorboard-plugin-wit-1.8.0 tensorflow-2.7.0 tensorflow-estimator-2.7.0 tensorflow-hub-0.12.0 tensorflow-io-gcs-filesystem-0.22.0 tensorflow-text-2.7.3 termcolor-1.1.0 wrapt-1.13.3 zipp-3.6.0