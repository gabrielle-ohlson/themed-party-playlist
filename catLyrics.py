import categorize

from pytrends.request import TrendReq

pytrend = TrendReq()

import nltk
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer,PorterStemmer
from nltk.corpus import stopwords
import re
lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer() 

word_tags = nltk.corpus.brown.tagged_words(tagset='universal')


# import nltk

# from nltk.corpus import stopwords
# # nltk.download('stopwords')
# from nltk.tokenize import word_tokenize

# import spacy

# sp = spacy.load('en_core_web_sm')

# all_stopwords = sp.Defaults.stop_words

import argparse
parser = argparse.ArgumentParser()

parser.add_argument("-t", "--theme", help="word that represents the theme to detect. theme contains multiple words, use an underscore ('_') in place of a space.", type=str)
parser.add_argument("-f", "--file", help="lyrics file path", type=str)

parser.add_argument("-s", "--sim_threshold", default=0.5, help="similarity threshold", type=int)

args = parser.parse_args()


def normalize(string):
	return string.lower().replace('_', ' ')


theme = normalize(args.theme)
thresh = args.sim_threshold

def detectSim(w, w2=theme):
	w = normalize(w)
	sim = categorize.cosSimPair(w, w2, thresh)
	# print(f"Similarity of '{w}' to '{theme}': {sim}.")
	return sim


with open(args.file, 'r') as file:
	text = file.read().replace("\'"," ").replace("\n", " ")  # replacing \ and \n from txt file


# words = text.split()
def preprocess(sentence, repeats=False, tokens=True, lem=False, stem=False):
	sentence = str(sentence)
	sentence = sentence.lower()
	sentence = sentence.replace('{html}',"")
	cleanr = re.compile('<.*?>')
	cleantext = re.sub(cleanr, '', sentence)
	rem_url = re.sub(r'http\S+', '',cleantext)
	rem_num = re.sub('[0-9]+', '', rem_url)
	tokenizer = RegexpTokenizer(r'\w+')
	tokens = tokenizer.tokenize(rem_num)  
	filtered_words = [w for w in tokens if len(w) > 2 if not w in stopwords.words('english')]
	
	if stem: filtered_words = [stemmer.stem(w) for w in filtered_words]
	if lem: filtered_words = [lemmatizer.lemmatize(w) for w in filtered_words]

	if not repeats: filtered_words = list(set(filtered_words))

	if tokens: return filtered_words
	else: return " ".join(filtered_words)


excludeTags = ['RB', 'PRP', 'W', 'CC', 'DT', 'EX', 'LS', 'IN', 'MD', 'TO'] #adverbs, pronouns, WH, conjunctions, determiners, existential, list, prepositions, modal-verbs, 'to'

def tagWords(words, exclude=[], returnExcluded=False, asList=False):
	'''
	Tags words by part-of-speech.

	Tags:

		 * Adjectives:
		  * JJ   (adjective)                               "big"
		  * JJR  (adjective, comparative)                  "bigger"
		  * JJS  (adjective, superlative)                  "biggest"
		 * Adverbs:
		  * RB   (adverb)                                  "very, silently, now, completely"
		  * RBR  (adverb, comparative)                     "better"
		  * RBS  (adverb, superlative)                     "best"
		 * Nouns:
		  * NN   (noun, singular)                          "desk"
		  * NNS  (noun, plural)                            "desks"
		  * NNP  (proper noun, singular)                   "Harrison"
		  * NNPS (proper noun, plural)                     "Americans"
		 * Numbers:
		  * CD   (cardinal digit)                          "twenty-four, fourth, 1991, 14:24"
		 * Pronouns:
		  * PRP  (personal pronoun)                        "I, he, she"
		  * PRP$ (possessive pronoun)                      "my, his, hers"
		 * Verbs:
		  * VB   (verb, base form)                         "take"
		  * VBD  (verb, past tense)                        "took"
		  * VBG  (verb, gerund/present participle)         "taking"
		  * VBN  (verb, past participle)                   "taken"
		  * VBP  (verb, sing. present, non-3d)             "take"
		  * VBZ  (verb, 3rd person sing. present)          "takes"
		 * WH Determiners:
		  * WDT  (wh-determiner)                           "which"
		  * WP   (wh-pronoun)                              "who, what"
		  * WP$  (possessive wh-pronoun)                   "whose"
		  * WRB  (wh-abverb)                               "where, when"

		 * CC    (coordinating conjunction)                "and, or, but, if, while, although"
		 * DT    (determiner)                              "the, a, some, most, every, no"
		 * EX    (existential there)                       "there, there's"
		 * FW    (foreign word)                            "dolce, ersatz, esprit, quo, maitre"
		 * LS    (list marker)                             "1)"
		 * IN    (prepositions/subordinating conjunction)  "on, of, at, with, by, into, under"
		 * MD    (modal verb)                              "will, can, would, may, must, should"
		 * PDT   (predeterminer)                           "all the kids"
		 * POS   (possessive ending)                       "parent’s"
		 * RP    (present participle)                      "give up, making, going, playing, working"
     * TO    (the word to)                             "to"
		 * UH    (interjection)                            "ah, bang, ha, whee, hmpf, oops"

	Parameters:
	----------
		 * words          (list):            tokenized list of words to be tagged
		 * exclude        (list, optional):  any tags to exclude 
		 * returnExcluded (bool, optional):  whether or not to also return a list of tuples that were excluded
		 * asList         (bool, optional):  whether or not to format return as list containing only the words (without the tags)

	Returns:
	-------
		 * tagged (list of tuples): list of tuples with (word, tag); just list of words if asList == True
	'''

	tagged = nltk.pos_tag(words)
	if len(exclude):
		tagged_copy = tagged.copy()
		tagged = list(filter(lambda tup: not any(tup[1].startswith(tag) for tag in exclude), tagged))
		if asList: tagged = [i[0] for i in tagged]

		if returnExcluded:
			excluded = list(filter(lambda tup: tup not in tagged, tagged_copy))
			return tagged, excluded
	else:
		if asList: return [i[0] for i in tagged]
		else: return tagged


