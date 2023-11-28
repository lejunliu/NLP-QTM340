# -*- coding: utf-8 -*-
"""QTM340 Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1T-MWHtNvV1V0-tW4JBf_HE1fX62WTkXm
"""

import os
import json
import gzip
import pandas as pd
import numpy as np
import sklearn
from tqdm import tqdm

import torch
import nltk
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from gensim.models import Word2Vec
from scipy.stats import percentileofscore

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import roc_auc_score, f1_score,confusion_matrix
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import make_scorer, roc_auc_score

import seaborn as sns
import matplotlib.pyplot as plt

nltk.download('punkt')
nltk.download('stopwords')

"""#### Import the dataset:
Reference: https://colab.research.google.com/drive/1Zv6MARGQcrBbLHyjPVVMZVnRWsRnVMpV#scrollTo=feWoOrmt4Tja
"""

!wget https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/metaFiles2/meta_All_Beauty.json.gz
!wget https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/categoryFiles/All_Beauty.json.gz

# load beauty data
data = []
with gzip.open('All_Beauty.json.gz', 'r') as f:
    for l in tqdm(f):
        data.append(json.loads(l))

df = pd.DataFrame(data)
df.shape

df = df.drop(['reviewerID', 'reviewTime','asin', 'unixReviewTime', 'style', 'image'],axis = 1)

df.dropna(inplace=True)

df.head()

df.shape
df.dtypes

df['vote']= df['vote'].str.replace(',', '').astype(int)
df['vote'].describe()

percentile = percentileofscore(df['vote'], 30, kind='rank')
percentile

df['target'] = np.where(df['vote'] > 30, 1, 0)

df.head()

# remove stopwords and perform tokenization
def preprocess_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))

    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]

    return tokens

df['processed_reviewText'] = df['reviewText'].apply(preprocess_text)

"""### TFIDF with MLP"""

vectorizer = TfidfVectorizer()
vectorizer.fit(df['reviewText'])


feature_names = vectorizer.get_feature_names_out()
idf_values = vectorizer.idf_

word_idf_dict = dict(zip(feature_names, idf_values))

# Sort words by their IDF scores in descending order and select top N words
sorted_words_by_idf = sorted(word_idf_dict.items(), key=lambda x: x[1], reverse=True)
top_n = 5000
top_n_words = [word for word, idf in sorted_words_by_idf[:min(top_n, len(sorted_words_by_idf))]]

# Create a new TF-IDF Vectorizer considering only the top N words
top_n_vectorizer = TfidfVectorizer(vocabulary=top_n_words)

top_n_tfidf_matrix = top_n_vectorizer.fit_transform(df['reviewText'])
feature_vectors = top_n_tfidf_matrix.toarray()

X_train, X_test, y_train, y_test = train_test_split(feature_vectors, df['target'], test_size=0.3)

mlp = MLPClassifier(hidden_layer_sizes=(500,200))
mlp.fit(X_train, y_train)

score = mlp.score(X_test, y_test)

y_pred_proba = mlp.predict_proba(X_test)[:, 1]  # Adjust index if needed
auc_score = roc_auc_score(y_test, y_pred_proba)
y_pred = mlp.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

"""### Word2Vec"""

sentences = df['processed_reviewText'].tolist()
model_w2v = Word2Vec(sentences, vector_size=100, window=5, min_count=1, workers=4)
model_w2v.save("word2vec.model")

def review_to_vec(review, model):
    vecs = [model.wv[word] for word in review if word in model.wv]
    return np.sum(vecs, axis=0) if vecs else np.zeros(model.vector_size)

df['reviewVec'] = df['processed_reviewText'].apply(lambda x: review_to_vec(x, model_w2v))

"""### Word Embedding with SVM"""

from sklearn.svm import SVC

X_train, X_test, y_train, y_test = train_test_split(df['reviewVec'].tolist(), df['target'], test_size=0.3)

svm = SVC(probability=True)
svm.fit(X_train, y_train)


score = svm.score(X_test, y_test)

