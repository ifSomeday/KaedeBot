import os
    import pickle

    TABLE_NAME = os.getcwd() + "\\ratings.pickle"

    def lload():
        if os.path.getsize(TABLE_NAME) > 0:
            with open(TABLE_NAME,'rb') as f:
                return(pickle.load(f))

    f = lload()
    print("---------------------------------------------------")
    print(f)

    for(key in f):
