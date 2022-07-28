from nltk import pos_tag
from nltk.stem import WordNetLemmatizer


# Just to make it a bit more readable
NOUN = 'n'
VERB = 'v'
ADJECTIVE = 'a'
ADJECTIVE_SATELLITE = 's'
ADVERB = 'r'

lemmatizer = WordNetLemmatizer()


stopwords = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

punctuation = [',' '.', '!', '?', '(', ')', ':', '"']



def similarity(nlp, sentences, theme, thresh=0.3):
  matches = []
  
  for sent in sentences:
  # for idx, sent in enumerate(sentences):
    # print(f'sentence {idx}/{len(sentences)}')
    sent = ''.join(c for c in sent if c not in ',.?:!/:;()') # 0123456789

    words = sent.split(' ')

    words = [word for word in words if word.strip() and not word.lower() in stopwords]

    if not len(words): continue

    tagged = pos_tag(words)

    lem_words = []

    for word, tag in tagged:
      try:
        lem_words.append(lemmatizer.lemmatize(word, tag[0].lower()))
      except:
        lem_words.append(word)

    sim = nlp.similarity(theme, lem_words)

    matches.extend([(word, sim[i].item()) for i, word in enumerate(words)]) #new # if (word, sim[i].item()) not in matches


  matches.sort(key=lambda x: x[1], reverse=True)

  ct_20p = int(0.2*len(matches))

  top_20p = matches[:ct_20p]

  print('ct_20p top_20\% ({ct_20p} words)', top_20p, '!') #remove #debug

  score = sum([m[1] for m in top_20p])/ct_20p

  matches = list(set(matches))

  return score, matches