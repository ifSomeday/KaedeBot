from enum import Enum
import operator, os, pickle, datetime, math

##     ## ######## ########   #######     ##    ##    ###    ##     ## ########
##     ## ##       ##     ## ##     ##    ###   ##   ## ##   ###   ### ##
##     ## ##       ##     ## ##     ##    ####  ##  ##   ##  #### #### ##
######### ######   ########  ##     ##    ## ## ## ##     ## ## ### ## ######
##     ## ##       ##   ##   ##     ##    ##  #### ######### ##     ## ##
##     ## ##       ##    ##  ##     ##    ##   ### ##     ## ##     ## ##
##     ## ######## ##     ##  #######     ##    ## ##     ## ##     ## ########

def get_hero_name(hero_id, hero_list):
    for hero in hero_list['heroes']:
        if(str(hero_id) == str(hero['id'])):
            return(hero['localized_name'])

########  ##          ###    ##    ## ######## ########
##     ## ##         ## ##    ##  ##  ##       ##     ##
##     ## ##        ##   ##    ####   ##       ##     ##
########  ##       ##     ##    ##    ######   ########
##        ##       #########    ##    ##       ##   ##
##        ##       ##     ##    ##    ##       ##    ##
##        ######## ##     ##    ##    ######## ##     ##

class player:

    def __init__(self, op= None):
        self.steamID = 0
        self.playerName = ""
        self.TeamId = 0
        self.hero_dict = {}
        if(op):
            self.steamID = op.steamID
            self.playerName = op.playerName
            self.TeamId = op.TeamId

    def hero_row_form(self):
        row = [self.playerName]
        sorted_heroes = sorted(self.hero_dict.items(), key=operator.itemgetter(1), reverse=True)
        for i in range(0,5):
            if(i < len(sorted_heroes)):
                row.append(sorted_heroes[i][0])
            else:
                row.append("")
        return(row)

    def add_hero(self, hero_name):
        if(hero_name in self.hero_dict):
            self.hero_dict[hero_name] += 1
        else:
            self.hero_dict[hero_name] = 1

    def __str__(self):
        return(self.playerName + ":" + (self.steamID) + " ")

    def __repr__(self):
        return(self.playerName + ":" + str(self.steamID) + " ")

######## ########    ###    ##     ##
   ##    ##         ## ##   ###   ###
   ##    ##        ##   ##  #### ####
   ##    ######   ##     ## ## ### ##
   ##    ##       ######### ##     ##
   ##    ##       ##     ## ##     ##
   ##    ######## ##     ## ##     ##

class team:

    def __combine_dicts(self, dict1, dict2):
        return({x: dict1.get(x, 0) + dict2.get(x, 0) for x in set(dict1).union(dict2)})

    def calculate_hero_array(self):
        self.hero_dict = {}
        for player in self.players:
                self.hero_dict = self.__combine_dicts(player.hero_dict, self.hero_dict)

    def __init__(self, ot=None):
        self.players = []
        self.captain = None
        self.name = ""
        self.teamId = 0
        self.last_match = 0
        self.hero_dict = {}
        if(ot):
            for p in ot.players:
                self.players.append(player(p))
            self.captain = player(ot.captain)
            self.name = ot.name
            self.teamId = ot.teamId

    def __str__(self):
        return(self.name + ": " + str(self.players) + "\n")

    def __repr__(self):
        return(self.name + ": " + str(self.players) + "\n")

 ######  ##     ## ######## ######## ########    ##     ##    ###    ########  ######  ##     ##
##    ## ##     ## ##       ##          ##       ###   ###   ## ##      ##    ##    ## ##     ##
##       ##     ## ##       ##          ##       #### ####  ##   ##     ##    ##       ##     ##
 ######  ######### ######   ######      ##       ## ### ## ##     ##    ##    ##       #########
      ## ##     ## ##       ##          ##       ##     ## #########    ##    ##       ##     ##