def nounsOnly(words):
	tagged = nltk.pos_tag(words)
	tagged = list(filter(lambda tup: tup[1].startswith('NN'), tagged))
	return [i[0] for i in tagged]


def matchTag(words, tag): #to do: make it NOT about plurality #*#*#*
	tagged = nltk.pos_tag(words)
	tagged = list(filter(lambda tup: tup[1].startswith(tag), tagged))
	return [i[0] for i in tagged]


def findRelated(w, topics=False):
	wTag = nltk.pos_tag([w])[0][1]

	pytrend.build_payload(kw_list=[w])

	if topics: related = pytrend.related_topics()[w]
	else:
		related = pytrend.related_queries()[w]['top'].to_dict()['query']
		related = list(filter(lambda m: not w in m, related.values()))
	
	return related
	print(related, matchTag(related, wTag))

	# relatedText = nltk.Text(word.lower() for word in related)
	# print(relatedText, relatedText.similar(w))
	# print(related['top'])
	print('\n')

# ---------------------
relatedTerms = findRelated(theme)

words = preprocess(text)

tagged_words, excluded = tagWords(words, excludeTags, True, True)

# words = [i[0] for i in tagged_words]
nouns = nounsOnly(words)

print('\nWords:', words)
print('\nTagged words:', tagged_words)
print('\nExcluded:', excluded)

lem_words = preprocess(text, lem=True)

print('\n', words)
# tokens_without_sw = [word for word in words if not word in stopwords.words()]

# print(tokens_without_sw)

matches = []
matches_sim = {}

related_terms_matches = []
related_matches = []

for word in words:
	sim = detectSim(word)
	if sim and word not in matches:
		matches.append(word)
		matches_sim[word] = sim
	
	for term in relatedTerms: #new #v
		sim = detectSim(word, term)
		if sim:
			if term not in related_terms_matches: related_terms_matches.append(term)
			if word not in related_matches: related_matches.append(word)

matches_sim = dict(sorted(matches_sim.items(), key=lambda t: t[1], reverse=True))

matches.sort(key=lambda m: matches_sim[m], reverse=True)

print(f'\n{len(matches)} matches:')
print(u"=" * 10)
print(matches)

print('\n', matches_sim)

print('\n', related_terms_matches, '!', related_matches)

lem_matches = []

for word in lem_words:
	sim = detectSim(word)
	if sim and word not in lem_matches:
		lem_matches.append(word)

print(f'\n{len(lem_matches)} lemmatized matches:')
print(u"=" * 21)
print(lem_matches)

thresh = 0
print(detectSim('hurricane'))