y_pred_proba = svm.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred_proba)

y_pred = svm.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

"""### Word Embedding with MLP

"""

X_train, X_test, y_train, y_test = train_test_split(df['reviewVec'].tolist(), df['target'])

mlp = MLPClassifier(hidden_layer_sizes=(500,200))
mlp.fit(X_train, y_train)

score = mlp.score(X_test, y_test)

y_pred_proba = mlp.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred_proba)

y_pred = mlp.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
plt.xlabel('Predicted')
plt.ylabel('True')
plt.show()

"""### Aggregate Word Embeddings using TFIDF"""

df.head()

tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(df['reviewText'])

word2idf = {word: idf for word, idf in zip(tfidf_vectorizer.get_feature_names_out(), tfidf_vectorizer.idf_)}

def review_to_vec(review, model):
    weighted_vecs = [model.wv[word] * word2idf.get(word, 1.0) for word in review if word in model.wv]
    return np.mean(weighted_vecs, axis=0) if weighted_vecs else np.zeros(model.vector_size)

df['reviewVec'] = df['processed_reviewText'].apply(lambda x: review_to_vec(x, model_w2v))

def evaluate_model(mlp, X, y):
    # Evaluate the model
    score = mlp.score(X, y)

    y_pred_proba = mlp.predict_proba(X)[:, 1]
    auc_score = roc_auc_score(y, y_pred_proba)

    y_pred = mlp.predict(X)
    f1 = f1_score(y, y_pred)

    cm = confusion_matrix(y, y_pred)

    return score, auc_score, f1, cm

X_temp, X_test, y_temp, y_test = train_test_split(df['reviewVec'].tolist(), df['target'], test_size=0.2, random_state=42)
X_train, X_val, y_train, y_val = train_test_split(X_temp, y_temp, test_size=0.25, random_state=42)

param_grid = {
    'hidden_layer_sizes': [(500,200,100), (1000,500,200), (500,200), (300,100), (100,),(1000,)],
    'activation': ['relu', 'tanh', 'logistic'],
    'solver': ['adam', 'sgd'],
    'alpha': [0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05],
    'learning_rate':['constant', 'invscaling', 'adaptive']
}


mlp = MLPClassifier()
grid_search = GridSearchCV(estimator=mlp, param_grid=param_grid, scoring='roc_auc', cv=5)

# Fit the grid search to the data
grid_search.fit(X_train, y_train)

# Print the best parameters
print("Best Parameters found by GridSearchCV:")
print(grid_search.best_params_)

# Use the best estimator for further predictions
best_mlp = grid_search.best_estimator_


val_score, val_auc_score, val_f1, val_cm = evaluate_model(mlp, X_val, y_val)
print("Validation Set Evaluation:")
print(f"Accuracy: {val_score}")
print(f"AUC Score: {val_auc_score}")
print(f"F1 Score: {val_f1}")
print(f"Confusion Matrix:\n{val_cm}")

# Evaluate on Test Set
test_score, test_auc_score, test_f1, test_cm = evaluate_model(mlp, X_test, y_test)
print("\nTest Set Evaluation:")
print(f"Accuracy: {test_score}")
print(f"AUC Score: {test_auc_score}")
print(f"F1 Score: {test_f1}")
print(f"Confusion Matrix:\n{test_cm}")

"""### Contextual Embedding"""

# Commented out IPython magic to ensure Python compatibility.
# %%bash
# 
# pip install datasets
# pip install transformers
# pip install sentencepiece

### Import Models
# import torch
from transformers import *

tokenizer = AutoTokenizer.from_pretrained('allenai/scibert_scivocab_uncased')
model = AutoModel.from_pretrained('allenai/scibert_scivocab_uncased', output_hidden_states=True)
model.eval()

