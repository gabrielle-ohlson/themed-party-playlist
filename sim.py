def get_similar_words(nlp, lst_words, top=30): #TODO: preprocess and np.unique
	lst_out = []
	for tupla in nlp.most_similar(lst_words, topn=top):
		print(tupla[0]) #remove #debug
		lst_out.append(tupla[0])
	
	print('similar words:', list(set(lst_out))) #remove #debug
	return list(set(lst_out))