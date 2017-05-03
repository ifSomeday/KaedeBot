##Basic levenshtein distance

def distance(a, b):
    la = len(a) + 1
    lb = len(b) + 1

    tbl = [[0 for i in range(0, lb)] for j in range(0, la)]

    for i in range(0, la):
        tbl[i][0] = i
    for i in range(0, lb):
        tbl[0][i] = i

    for i in range(1, la):
        for j in range(1, lb):
            cost = 1
            if(a[i-1] == b[j-1]):
                cost = 0
            tbl[i][j] = min(tbl[i-1][j] + 1, tbl[i][j-1] + 1, tbl[i-1][j-1] + cost)
    return(tbl[la-1][lb-1])
