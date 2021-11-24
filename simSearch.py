import nltk

# nltk.download('wordnet')

from nltk.corpus import wordnet


from pytrends.request import TrendReq

pytrend = TrendReq()


def nounsOnly(words):
	tagged = nltk.pos_tag(words)

	tagged = list(filter(lambda tup: tup[1].startswith('NN'), tagged))
	return [i[0] for i in tagged]


def matchTag(words, tag):
	if tag == 'NNS': tag = 'NN' #convert to singular so it matches NN *and* NNS (since using `startswith`)
	tagged = nltk.pos_tag(words)

	tagged = list(filter(lambda tup: tup[1].startswith(tag), tagged))
	return [i[0] for i in tagged]


def wordExists(w):
	synset = wordnet.synsets(w)
	# print(f'synset for {w}: {synset}.') #remove #debug

	if len(synset):
		print(f'term "{w}" exists in wordnet corpus.')
		return True
	else:
		print(f'term "{w}" does NOT exist in wordnet corpus.')
		return False
		# related = findRelated(w)
		# print(related)
		# return False

def findRelated(w, topics=False):
	wTag = nltk.pos_tag([w])[0][1]

	print(f'tag for {w}: {wTag}.')

	pytrend.build_payload(kw_list=[w])

	if topics: related = pytrend.related_topics()[w]
	else:
		related = pytrend.related_queries()[w]['top'].to_dict()['query']
		related = list(filter(lambda m: not w in m, related.values()))
	
	print(f'terms related to {w}: {related}.')

	part_of_speech_matches = matchTag(related, wTag)
	print(f'terms matching "{wTag}" tag of {w}: {part_of_speech_matches}.')
	
	return part_of_speech_matches


def getUseableWords(w, addRelated=True):
	# if wordExists(w):
	# 	return [w]
	
	if addRelated or not wordExists(w):
		related = findRelated(w)
		related.append(w) #will be filtered out anyway if doesn't exist

		useable = list(filter(lambda r: wordExists(r), related))

		print(f'useable words related to {w}: {useable}.\n')

		return useable
	else: return [w]


#debug
# getUseableWords('natural disaster')

# getUseableWords('pizza')