##    ## ##     ## ##       ##          ##       ##     ## ##     ##    ##    ##    ## ##     ##
 ######  ##     ## ######## ########    ##       ##     ## ##     ##    ##     ######  ##     ##

class sheet_match:

    match_id = 0
    won = False
    side = "Radiant"
    mode = 0
    opponent = "n/a"
    heroes_played = []

    def __init__(self, match = None, side = None, team_ids = None, hero_list = None):
        if(match and team_ids and hero_list):
            self.match_id = match['match_id']
            self.won = (match['radiant_win'] == side)
            self.side = "Radiant" if side else "Dire"
            ##TODO: translate this
            self.mode = match['lobby_type']
            self.opponent = "n/a"
            self.heroes_played = []
            for player in match['players']:
                if str(player['account_id']) in team_ids:
                    if player['player_slot'] in (range(0,5) if side else range(128,133)):
                        self.heroes_played.append(get_hero_name(player['hero_id'], hero_list))
            while(len(self.heroes_played) < 5):
                self.heroes_played.append('')

    def row_form(self):
        row = [self.match_id, self.won, self.side, self.mode, self.opponent]
        for hero in self.heroes_played:
            row.append(hero)
        row.append("https://www.dotabuff.com/matches/" + str(self.match_id))
        return(row)

##       ########    ###     ######   ##     ## ########    ########  ##          ###    ##    ## ######## ########
##       ##         ## ##   ##    ##  ##     ## ##          ##     ## ##         ## ##    ##  ##  ##       ##     ##
##       ##        ##   ##  ##        ##     ## ##          ##     ## ##        ##   ##    ####   ##       ##     ##
##       ######   ##     ## ##   #### ##     ## ######      ########  ##       ##     ##    ##    ######   ########
##       ##       ######### ##    ##  ##     ## ##          ##        ##       #########    ##    ##       ##   ##
##       ##       ##     ## ##    ##  ##     ## ##          ##        ##       ##     ##    ##    ##       ##    ##
######## ######## ##     ##  ######    #######  ########    ##        ######## ##     ##    ##    ######## ##     ##

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

########  ########     ###    ######## ######## ########  ##          ###    ##    ## ######## ########
##     ## ##     ##   ## ##   ##          ##    ##     ## ##         ## ##    ##  ##  ##       ##     ##
##     ## ##     ##  ##   ##  ##          ##    ##     ## ##        ##   ##    ####   ##       ##     ##
##     ## ########  ##     ## ######      ##    ########  ##       ##     ##    ##    ######   ########
##     ## ##   ##   ######### ##          ##    ##        ##       #########    ##    ##       ##   ##
##     ## ##    ##  ##     ## ##          ##    ##        ##       ##     ##    ##    ##       ##    ##
########  ##     ## ##     ## ##          ##    ##        ######## ##     ##    ##    ######## ##     ##

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

 ######  ##     ## ########
##    ## ###   ### ##     ##
##       #### #### ##     ##
##       ## ### ## ##     ##
##       ##     ## ##     ##
##    ## ##     ## ##     ##
 ######  ##     ## ########

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

########  ####  ######   ######   #######  ########  ########      ######  ########  ######
##     ##  ##  ##    ## ##    ## ##     ## ##     ## ##     ##    ##    ## ##       ##    ##
##     ##  ##  ##       ##       ##     ## ##     ## ##     ##    ##       ##       ##
##     ##  ##   ######  ##       ##     ## ########  ##     ##    ##       ######   ##   ####
##     ##  ##        ## ##       ##     ## ##   ##   ##     ##    ##       ##       ##    ##
##     ##  ##  ##    ## ##    ## ##     ## ##    ##  ##     ##    ##    ## ##       ##    ##
########  ####  ######   ######   #######  ##     ## ########      ######  ##        ######

