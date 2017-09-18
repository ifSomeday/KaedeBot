import requests
from steam import SteamID

class openDotaPlugin:

    BASE_URL = "https://api.opendota.com/api/"

    def __init__(self,):
        pass

    ##MATCH RELATED REQUESTS
    def get_match(self, match_id):
        r = requests.get(self.BASE_URL + "matches/" + str(match_id))
        js = r.json()
        return(js)


    #####  #      #####  #   #  #####  #####  #####
    #   #  #      #   #  #   #  #      #   #  #
    #####  #      #####  #####  ###    ####   #####
    #      #      #   #    #    #      #  #       #
    #      #####  #   #    #    #####  #   #  #####
    def __player_request(self, account_id, url_end, params=None):
        acc = SteamID(str(account_id))
        r = requests.get(str(self.BASE_URL + "players/" + str(acc.as_32) + url_end), params=params)
        js = r.json()
        return(js)

    def get_players(self, account_id):
        return(self.__player_request(account_id, ""))

    def get_players_wl(self, account_id, params = None):
        return(self.__player_request(account_id, "/wl", params=params))

    def get_players_recent_matches(self, account_id):
        return(self.__player_request(account_id, "/recentMatches"))

    def get_players_matches(self, account_id, params = None):
        return(self.__player_request(account_id, "/matches", params=params))

    def get_players_heroes(self, account_id, params = None):
        return(self.__player_request(account_id, "/heroes", params=params))

    def get_players_peers(self, account_id, params = None):
        return(self.__player_request(account_id, "/peers", params=params))

    def get_players_pros(self, account_id, params = None):
        return(self.__player_request(account_id, "/pros", params=params))

    def get_players_totals(self, account_id, params = None):
        return(self.__player_request(account_id, "/totals", params=params))

    def get_players_counts(self, account_id, params = None):
        return(self.__player_request(account_id, "/counts", params=params))

    def get_players_histograms(self, account_id, field, params = None):
        return(self.__player_request(account_id, "/histograms/" + field, params=params))

    def get_players_wardmap(self, account_id, params = None):
        return(self.__player_request(account_id, "/wardmap", params=params))

    def get_players_wordcloud(self, account_id, params = None):
        return(self.__player_request(account_id, "/wordcloud", params=params))

    def get_players_ratings(self, account_id, params = None):
        return(self.__player_request(account_id, "/ratings", params=params))

    def get_players_rankings(self, account_id, params = None):
        return(self.__player_request(account_id, "/rankings", params=params))

    def refresh_player(self, account_id):
        acc = SteamID(int(account_id))
        r = requests.get(str(self.BASE_URL + "players/" + str(acc.as_32) + "/refresh"))
        return(True)

##########################
##########################
##########################

    def get_pro_players(self):
        r = requests.get(self.BASE_URL + "proPlayers")
        js = r.json()
        return(js)


##########################
##########################
##########################

    def get_pro_matches(self, params = None):
        r = requests.get(self.BASE_URL + "proMatches", params=params)
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_public_matches(self, params = None):
        r = requests.get(self.BASE_URL + "publicMatches", params=params)
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_hero_stats(self):
        r = requests.get(self.BASE_URL + "heroStats")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def explorer_search(self, sql_query):
        r = requests.get(self.BASE_URL + "explorer", params = {"sql" : sql_query})
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_metadata(self):
        r = requests.get(self.BASE_URL + "metadata")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_distributions(self):
        r = requests.get(self.BASE_URL + "distributions")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def search_player(self, q, similarity=0.51):
        params = {"q" : q,
            "similarity" : similarity}
        r = requests.get(self.BASE_URL + "search", params = params)
        js = r.json()
        return(js)


##########################
##########################
##########################

    def get_rankings(self, hero_id):
        params = {"hero_id" : hero_id}
        r = requests.get(self.BASE_URL + "rankings")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_benchmarks(self, hero_id):
        params = {"hero_id" : hero_id}
        r = requests.get(self.BASE_URL + "benchmarks")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_status(self):
        r = requests.get(self.BASE_URL + "status")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_health(self):
        r = requests.get(self.BASE_URL + "health")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_benchmarks(self, hero_id):
        params = {"hero_id" : hero_id}
        r = requests.get(self.BASE_URL + "benchmarks")
        js = r.json()
        return(js)

##########################
##########################
##########################

    def get_heroes(self):
        r = requests.get(self.BASE_URL + "heroes")
        js = r.json()
        return(js)
