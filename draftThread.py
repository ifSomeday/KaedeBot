from __future__ import print_function
import httplib2
import os

from gevent import monkey
monkey.patch_ssl()

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import time
import classes


SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = os.getcwd() + '\\dataStores\\google_api.json'
APPLICATION_NAME = 'KaedeBot Draft Plugin'
SPREADSHEET_ID = '1Ue1P6i4U4-1M4l-e9aX5gjNNm0dOZWNqzbVNpuZfNEg'
RANGE_FOR_PICKS = 'ADMIN DRAFT SHEET!B3:H'
RANGE_FOR_AMMR = 'ADMIN DRAFT SHEET!M4:N15'


def get_credentials():
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def main(kstQ, dscQ, draftEvent):
    print("here")
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl)


    last_pick = float('-inf')
    while(True):
        if(draftEvent.is_set()):
            values = get_sheet_data(service, SPREADSHEET_ID, RANGE_FOR_PICKS)
            for i in range(0, len(values)):
                row = values[i]
                if len(row) == 7:
                    if(i > last_pick):
                        command = classes.command(classes.discordCommands.BROADCAST_DRAFT_PICK, [row])
                        mmr_list = get_sheet_data(service, SPREADSHEET_ID, RANGE_FOR_AMMR)
                        for mmr in mmr_list:
                            if row[4] == mmr[0]:
                                command.args[0].append(mmr[1])
                        dscQ.put(command)
                        last_pick = i
                else:
                    break
            time.sleep(7)
        else:
            draftEvent.wait()

def get_sheet_data(service, spreadsheetId, rangeName):
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheetId, range= rangeName).execute()
    values = result.get('values',[])
    return(values)

if __name__ == '__main__':
    main()
