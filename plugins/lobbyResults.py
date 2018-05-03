def botLog(text):
    """
    logs a string. Adds bot name, and forces a flush
    """
    try:
        print("LobbyResult: " +  str(text), flush = True)
    except:
        print("LobbyResult: Logging error. Probably some retard name", flush = True)


##processes the CSODOTA protobuf and returns a python dict of the data
def processMatch(msg):
    
    ##init
    match = {}

    ##shared attributes
    match["game_mode"] = msg.game_mode
    match["state"] = msg.state
    match["leader_id"] = msg.leader_id
    match["lobby_type"] = msg.lobby_type
    match["allow_cheats"] = msg.allow_cheats
    match["fill_with_bots"] = msg.fill_with_bots
    match["intro_mode"] = msg.intro_mode
    match["game_name"] = msg.game_name
    match["server_region"] = msg.server_region
    match["cm_pick"] = msg.cm_pick
    match["allow_spectating"] = msg.allow_spectating
    match["bot_difficulty_radiant"] = msg.bot_difficulty_radiant
    match["game_version"] = msg.game_version
    match["pass_key"] = msg.pass_key
    match["leagueid"] = msg.leagueid
    match["penalty_level_radiant"] = msg.penalty_level_radiant
    match["penalty_level_dire"] = msg.penalty_level_dire
    match["series_type"] = msg.series_type
    match["radiant_series_wins"] = msg.radiant_series_wins
    match["dire_series_wins"] = msg.dire_series_wins
    match["allchat"] = msg.allchat
    match["dota_tv_delay"] = msg.dota_tv_delay
    match["lan"] = msg.lan
    match["lan_host_ping_to_server_region"] = msg.lan_host_ping_to_server_region
    match["visibility"] = msg.visibility
    match["league_series_id"] = msg.league_series_id
    match["league_game_id"] = msg.league_game_id
    match["previous_match_override"] = msg.previous_match_override
    match["pause_setting"] = msg.pause_setting
    match["bot_difficulty_dire"] = msg.bot_difficulty_dire
    match["bot_radiant"] = msg.bot_radiant
    match["bot_dire"] = msg.bot_dire
    match["selection_priority_rules"] = msg.selection_priority_rules

    botLog(msg.state)

    ##completed match only fields
    if(msg.state == "POSTGAME"):

        
        match["connect"] = msg.connect
        match["server_id"] = msg.server_id
        match["game_state"] = msg.game_state
        match["match_id"] = msg.match_id
        match["first_blood_happened"] = msg.first_blood_happened
        match["match_outcome"] = msg.match_outcome
        match["game_start_time"] = msg.game_start_time

        ##teams

        ##radiant team
        match["radiant"] = {}
        match["radiant"]["team_name"] = msg.team_details[0].team_name
        match["radiant"]["team_tag"] = msg.team_details[0].team_tag
        match["radiant"]["team_id"] = msg.team_details[0].team_id
        match["radiant"]["team_logo"] = msg.team_details[0].team_logo
        match["radiant"]["team_base_logo"] = msg.team_details[0].team_base_logo
        match["radiant"]["team_banner_logo"] = msg.team_details[0].team_banner_logo
        match["radiant"]["team_complete"] = msg.team_details[0].team_complete
        match["radiant"]["rank"] = msg.team_details[0].rank

        ##dire team
        match["dire"] = {}
        match["dire"]["team_name"] = msg.team_details[1].team_name
        match["dire"]["team_tag"] = msg.team_details[1].team_tag
        match["dire"]["team_id"] = msg.team_details[1].team_id
        match["dire"]["team_logo"] = msg.team_details[1].team_logo
        match["dire"]["team_base_logo"] = msg.team_details[1].team_base_logo
        match["dire"]["team_banner_logo"] = msg.team_details[1].team_banner_logo
        match["dire"]["team_complete"] = msg.team_details[1].team_complete
        match["dire"]["rank"] = msg.team_details[1].rank

    ##players
    match["members"] = []

    for member in msg.members:
        new_member = {}
        new_member["id"] = member.id
        new_member["hero_id"] = member.hero_id
        new_member["team"] = member.team
        new_member["name"] = member.name
        new_member["slot"] = member.slot
        new_member["meta_level"] = member.meta_level
        new_member["meta_xp"] = member.meta_xp
        new_member["meta_xp_awarded"] = member.meta_xp_awarded
        new_member["leaver_status"] = member.leaver_status
        new_member["channel"] = member.channel
        new_member["partner_account_type"] = member.partner_account_type
        new_member["coach_team"] = member.coach_team
        new_member["cameraman"] = member.cameraman
        new_member["favorite_team_packed"] = member.favorite_team_packed
        new_member["is_plus_subscriber"] = member.is_plus_subscriber

        match["members"].append(new_member)

    return(match)



def addOptVal(match, msg, field):
    pass