class discordConfigHelper:

    ##channel lists
    config_dict = {}

    valid_permission_types = ["meme", "imagemacro", "deletion", "chatresponse", "floodcontrol", "draft", "opendota"]

    ##dict path
    dict_path = os.getcwd() + "/dataStores/discordConfig.pickle"

    def __init__(self):
        self.loadDict()
        self.updateDict()

    def loadDict(self):
        if(os.path.exists(self.dict_path) and os.path.getsize(self.dict_path) > 0):
            with open(self.dict_path, 'rb') as f:
                self.config_dict = pickle.load(f)
        else:
            self.saveDict()

    def updateDict(self):
        for permission in self.valid_permission_types:
            if(not permission + "Channel" in self.config_dict):
                self.config_dict[permission + "Channel"] = []
            if(not permission + "Server" in self.config_dict):
                self.config_dict[permission + "Server"] = []

    def saveDict(self):
        with open(self.dict_path, 'wb') as f:
            pickle.dump(self.config_dict, f)

    def getElements(self, key):
        return(self.config_dict[key])

    def addElement(self, key, entry):
        if(not entry in self.config_dict[key]):
            self.config_dict[key].append(entry)

    def delElement(self, key, entry):
        while(entry in self.config_dict[key]):
            self.config_dict[key].remove(entry)

    def addAll(self, message, channel):
        t = "Server"
        obj = message.server.id
        if(channel):
            t = "Channel"
            obj = message.channel.id
        for key in self.config_dict.keys():
            if(t in key):
                self.addElement(key, obj)

    def removeAll(self, message, channel):
        t = "Server"
        obj = message.server.id
        if(channel):
            t = "Channel"
            obj = message.channel.id
        for key in self.config_dict.keys():
            if(t in key):
                self.delElement(key, obj)

    def check(self, key, channel, server):
        if(channel in self.config_dict[key + "Channel"] or server in self.config_dict[key + "Server"]):
            return(True)
        return(False)

    def checkAny(self, message):
        for permission in self.config_dict.keys():
            if("Channel" in permission):
                if(message.channel.id in self.config_dict[permission]):
                    return(True)
            ##if("Server" in permission):
            ##    if(message.server.id in self.config_dict[permission]):
            ##        return(True)
        return(False)

    def checkMessage(self, key, message):
        return(self.check(key, message.channel.id, message.server.id))




########   #######  ########    #### ##    ## ########  #######
##     ## ##     ##    ##        ##  ###   ## ##       ##     ##
##     ## ##     ##    ##        ##  ####  ## ##       ##     ##
########  ##     ##    ##        ##  ## ## ## ######   ##     ##
##     ## ##     ##    ##        ##  ##  #### ##       ##     ##
##     ## ##     ##    ##        ##  ##   ### ##       ##     ##
########   #######     ##       #### ##    ## ##        #######

class steamBotInfo:

    def __init__(self, name, username, password, steamLink, requester='', teams=[]):
        self.name = name
        self.username = username
        self.password = password
        self.steamLink = steamLink
        self.in_use = False
        self.requester = requester
        self.teams = teams



class league:

    def __init__(self, ids, league_name, channel_id, num_teams=0, last_match = 0, short_results = False, roundup_only = False, best_of = 2, team_ids=[]):
        
        ##Parameters
        self.league_ids = ids
        self.league_name = league_name
        self.channel_id = channel_id
        self.num_teams = num_teams
        self.set_last_matches(last_match)
        self.short_results = short_results
        self.roundup_only = roundup_only
        self.best_of = best_of
        self.team_ids = team_ids

        ##internal data storage
        self.results = []
        self.awaiting_processing = []
        self.awaiting_opendota = []

        ##Estimated results (based on num_teams and best_of)
        self.set_est_results()


    def set_est_results(self):
        self.est_results = math.ceil(((self.num_teams if self.num_teams % 2 == 0 else self.num_teams - 1) / 2) * self.best_of)

    def set_last_matches(self, last_match):
        for league_id in self.league_ids:
            self.last_matches = [last_match for x in self.league_ids]

    ##here winner refers to the index of the winner in the ids array
    ##names array must be same order as the names array
    def add_result(self, ids, names, winner):
        found_match = False
        for result in self.results:
            if(result.get_right_series(ids[0], ids[1])):
                found_match = True
                result.add_match(ids[0], ids[1], 1 + winner)
                break
        if(not found_match):
            self.results.append(league_series(ids[0], names[0], ids[1], names[1], winner = (1 + winner)))

    def get_week_done(self):
        if(not self.num_teams == 0 and len(self.results) >= self.est_results and not len(self.results) == 0):
            return(True)
        return(False)

    def output_results(self):
        out_str = ""
        for result in self.results:
            out_str += result.get_series_results() + "\n"
        return(out_str)

    def new_week(self):
        self.results = []
        self.awaiting_processing = []
        self.awaiting_opendota = []

