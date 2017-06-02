from enum import Enum

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

class draftPlayer:
    rnd = 0
    pick = 0
    overall = 0
    cpt = ""
    player = ""
    mmr = 0

    def __init__(self, arr=None):
        if(arr):
            self.rnd = arr[1]
            self.pick = arr[2]
            self.overall = arr[0]
            self.captain = arr[4]
            self.player = arr[5]
            self.mmr = arr[6]

    ##TODO: Im retarded
    def isChanged(self, arr):
        if(not self.rnd == arr[1]):
            return(True)
        elif(not self.pick == arr[2]):
            return(True)
        elif(not self.overall == arr[0]):
            return(True)
        elif(not self.captain == arr[4]):
            return(True)
        elif(not self.player == arr[5]):
            return(True)
        elif(not self.mmr == arr[6]):
            return(True)
        else:
            return(False)

    def __str__(self):
        return(str([self.rnd, self.pick, self.overall, self.cpt, self.player, self.mmr]))

    def __repr__(self):
        return(str([self.rnd, self.pick, self.overall, self.cpt, self.player, self.mmr]))

class command:

    command = None
    args = []

    def __init__(self, command, args):
        self.command = command
        self.args = args

    def __str__(self):
        return("command = " + str(self.command) + ", args = " + str(self.args))

    def __repr__(self):
        return("command = " + str(self.command) + ", args = " + str(self.args))

class steamCommands(Enum):
    INVALID_COMMAND = 0
    LEAVE_LOBBY = 1
    LEAVE_TEAM = 2
    LEAVE_PARTY = 3
    STATUS = 4
    LEADERBOARD = 5
    PARTY_INVITE = 6
    LOBBY_INVITE = 7
    LAUNCH_LOBBY = 8
    STOP_BOT = 9
    INHOUSE = 10
    STATUS_4D = 11
    LEADERBOARD_4D = 12
    LOBBY_CREATE = 13
    TOURNAMENT_LOBBY_CREATE = 14

class discordCommands(Enum):
    INVALID_COMMAND = 0
    BROADCAST = 1
    SEND_MEME = 2
    NEW_MEME = 3
    PURGE_MEMES = 4
    HELP = 5
    BSJ_MEME = 6
    BSJ_NAME = 7
    TWITTER = 8
    GET_STEAM_STATUS = 9
    GET_STEAM_LEADERBOARD = 10
    THUMBSUP = 11
    AIRGUITAR = 12
    CHEERLEADER = 13
    CHOCOLATE = 14
    TOMATO = 15
    TRANSFORM = 16
    BROADCAST_LOBBY = 17
    SEND_OLD_MEME = 18
    BROADCAST_DRAFT_PICK = 19
    UPDATE_DRAFT_PICK = 20
    TOGGLE_DRAFT_MODE = 21

class lobbyCommands(Enum):
    INVALID_COMMAND = 0
    BROADCAST = 1