'''
		 * ADJ (adjective)           e.g.: new, good, high, special, big, local
		 * ADV (adverb)              e.g.: really, already, still, early, now
		 * CNJ (conjunction)         e.g.: and, or, but, if, while, although
		 * DET (determiner)          e.g.: the, a, some, most, every, no
		 * EX  (existential)         e.g.: there, there's
		 * FW  (foreign word)        e.g.: dolce, ersatz, esprit, quo, maitre
		 * MOD (modal verb)          e.g.: will, can, would, may, must, should
		 * N   (noun)                e.g.: year, home, costs, time, education
		 * NP  (proper noun)         e.g.: Alison, Africa, April, Washington
		 * NUM (number)              e.g.: twenty-four, fourth, 1991, 14:24
		 * PRO (pronoun)             e.g.: he, their, her, its, my, I, us
		 * P   (preposition)         e.g.: on, of, at, with, by, into, under
		 * TO  (the word to)         e.g.: to
		 * UH  (interjection)        e.g.: ah, bang, ha, whee, hmpf, oops
		 * V   (verb)                e.g.: is, has, get, do, make, see, run
		 * VD  (past tense)          e.g.: said, took, told, made, asked
		 * VG  (present participle)  e.g.: making, going, playing, working
		 * VN  (past participle)     e.g.: given, taken, begun, sung
		 * WH  (wh determiner)       e.g.: who, which, when, what, where, how


		 * ADP	adposition	on, of, at, with, by, into, under
		 * ADV	adverb	really, already, still, early, now
		 * CONJ	conjunction	and, or, but, if, while, although
		 * DET	determiner, article	the, a, some, most, every, no, which
		 * NOUN	noun	year, home, costs, time, Africa
		 * NUM	numeral	twenty-four, fourth, 1991, 14:24
		 * PRT	particle	at, on, out, over per, that, up, with
		 * PRON	pronoun	he, their, her, its, my, I, us
		 * VERB	verb	is, say, told, given, playing, would
		 * .	punctuation marks	. , ; !
		 * X	other	ersatz, esprit, dunno, gr8, univeristy


		 			* CC (coordinating conjunction) -- and
		 			* CD cardinal digit
		 			* DT determiner
		 			* EX existential there (like: “there is” … think of it like “there exists”)
		 			* FW foreign word
		   		* IN preposition/subordinating conjunction
					* JJ adjective ‘big’
					* JJR adjective, comparative ‘bigger’
					* JJS adjective, superlative ‘biggest’
		 			* LS list marker 1)
		 			* MD modal could, will
					* NN noun, singular ‘desk’
					* NNS noun plural ‘desks’
					* NNP proper noun, singular ‘Harrison’
					* NNPS proper noun, plural ‘Americans’
					* PDT predeterminer ‘all the kids’
					* POS possessive ending parent’s
					* PRP personal pronoun I, he, she
					* PRP$ possessive pronoun my, his, hers
					* RB (adverb) -- very, silently, now, completely
					* RBR adverb, comparative better
					* RBS adverb, superlative best
		 			* RP particle give up
		 			* TO, to go ‘to’ the store.
		 			* UH interjection, errrrrrrrm
					* VB verb, base form take
					* VBD verb, past tense took
					* VBG verb, gerund/present participle taking
					* VBN verb, past participle taken
					* VBP verb, sing. present, non-3d take
					* VBZ verb, 3rd person sing. present takes
		 * WDT wh-determiner which
		 * WP wh-pronoun who, what
		 * WP$ possessive wh-pronoun whose
		 * WRB wh-abverb where, when

		 * ADJ (adjective)           e.g.: new, good, high, special, big, local
		 * ADV (adverb)              e.g.: really, already, still, early, now
		 * CNJ (conjunction)         e.g.: and, or, but, if, while, although
		 * DET (determiner)          e.g.: the, a, some, most, every, no
		 * EX  (existential)         e.g.: there, there's
		 * FW  (foreign word)        e.g.: dolce, ersatz, esprit, quo, maitre
		 * MOD (modal verb)          e.g.: will, can, would, may, must, should
		 * N   (noun)                e.g.: year, home, costs, time, education
		 * NP  (proper noun)         e.g.: Alison, Africa, April, Washington
		 * NUM (number)              e.g.: twenty-four, fourth, 1991, 14:24
		 * PRO (pronoun)             e.g.: he, their, her, its, my, I, us
		 * P   (preposition)         e.g.: on, of, at, with, by, into, under
		 * TO  (the word to)         e.g.: to
		 * UH  (interjection)        e.g.: ah, bang, ha, whee, hmpf, oops
		 * V   (verb)                e.g.: is, has, get, do, make, see, run
		 * VD  (past tense)          e.g.: said, took, told, made, asked
		 * VG  (present participle)  e.g.: making, going, playing, working
		 * VN  (past participle)     e.g.: given, taken, begun, sung
		 * WH  (wh determiner)       e.g.: who, which, when, what, where, how
'''