class league_series:

    def __init__(self, team1_id, team1_name, team2_id, team2_name, winner = -1):
        self.team1_id = team1_id
        self.team1_name = team1_name
        self.team2_id = team2_id
        self.team2_name = team2_name
        self.score = [0, 0]
        self.done = False
        if(not winner == -1 and winner in range(1, 3)):
            self.score[winner - 1] += 1

    def add_match(self, team1_id, team2_id, winner):
        if(not winner in range(1, 3)):
            print("Unable to record series results due to invalid winner", flush=True)
            return
        if(self.team1_id == team1_id and self.team2_id == team2_id):
            self.score[winner - 1] += 1
        elif(self.team1_id == team2_id and self.team2_id == team1_id):
            self.score[winner % 2] += 1
        else:
            print("Unable to record series results due to invalid team ids", flush=True)

        total_games = sum(self.score)
        if(total_games > 2):
            self.done = True

    def get_right_series(self, team1id, team2id):
        if((team1id == self.team1_id and team2id == self.team2_id) or (team2id == self.team1_id and team1id == self.team2_id)):
            print("Found a matching series: " + str(self.team1_id) + " " + str(self.team2_id))
            return(True)
        return(False)

    def get_series_results(self):
        return("*{}*  **{} - {}**  *{}*".format(self.team1_name, self.score[0], self.score[1], self.team2_name))


 ######  ######## ########    ###    ##     ##     ######  ##     ## ########   ######
##    ##    ##    ##         ## ##   ###   ###    ##    ## ###   ### ##     ## ##    ##
##          ##    ##        ##   ##  #### ####    ##       #### #### ##     ## ##
 ######     ##    ######   ##     ## ## ### ##    ##       ## ### ## ##     ##  ######
      ##    ##    ##       ######### ##     ##    ##       ##     ## ##     ##       ##
##    ##    ##    ##       ##     ## ##     ##    ##    ## ##     ## ##     ## ##    ##
 ######     ##    ######## ##     ## ##     ##     ######  ##     ## ########   ######

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
    FREE_BOT = 15
    REQUEST_LOBBY_BOT = 16
    REQUEST_LOBBY_BOT_FLAME = 17
    SHUTDOWN_BOT = 18
    REQUEST_SHUTDOWN = 19 ##TODO: implement this

