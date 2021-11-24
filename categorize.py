import torch
import torchtext.vocab as vocab

glove = vocab.GloVe(name='6B', dim=100)

print('Loaded {} words'.format(len(glove.itos)))


def get_word(word):
	return glove.vectors[glove.stoi[word]]


def closest(vec, n=10, words=glove.itos):
	"""
	Find the closest words for a given vector
	"""
	all_dists = [(w, torch.dist(vec, get_word(w))) for w in words]
	
	if type(words) == list: print(all_dists) #new
	# all_dists = [(w, torch.dist(vec, get_word(w))) for w in glove.itos]
	return sorted(all_dists, key=lambda t: t[1])[:n]


def euclideanDist(w1, w2):
	dist = torch.norm(glove[w1] - glove[w2])
	return dist.item()


def cosineSimilarity(*words, threshold=0): #*#*#*
	sim = []
	for w in range(0, len(words)):
		for i in range(w+1, len(words)):
			w1, w2 = words[w], words[i]
			x = glove[w1]
			y = glove[w2]
			sim_tensor = torch.cosine_similarity(x.unsqueeze(0), y.unsqueeze(0))
			cos_sim = sim_tensor[0].item()
			if cos_sim >= threshold:
				sim.append({'words': (w1, w2), 'similarity': sim_tensor[0].item()})
			else: print(f'skipping words {w1} and {w2} because their cosine similarity ({cos_sim}) does not exceed the threshold ({threshold}).')

	return sim


def cosSimPair(w1, w2, threshold=0):
	x = glove[w1]
	y = glove[w2]
	sim_tensor = torch.cosine_similarity(x.unsqueeze(0), y.unsqueeze(0))
	sim = sim_tensor[0].item()
	if sim >= threshold: return sim #else will return None
	# return sim_tensor[0].item()


# def cosineSimilarity(w1, w2): #*#*#*
# 	x = glove[w1]
# 	y = glove[w2]
# 	sim_tensor = torch.cosine_similarity(x.unsqueeze(0), y.unsqueeze(0))
# 	return sim_tensor[0].item()


def print_tuples(tuples):
	for tup in tuples:
		print('(%.4f) %s' % (tup[1], tup[0]))


#test
# print_tuples(closest(get_word('google')))


# In the form w1 : w2 :: w3 : ?
def analogy(w1, w2, w3, n=5, filter_given=True):
	print('\n[%s : %s :: %s : ?]' % (w1, w2, w3))
	
	# w2 - w1 + w3 = w4
	closest_words = closest(get_word(w2) - get_word(w1) + get_word(w3))
	
	# Optionally filter out given words
	if filter_given:
		closest_words = [t for t in closest_words if t[0] not in [w1, w2, w3]]
			
	print_tuples(closest_words[:n])


# def similarity(w1, w2):
# 	def closest(vec, n=10):
# 	"""
# 	Find the closest words for a given vector
# 	"""
# 	all_dists = [(w, torch.dist(vec, get_word(w))) for w in glove.itos]
# 	return sorted(all_dists, key=lambda t: t[1])[:n]
# 	print(get_word(w1) - get_word(w2))

#test
# analogy('king', 'man', 'queen')


# closest(get_word('man'), words=['woman', 'cat'])

# print('euclideanDist:')
# print(euclideanDist('man', 'woman'))
# print(euclideanDist('man', 'cat'))
# print(euclideanDist('man', 'baby'))

# print('cosine:')
# print(cosineSimilarity('man', 'woman'))
# print(cosineSimilarity('man', 'cat'))
# print(cosineSimilarity('man', 'baby'))

# print(cosineSimilarity('clothes', 'hat', 'necklace', 'bag', 'shirt', 'person', threshold=0.5))

# http://anie.me/On-Torchtext/
# https://pytorch.org/tutorials/beginner/text_sentiment_ngrams_tutorial.html