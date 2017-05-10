class leaguePlayer:

    mmr = 1400
    account_name = "null"
    account_id = -1
    wins = 0
    games = 0

    def new_mmr(self, opp_mmr, won):
        expected = (1/(1 + pow(10,(opp_mmr - self.mmr)/400)))

        k = 16
        if(opp_mmr < 2100):
            k = 32
        elif(opp_mmr < 2400):
            k = 24

        self.mmr = int(self.mmr + k*(won - expected))
        self.games += 1
        self.wins += won

    def printStats(self):
        try:
            print(self.account_name, flush=True)
        except:
            print("cant encode name", flush=True)
        print("\tmmr = " + str(self.mmr), flush=True)
        print("\taccount_id = " + str(self.account_id), flush=True)
        print("\twins = " + str(self.wins), flush=True)
        print("\tgames = " + str(self.games), flush=True)
