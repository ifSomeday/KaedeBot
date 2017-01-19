import requests
import calendar, random, time, pickle, os

class BSJText:
    def __init__(self):
        self.placeHolders = ["HERO", "MONTH", "PERC", "DEGREE", "B-WORD", "S-WORD", "J-WORD"]
        self.responses = ["BSJ has never won on HERO in MONTH", "BSJ has a PERC% winrate on HERO", "BSJ has a PHD in DEGREE from Cal Poly", "BSJ stands for B-WORD S-WORD J-WORD", "BSJ's least favorite hero is HERO", "BSJ's favorite hero is HERO", "BSJ is currently streaming!", "BSJ has a PERC% winrate on HERO when against HERO", ":BSJSmooth:"]
        self.heroArray = self._getHeroList()
        self.monthArray = calendar.month_name
        self.degreeArray = self._getDegreeArray()
        self.bList, self.sList, self.jList = self._getWordList()
        self.placeDict = {"HERO" : self.getRandHero, "MONTH" : self.getRandMonth, "PERC" : self.getPerc, "DEGREE" : self.getRandDegree, "B-WORD" : self.getRandBWord, "S-WORD" : self.getRandSWord, "J-WORD" : self.getRandJWord}

    def _getHeroList(self):
        heroJSON = requests.get("https://raw.githubusercontent.com/kronusme/dota2-api/master/data/heroes.json").json()
        heroArray = []
        for hero in heroJSON["heroes"]:
            heroArray.append(hero["localized_name"])
        return(heroArray)

    def getPerc(self):
        return(round(random.random()*100, 2))

    def _getDegreeArray(self):
        degreeArray = []
        try:
            with open(os.cwd() + "/degrees.txt", "r") as f:
                for line in f:
                    degreeArray.append(line.strip())
        except:
            degreeArray.append("feeding")
        return(degreeArray)

    ##need to filedummp for speed
    def _getWordList(self):
        bList = []
        sList = []
        jList = []
        try:
            with open(os.cwd() + "/bList.dat" , "rb") as f:
                bList = pickle.load(f)
            with open(os.cwd() + "/sList.dat" , "rb") as f:
                sList = pickle.load(f)
            with open(os.cwd() + "/jList.dat", "rb") as f:
                jList = pickle.load(f)
        except:
            allwordlist = requests.get("http://www.mieliestronk.com/corncob_lowercase.txt").text.split()
            bList.clear()
            sList.clear()
            jList.clear()
            for word in allwordlist:
                if word.startswith("b"):
                    bList.append(word)
                if word.startswith("s"):
                    sList.append(word)
                if word.startswith("j"):
                    jList.append(word)

            with open("bList.dat", "wb") as f:
                pickle.dump(bList, f)
            with open("/home/pi/Discord_Bot/sList.dat", "wb") as f:
                pickle.dump(sList, f)
            with open("/home/pi/Discord_Bot/jList.dat", "wb") as f:
                pickle.dump(jList, f)
        return(bList, sList, jList)

    def getRandHero(self):
        return(random.choice(self.heroArray))

    def getRandMonth(self):
        return(random.choice(self.monthArray))

    def getRandDegree(self):
        return(random.choice(self.degreeArray))

    def getRandBWord(self):
        return(random.choice(self.bList).title())

    def getRandSWord(self):
        return(random.choice(self.sList).title())

    def getRandJWord(self):
        return(random.choice(self.jList).title())


    def getFact(self):
        s = random.choice(self.responses)
        for placeholder in list(self.placeDict.keys()):
            while placeholder in s:
                s = str.replace(s, placeholder, str(self.placeDict[placeholder]()), 1)
        return(s)


    def bsjName(self):
        s = self.responses[3]
        for placeholder in list(self.placeDict.keys()):
            while placeholder in s:
                s = str.replace(s, placeholder, str(self.placeDict[placeholder]()), 1)
        return(s)