########  ####  ######   ######   #######  ########  ########      ######  ##     ## ########   ######
##     ##  ##  ##    ## ##    ## ##     ## ##     ## ##     ##    ##    ## ###   ### ##     ## ##    ##
##     ##  ##  ##       ##       ##     ## ##     ## ##     ##    ##       #### #### ##     ## ##
##     ##  ##   ######  ##       ##     ## ########  ##     ##    ##       ## ### ## ##     ##  ######
##     ##  ##        ## ##       ##     ## ##   ##   ##     ##    ##       ##     ## ##     ##       ##
##     ##  ##  ##    ## ##    ## ##     ## ##    ##  ##     ##    ##    ## ##     ## ##     ## ##    ##
########  ####  ######   ######   #######  ##     ## ########      ######  ##     ## ########   ######

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
    BROADCAST_MATCH_RESULT = 22
    ADD_CHANNEL_PERMISSION = 23
    REMOVE_CHANNEL_PERMISSION = 24
    ADD_SERVER_PERMISSION = 25
    REMOVE_SERVER_PERMISISON = 26
    PERMISSION_STATUS = 27
    PERMISSION_HELP = 28
    CREATE_LOBBY = 29
    FREE_BOT_LIST = 30
    BOT_LIST_RET = 31
    TEST_COMMAND = 32
    SEAL_EMBEDS = 33
    HONORARY_CHAMPS = 34
    OPENDOTA = 35
    LOBBY_CREATE_MESSAGE = 36
    NO_BOTS_AVAILABLE = 37
    REQUEST_SHUTDOWN = 38
    SHUTDOWN_BOT = 39
    EGIFT = 40
    OUTPUT_LEAGUE_RESULTS = 41
    LEAGUE_NEW_WEEK = 42
    OMEGA_W = 43
    DECODE = 44
    YURU_YURI_FULL = 45
    ADD_NEW_LEAGUE = 46
    MODIFY_LEAGUE = 47
    SHADOW_COUNCIL_UNBAN_ALL = 48
    ADD_ROLE = 49
    ROLE_HELP = 50
    DUMP_ROLES = 51
    CHECK_VERIFIER = 52
    REMOVE_ROLE = 53

##        #######  ########  ########  ##    ##     ######  ##     ## ########   ######
##       ##     ## ##     ## ##     ##  ##  ##     ##    ## ###   ### ##     ## ##    ##
##       ##     ## ##     ## ##     ##   ####      ##       #### #### ##     ## ##
##       ##     ## ########  ########     ##       ##       ## ### ## ##     ##  ######
##       ##     ## ##     ## ##     ##    ##       ##       ##     ## ##     ##       ##
##       ##     ## ##     ## ##     ##    ##       ##    ## ##     ## ##     ## ##    ##
########  #######  ########  ########     ##        ######  ##     ## ########   ######

class lobbyCommands(Enum):
    INVALID_COMMAND = 0
    BROADCAST = 1

##       ########    ###     ######   ##     ## ########     ######  ##     ## ########   ######
##       ##         ## ##   ##    ##  ##     ## ##          ##    ## ###   ### ##     ## ##    ##
##       ##        ##   ##  ##        ##     ## ##          ##       #### #### ##     ## ##
##       ######   ##     ## ##   #### ##     ## ######      ##       ## ### ## ##     ##  ######
##       ##       ######### ##    ##  ##     ## ##          ##       ##     ## ##     ##       ##
##       ##       ##     ## ##    ##  ##     ## ##          ##    ## ##     ## ##     ## ##    ##
######## ######## ##     ##  ######    #######  ########     ######  ##     ## ########   ######

class leagueLobbyCommands(Enum):
    SWITCH_SIDE = 0
    FIRST_PICK = 1
    SERVER = 2
    START = 3
    GAME_NAME = 4
    GAME_PASS = 5
    CANCEL_START = 6
    SHUFFLE = 7

########   #######  ######## ########  ######  ########     ######  ##     ## ########   ######
##     ## ##     ##    ##    ##       ##    ##    ##       ##    ## ###   ### ##     ## ##    ##
##     ## ##     ##    ##    ##       ##          ##       ##       #### #### ##     ## ##
########  ##     ##    ##    ######   ##          ##       ##       ## ### ## ##     ##  ######
##     ## ##     ##    ##    ##       ##          ##       ##       ##     ## ##     ##       ##
##     ## ##     ##    ##    ##       ##    ##    ##       ##    ## ##     ## ##     ## ##    ##
########   #######     ##    ##        ######     ##        ######  ##     ## ########   ######

