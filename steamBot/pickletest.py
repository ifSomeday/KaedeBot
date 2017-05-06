import os
import pickle

TABLE_NAME = os.getcwd() + "\\ratings.pickle"



d = {}
if os.path.getsize(TABLE_NAME) > 0:
    with open(TABLE_NAME,'rb') as f:
        d = pickle.load(f)
print("---------------------------------------------------")

for key, value in d.items():
    value.printStats()