def corpus2contextualmat_averagedlayers (corpus, last_layers=4):
  """ Take the contextual embedding of any word as the average of the
      embeddings of the word from the last 4 layers.
  """
  embeddings = []

  for i in tqdm(range(0, len(corpus), 32)):
      curr_batch = list(corpus[i:i+32])

      encoded_input = tokenizer(curr_batch,
                                return_tensors='pt',
                                max_length=512,
                                truncation=True,
                                padding=True)

      with torch.no_grad():
          outputs = model(**encoded_input) #  output_hidden_states=True

      hidden_states = outputs.hidden_states[-last_layers:] # Tuple of tf.Tensor (one for the output of the embeddings + one for the output of each layer) of shape (batch_size, sequence_length, hidden_size).

      all_embeddings = torch.stack(hidden_states)
      # print(all_embeddings.ndim)
      # print(all_embeddings.shape)
      # [number of layers, batch size, sequence length, hidden size]
      avg_hidden_states = torch.mean(all_embeddings, dim=0) # take mean accorss the layers

      batch_embeddings = avg_hidden_states[:,0,:]
      embeddings.append(batch_embeddings)

  embeddings = torch.cat(embeddings, dim=0)
  return embeddings

df.head()

# Separate into positive and negative subsets
positive_subset = df[df['target'] == 1]
negative_subset = df[df['target'] == 0]

# Sample 10 positive and 90 negative entries
positive_sample = positive_subset.sample(n=10)
negative_sample = negative_subset.sample(n=90)

# Combine the samples
combined_sample = pd.concat([positive_sample, negative_sample])

# If you want to shuffle the combined sample
sample = combined_sample.sample(frac=1).reset_index(drop=True)

contextual_embedding = corpus2contextualmat_averagedlayers(sample['reviewText'].values)

embeddings_list = [embedding.numpy().tolist() for embedding in contextual_embedding]
sample['contextualEmbedding'] = embeddings_list

X_train, X_test, y_train, y_test = train_test_split(sample['contextualEmbedding'].tolist(), sample['target'], test_size=0.2, random_state=42)

param_grid = {
    'hidden_layer_sizes': [(500,200,100), (1000,500,200), (500,200), (300,100), (200,), (100,)],
    'activation': ['relu', 'tanh', 'logistic'],
    'solver': ['adam', 'sgd'],
    'alpha': [0.0001, 0.001, 0.01],
    'learning_rate':['constant', 'invscaling', 'adaptive']
}


mlp = MLPClassifier()
grid_search = GridSearchCV(estimator=mlp, param_grid=param_grid, scoring='roc_auc', cv=5)

# Fit the grid search to the data
grid_search.fit(X_train, y_train)

# Print the best parameters
print("Best Parameters found by GridSearchCV:")
print(grid_search.best_params_)

# Use the best estimator for further predictions
best_mlp = grid_search.best_estimator_

y_pred_proba = best_mlp.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred_proba)

y_pred = best_mlp.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

y_pred_proba = best_mlp.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred_proba)

y_pred = best_mlp.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

sample.head()

sample.dtypes

import lightgbm as lgb
from sklearn.model_selection import GridSearchCV

param_grid = {
    'num_leaves': [31, 50, 70],
    'learning_rate': [0.01, 0.1, 0.5],
    'n_estimators': [100, 200, 500]
    # 'max_depth': [3, 5, 7],
    # 'boosting_type': ['gbdt', 'dart', 'goss']
}

# Create a LightGBM classifier
lgbm = lgb.LGBMClassifier()

# Set up Grid Search
grid_search = GridSearchCV(estimator=lgbm, param_grid=param_grid, scoring='roc_auc', cv=3)

# Fit the grid search to the data
grid_search.fit(X_train, y_train)

# Print the best parameters
print("Best Parameters found by GridSearchCV:")
print(grid_search.best_params_)

# Use the best estimator for further predictions
best_lgbm = grid_search.best_estimator_

y_pred_proba = best_lgbm.predict_proba(X_test)[:, 1]
auc_score = roc_auc_score(y_test, y_pred_proba)

y_pred = best_lgbm.predict(X_test)
f1 = f1_score(y_test, y_pred)

cm = confusion_matrix(y_test, y_pred)

print(f"AUC Score: {auc_score}")
print(f"F1 Score: {f1}")