class botFactoryCommands(Enum):
    SPAWN_SLAVE = 0
    FREE_SLAVE = 1
    LIST_BOTS_D = 2
    SHUTDOWN_BOT = 3
    PROCESS_BASIC = 4

################################################################
################################################################
################################################################
################################################################
################################################################

class slaveBotCommands(Enum):
    INVITE_PLAYER = 0
    RELEASE_BOT = 1

######## ########    ###    ##     ##  ######
   ##    ##         ## ##   ###   ### ##    ##
   ##    ##        ##   ##  #### #### ##
   ##    ######   ##     ## ## ### ##  ######
   ##    ##       ######### ##     ##       ##
   ##    ##       ##     ## ##     ## ##    ##
   ##    ######## ##     ## ##     ##  ######

class Teams(Enum):
    DANNY = 0
    TERESA = 1
    BURGEONING =2
    PANDA = 3
    SMACKDICKZ = 4
    MICHAELJJACKSON = 5
    THEMANTIS = 6
    FINITE = 7
    KODOS = 8
    BLAMESOCIABLE = 9
    CRAP = 10
    XAG = 11
    TRUCKWAFFLE = 12
    DREAM = 13
    STAREND = 14
    AR = 15

 ######     ###    ########  ########    ###    #### ##    ##  ######
##    ##   ## ##   ##     ##    ##      ## ##    ##  ###   ## ##    ##
##        ##   ##  ##     ##    ##     ##   ##   ##  ####  ## ##
##       ##     ## ########     ##    ##     ##  ##  ## ## ##  ######
##       ######### ##           ##    #########  ##  ##  ####       ##
##    ## ##     ## ##           ##    ##     ##  ##  ##   ### ##    ##
 ######  ##     ## ##           ##    ##     ## #### ##    ##  ######

##TODO: not be retarded
def Captain_name_to_enum(string):
    if(string == "Danny"):
        return(Teams.DANNY)

    elif(string == "Teresa"):
        return(Teams.TERESA)

    elif(string == "Burgeoning"):
        return(Teams.BURGEONING)

    elif(string == "Panda"):
        return(Teams.PANDA)

    elif(string == "smackdickz"):
        return(Teams.SMACKDICKZ)

    elif(string == "MichaelJJackson"):
        return(Teams.MICHAELJJACKSON)

    elif(string == "TheMantis"):
        return(Teams.THEMANTIS)

    elif(string.strip() == "FiNite"):
        return(Teams.FINITE)

    elif(string == "Kodos"):
        return(Teams.KODOS)

    elif(string == "BlameSociable"):
        return(Teams.BLAMESOCIABLE)

    elif(string == "CRAP"):
        return(Teams.CRAP)

    elif(string == "Xag"):
        return(Teams.XAG)

    elif(string == "Truckwaffle"):
        return(Teams.TRUCKWAFFLE)

    elif(string == "Dream"):
        return(Teams.DREAM)

    elif(string == "StarEnd"):
        return(Teams.STAREND)

    elif(string == "Abyssal.Reality"):
        return(Teams.AR)

    else:
        print("cant translate " + string)


################################################################
################################################################
################################################################
################################################################
################################################################

class requester(Enum):
    DISCORD = 0
    WEB = 1
    UNKNOWN = 2

class gameInfo():

    source = requester.UNKNOWN

    lobbyName = ""
    lobbyPassword = ""
    tournament = 0

    ##one of these will always remain none, based on request type
    discordMessage = None
    jobQueue = None
    commandQueue = None

    ##64 bit steam IDs of players to invite (includes captains)
    players = []

    ##64 bit steam IDs of captains in lobby
    captains = []

    ##url to POST final match data to
    hook = ""

    ##ident
    ident = ""

    ##addition lobby config options
    config = {}

    ##the most recent CSOLobby
    lobby = None

    ##the current active players in the lobby (on radiant/dire)
    currPlayers = []

    ##when the lobby times out, in seconds since epoch
    timeout = 0

    def __init__(self):
        pass
