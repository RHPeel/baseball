import json
from tabulate import tabulate
from bs4 import BeautifulSoup
import statsapi
import copy
import re
import pytz
from datetime import datetime, timedelta

#input today's date here.'
gameDate = '07/30/2024'
myTimeZone = 'eastern'
metsMode = 0

#grab the standings data from the API.
standingsData = statsapi.standings_data(date=gameDate)

def get_next_day(date_str):
    # Parse the input date string to a datetime object
    date_obj = datetime.strptime(date_str, "%m/%d/%Y")

    # Add one day to the date
    next_day_obj = date_obj + timedelta(days=1)

    # Convert the new date back to a string in the format MM/DD/YYYY
    next_day_str = next_day_obj.strftime("%m/%d/%Y")

    return next_day_str

def convert_dt_to_timezone(myDT,timezone):
    zulu_time = datetime.strptime(myDT, "%Y-%m-%dT%H:%M:%SZ")
    myTZ = pytz.timezone('US/Eastern')
    if timezone == 'central':
        myTZ = pytz.timezone('US/Central')
    elif timezone == 'pacific':
        myTZ = pytz.timezone('US/Pacific')
    elif timezone == 'mountain':
        myTZ = pytz.timezone('US/Mountain')
    zulu_time_utc = pytz.utc.localize(zulu_time)
    timeString = zulu_time_utc.astimezone(myTZ).strftime("%I:%M %p")
    if str(timeString[0]) == '0':
        return str(timeString[1:])
    else:
        return str(timeString)

def write_schedule(mySchedule):
    myScheduleTable = []
    myGameList = ["Time", "Game", "Venue", "Road Probable Pitcher", "Home Probable Pitcher"]
    myScheduleTable.append(myGameList)
    for item in mySchedule:
        myGameList = []
        myGameList.append(convert_dt_to_timezone(item['game_datetime'],myTimeZone))
        myGameList.append(item['away_name'] + ' at ' + item['home_name'])
        myGameList.append(item['venue_name'])
        if item['away_probable_pitcher'] == '':
            myGameList.append('TBD')
        else:
            myGameList.append(item['away_probable_pitcher'])
        if item['home_probable_pitcher'] == '':
            myGameList.append('TBD')
        else:
            myGameList.append(item['home_probable_pitcher'])
        myScheduleTable.append(myGameList)
    return tabulate(myScheduleTable, tablefmt='html', headers="firstrow")

#This function combines two HTML files. We'll use this to build out the list of boxscores.'
def merge_html(html_base, new_html):
    # Parse both input HTML strings
    soup1 = BeautifulSoup(html_base, 'html.parser')
    soup2 = BeautifulSoup(new_html, 'html.parser')

    # Create a new BeautifulSoup object with a basic HTML structure
    new_soup = BeautifulSoup('<html><head></head><body></body></html>', 'html.parser')

    # Handle the <head> section, using the <head> from soup1
    if soup1.head:
        new_soup.head.replace_with(soup1.head)

    # Extract <body> contents from both soups
    body1 = soup1.body
    body2 = soup2.body

    # Merge the body contents
    if body1:
        new_soup.body.extend(body1.contents)
    if body2:
        new_soup.body.extend(body2.contents)

    # Return the string representation of the merged HTML
    return str(new_soup)

#This dictionary links IDs from the standings API to actual division names.
divisionDict = {200: "AL West",
                201: "AL East",
                202: "AL Central",
                203: "NL West",
                204: "NL East",
                205: "NL Central"}

#We'll store the standings here.'
standingsDict = {}

#This function takes the input from the standings, by division, and makes it into a list-of-lists.
def build_standings_group(a):
    standingsLOL = []
    for item in a:
        standingsRow = []
        standingsRow.append(item['name'])
        standingsRow.append(item['w'])
        standingsRow.append(item['l'])
        #We're calculating winning percentage, leaving off the leading 0. and rounding to 3 digits.
        standingsRow.append(str(f"{item['w'] / (item['w'] + item['l']):.3f}")[1:])
        standingsRow.append(item['gb'])
        #Key part here is for later exclusion from the wild card grouping.
        #First place teams are excluded from the wild card grouping.
        if item['div_rank'] != '1':
            standingsRow.append(item['wc_gb'])
        else:
            standingsRow.append("xxxx")
        standingsLOL.append(standingsRow)
    return standingsLOL

#This takes the three divisions as inputs and adds everything to a new "wild card" group.
#But... if we see that "xxxx" we know NOT to include it in the wild card set.
def build_wild_card_group(a,b,c):
    standingsLOL = []
    for item in a:
        #if item[5] != '-':
        if item[5] != "xxxx":
            standingsLOL.append(item)
    for item in b:
        if item[5] != "xxxx":
            standingsLOL.append(item)
    for item in c:
        if item[5] != "xxxx":
            standingsLOL.append(item)
    return standingsLOL

#This is a simple procedure to write the HTML table, but it adds a "special row" class to the headers.
#Special row is just bolded text, but it's all handled via stylesheet.'
def generate_HTML_standings_table(a):
    html = '<table>\n'
    for i in a:
        if (i[0][0:2] == "AL") or (i[0][0:2] == "NL"):
                html += '<tr class="special-row">\n'
        else:
            html += '<tr>'
        for j in i:
            html += f'<td>{j}</td>\n'
        html += '</tr>\n'
    html += '</table>'
    return html

#Very simple utility to merge two lists of lists into a single list-of-lists.
def append_lists_of_lists(list1, list2):
    # Append each sublist in list2 to list1
    for sublist in list2:
        list1.append(sublist)
    return list1

#Sort procedure. We use this to sort by winning percentage.
def sort_list_of_lists(lists, key_index=0, descending=True):
    """
    Sorts a list of lists based on a specified key index.

    Parameters:
    lists (list of lists): The list of lists to be sorted.
    key_index (int): The index of the element in the inner lists to sort by.
    descending (bool): Whether to sort in descending order.

    Returns:
    list of lists: The sorted list of lists.
    """
    return sorted(lists, key=lambda x: x[key_index], reverse=descending)

def remove_extra_gb(a,b):
    newItem = list(a)
    newItem.pop(b)
    return newItem

#We're leaning on the divisionCodes to loop through in building a standings table.'
def build_standings_html_table(myStandings,x):
    standingsLOL = []
    divisionCodes = [201,202,200]
    if x == "NL":
        for division in divisionCodes:
            standingsHeader = build_standings_headers(myStandings,divisionDict[division + 3])
            standingsLOL.append(standingsHeader)
            for item in myStandings[division + 3]:
                standingsLOL.append(remove_extra_gb(item,5))
        standingsHeader = build_standings_headers(myStandings,"NL Wild Card")
        standingsLOL.append(standingsHeader)
        for item in myStandings['nlwc']:
            standingsLOL.append(remove_extra_gb(item,4))
    else:
        for division in divisionCodes:
            standingsHeader = build_standings_headers(myStandings,divisionDict[division])
            standingsLOL.append(standingsHeader)
            for item in myStandings[division]:
                standingsLOL.append(remove_extra_gb(item,5))
        standingsHeader = build_standings_headers(myStandings,"NL Wild Card")
        standingsLOL.append(standingsHeader)
        for item in myStandings['alwc']:
            standingsLOL.append(remove_extra_gb(item,4))
    return standingsLOL

#This builds the headers for each standings group.
def build_standings_headers(a,b):
    a = []
    a.append(b)
    a.append('W')
    a.append('L')
    a.append('WP')
    a.append('GB')
    return a

#We use this class for building out the line score.
#Each inning gets a "start" and "stop" score. The difference between those two goes into the line score.
class Inning:
    def __init__(self):
        self.inningNumber = 0
        self.topRunsStart = 0
        self.topRunsEnd = 0
        self.bottomRunsStart = 0
        self.bottomRunsEnd = 0

#Figure out if the game went to extra innings.
#Note that as of now we assume ALL games go at least 9, even rain-shortened games.
def get_max_inning(a):
    maxInning = 9
    for item in a:
        if item['about']['inning'] > maxInning:
            maxInning = item['about']['inning']
    return maxInning

#Go through each inning and build the line score.
def log_runs(a,b):
    for item in a:
        checkInning = item['about']['inning']
        if item['result']['awayScore'] > b[checkInning].topRunsEnd:
            b[checkInning].topRunsEnd = item['result']['awayScore']
        if item['result']['homeScore'] > b[checkInning].bottomRunsEnd:
            b[checkInning].bottomRunsEnd = item['result']['homeScore']
    return b

#This catches anything that our iterative processe misses.
def clean_table(a):
    keyList = []
    for key in a:
        keyList.append(key)
    for i in range(1,len(keyList)):
        if a[i].topRunsStart > a[i].topRunsEnd:
            a[i].topRunsEnd = a[i].topRunsStart
        if a[i].bottomRunsStart > a[i].bottomRunsEnd:
            a[i].bottomRunsEnd = a[i].bottomRunsStart
        if a[i].topRunsEnd > a[i + 1].topRunsStart:
            a[i + 1].topRunsStart = a[i].topRunsEnd
        if a[i].bottomRunsEnd > a[i + 1].bottomRunsStart:
            a[i + 1].bottomRunsStart = a[i].bottomRunsEnd
        finalInning = i + 1
    if a[finalInning].topRunsStart > a[finalInning].topRunsEnd:
        a[finalInning].topRunsEnd = a[finalInning].topRunsStart
    if a[finalInning].bottomRunsStart > a[finalInning].bottomRunsEnd:
        a[finalInning].bottomRunsEnd = a[finalInning].bottomRunsStart
    if a[9].topRunsEnd < a[9].bottomRunsStart:
        a[9].bottomRunsStart = 'x'
        a[9].bottomRunsEnd = 'x'
    return a

#Actually builds the inning totals.
def make_linescore(a,road_team,home_team):
    linescoreLOL = []
    linescoreList = [""]
    roadList = [road_team]
    homeList = [home_team]
    for key in a:
        linescoreList.append(a[key].inningNumber)
        roadList.append(a[key].topRunsEnd - a[key].topRunsStart)
        if key != 9:
            homeList.append(a[key].bottomRunsEnd - a[key].bottomRunsStart)
        else:
            if a[key].bottomRunsStart == 'x':
                homeList.append('x')
            else:
                homeList.append(a[key].bottomRunsEnd - a[key].bottomRunsStart)

    linescoreLOL.append(linescoreList)
    linescoreLOL.append(roadList)
    linescoreLOL.append(homeList)
    return linescoreLOL

#We need actual totals added.
def add_totals_to_linescore(linescore,a):
    linescore[0].append("R")
    linescore[1].append(a['away']['teamStats']['batting']['runs'])
    linescore[2].append(a['home']['teamStats']['batting']['runs'])
    linescore[0].append("H")
    linescore[1].append(a['away']['teamStats']['batting']['hits'])
    linescore[2].append(a['home']['teamStats']['batting']['hits'])
    linescore[0].append("E")
    linescore[1].append(figure_out_team_errors(a['away']['info']))
    linescore[2].append(figure_out_team_errors(a['home']['info']))
    return linescore

#Need to correct the 9th inning values to make sure they're right-adjusted.
def fix_linescore_html(myLinescoreTable):
    soup = BeautifulSoup(myLinescoreTable, 'html.parser')
    for td in soup.find_all('td'):
        if td.get_text(strip=True).isnumeric() or td.get_text(strip=True) == 'x':
            td['style'] = "text-align: right;"
    for th in soup.find_all('th'):
        if th.get_text(strip=True).isnumeric() or th.get_text(strip=True) == 'x':
            th['style'] = "text-align: right;"
    return str(soup)

def extract_and_clean_parentheses_text(input_string):
    # Find all text within parentheses
    input_string = error_cleanup(input_string)
    pattern = r'\(([^)]*)\)'
    matches = re.findall(pattern, input_string)

    cleaned_matches = []
    for match in matches:
        # Split the text at the first comma and take the second part (if exists)
        parts = match.split(',', 1)
        if len(parts) > 1:
            cleaned_matches.append(parts[1].strip())
        else:
            cleaned_matches.append(parts[0].strip())

    # Join the cleaned matches into a single string
    result = ' '.join(cleaned_matches)
    return result

def error_cleanup(a):
    a = a.replace("catcher interference","CI")
    return a

def figure_out_team_errors(a):
    hasErrors = 0
    i = 0
    for item in a:
        if item['title'] == 'FIELDING':
            for item2 in item['fieldList']:
                if item2['label'] == 'E':
                    errorData = item2['value']
                    hasErrors = 1
    if hasErrors == 0:
        return(0)
    else:
        return(len(extract_and_clean_parentheses_text(errorData).split(" ")))

def merge_html(html_base, new_html):
    # Parse both input HTML strings
    soup1 = BeautifulSoup(html_base, 'html.parser')
    soup2 = BeautifulSoup(new_html, 'html.parser')

    # Create a new BeautifulSoup object with a basic HTML structure
    new_soup = BeautifulSoup('<html><head></head><body></body></html>', 'html.parser')

    # Handle the <head> section, using the <head> from soup1
    if soup1.head:
        new_soup.head.replace_with(soup1.head)

    # Extract <body> contents from both soups
    body1 = soup1.body
    body2 = soup2.body

    # Merge the body contents
    if body1:
        new_soup.body.extend(body1.contents)
    if body2:
        new_soup.body.extend(body2.contents)

    # Return the string representation of the merged HTML
    return str(new_soup)

#Some BeautifulSoup-driven functions to modify our HTML.

#This one adds a row to the bottom of a table that is basically just a text box.
def append_row_with_colspan_to_html_table(html_table, new_row, colspan_index, colspan_value):
    soup = BeautifulSoup(html_table, "html.parser")
    table = soup.find("table")
    new_row_tag = soup.new_tag("tr")
    for i, cell in enumerate(new_row):
        new_cell_tag = soup.new_tag("td")
        if i == colspan_index:
            new_cell_tag['colspan'] = colspan_value
        new_cell_tag.string = str(cell)
        new_row_tag.append(new_cell_tag)
    table.append(new_row_tag)
    return str(soup)

#This one replaces three asterisks in a cell with a special kind of indented cell.
def add_indent_to_asterisk_cells_in_table(html_table):
    """
    Takes an HTML string representing a single table, searches for <td> elements containing '***',
    and adds the 'special-cell' class to those elements.

    Parameters:
    html_table (str): The input HTML string representing a single table.

    Returns:
    str: The modified HTML table as a string.
    """
    # Parse the HTML table string
    soup = BeautifulSoup(html_table, 'html.parser')

    # Find all <td> elements containing '***'
    for td in soup.find_all('td'):
        if '***' in td.get_text(strip=True):
            td['class'] = td.get('class', []) + ['indented-cell']  # Add 'special-cell' class
            td.string.replace_with(td.get_text().replace("***", ""))

    # Return the modified HTML table as a string
    return str(soup)

def create_boxscore_row(myItem,myPositions):
    myRow = []
    if myItem['substitution']:
        nameField = "***" + myItem['namefield']
    else:
        nameField = myItem['namefield']
    newPositions = ''
    if len(myPositions) > 1 and nameField != 'Totals':
        nameFieldList = nameField.split(" ")
        nameFieldList.pop()
        for item in myPositions:
            newPositions = newPositions + item['abbreviation'] + '-'
        nameFieldList.append(newPositions)
        nameField = ''
        #print(nameFieldList)
        for item in nameFieldList:
            nameField = nameField + item + ' '
        nameField = nameField[:-2]
    myRow.append(nameField)
    myRow.append(myItem['ab'])
    myRow.append(myItem['r'])
    myRow.append(myItem['h'])
    myRow.append(myItem['rbi'])
    myRow.append(myItem['bb'])
    myRow.append(myItem['k'])
    myRow.append(myItem['avg'])
    myRow.append(myItem['obp'])
    myRow.append(myItem['slg'])
    return myRow

def create_pitcher_row(myItem):
    myRow = []
    myRow.append(myItem['namefield'])
    myRow.append(myItem['ip'])
    myRow.append(myItem['h'])
    myRow.append(myItem['r'])
    myRow.append(myItem['er'])
    myRow.append(myItem['bb'])
    myRow.append(myItem['k'])
    myRow.append(myItem['hr'])
    myRow.append(myItem['era'])
    return myRow

def build_hitter_list(hitterData,hitterTotals,teamPlayers):
    hitterChart = []
    for item in hitterData:
        positionData = ''
        if item['personId']:
            playerID = 'ID' + str(item['personId'])
            positionData = teamPlayers[playerID]['allPositions']
            #print(positionData)
        hitterRow = create_boxscore_row(item,positionData)
        hitterChart.append(hitterRow)
    hitterRow = create_boxscore_row(hitterTotals,positionData)
    hitterChart.append(hitterRow)
    return tabulate(hitterChart, tablefmt='html', headers="firstrow")

def append_hitter_notes(hitterTable,hitterNotes):
    myHitterNotes = ''
    for item in hitterNotes:
        myHitterNotes = myHitterNotes + hitterNotes[item] + "\n"
    hitterNotesList = []
    hitterNotesList.append(myHitterNotes)
    hitterTable = append_row_with_colspan_to_html_table(hitterTable,hitterNotesList,0,10)
    return hitterTable

def append_other_notes(hitterTable,hitterOtherNotes):
    myOtherNotes = ""
    myOtherNotesList = []
    for item in hitterOtherNotes:
        for item2 in item['fieldList']:
            myOtherNotes = myOtherNotes + item2['label'] + ': ' + item2['value'] + ' '
    myOtherNotesList.append(myOtherNotes)
    hitterTable = append_row_with_colspan_to_html_table(hitterTable,myOtherNotesList,0,10)
    return hitterTable

def build_pitcher_list(pitcherData,pitcherTotals):
    pitchingChart = []
    for item in pitcherData:
        pitcherRow = create_pitcher_row(item)
        pitchingChart.append(pitcherRow)
    pitcherRow = create_pitcher_row(pitcherTotals)
    pitchingChart.append(pitcherRow)
    return tabulate(pitchingChart, tablefmt='html', headers="firstrow")

def add_game_notes(pitcherTable,boxInfo):
    gameNotes = ''
    gameNotesList = []
    for i in range(0,len(boxInfo) - 1):
        gameNotes = gameNotes + boxInfo[i]['label'] + ': ' + boxInfo[i]['value'] + ' '
    gameNotesList.append(gameNotes)
    pitcherTable = append_row_with_colspan_to_html_table(pitcherTable,gameNotesList,0,10)
    return pitcherTable


#Grab all of the games from the selected date and store the gameIDs.
gameDateOutput = gameDate.replace("/","-")
outputFileName = 'box_scores-' + gameDateOutput
yesterdaysGames = statsapi.schedule(date=gameDate, team="", opponent="", sportId=1, game_id=None)
print(yesterdaysGames)
yesterdayGameIDs = []

for keys in divisionDict:
    standingsDict[keys] = build_standings_group(standingsData[keys]['teams'])

wildCardStandings = build_wild_card_group(standingsDict[200],standingsDict[201],standingsDict[202])
wildCardStandings = sort_list_of_lists(wildCardStandings,3)
standingsDict['alwc'] = wildCardStandings
standingsAL = (build_standings_html_table(standingsDict,"AL"))
standingsALHTML = generate_HTML_standings_table(standingsAL)
print("Logging AL Standings")

wildCardStandings = build_wild_card_group(standingsDict[203],standingsDict[204],standingsDict[205])
wildCardStandings = sort_list_of_lists(wildCardStandings,3)
standingsDict['nlwc'] = wildCardStandings
standingsNL = (build_standings_html_table(standingsDict,"NL"))
standingsNLHTML = generate_HTML_standings_table(standingsNL)
print("Logging NL Standings")

nextDay = get_next_day(gameDate)
todaysSchedule = statsapi.schedule(start_date=nextDay,end_date=nextDay)

print("Logging today's games")
todaysScheduleTable = write_schedule(todaysSchedule)

#This is the initial HTML template. Note that it will include our style sheet.
#It also includes the standings tables to start.
boxScoreHTML = f"""
        <html>
        <head>
            <style>
                .table-container {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px; /* Adjust the gap between columns */
                }}
                table {{ border-collapse: collapse;
                        width: 100%}}
                td, th {{ padding-top: 0.1px;
                        padding-bottom: 0.1px;
                        padding-left: 5px;
                        padding-right: 5px;
                        border: 0px solid black;
                        font-size: 9.5px; /* Adjust font size as needed */
                        font-family: 'Arial';
                        word-wrap: break-word;
                    overflow-wrap: break-word; }}
                .nested-table {{
                                width: 100%}}
                .indented-cell {{
                        padding-left: 10px;}}
                .special-row {{
                                  font-weight: bold}}
            </style>
        </head>
        <body>
        <h2>MLB Standings - {get_next_day(gameDate)}</h2>
        <div class="table-container">
        <table>
        <tr><td class="nested-standings-table">{standingsALHTML}</td></tr>
        </table>
        <table>
        <tr><td class="nested-standings-table">{standingsNLHTML}</td></tr>
        </table>
        </div>
        <br>
        <h2>Today's Games</h2>
        {todaysScheduleTable}
        <br>
        </body>
        </html>
        """

for item in yesterdaysGames:
    if metsMode == 1:
        if item['away_name'] == 'New York Mets' or item['home_name'] == 'New York Mets':
            yesterdayGameIDs.append(item['game_id'])
    else:
        yesterdayGameIDs.append(item['game_id'])

#Loop through all of the game_IDs we just added.
for j in range(0,len(yesterdayGameIDs)):
#for j in range(0,2):
    gameID = yesterdayGameIDs[j]
    #gameID = 745807
    #Get the boxscore data and line score.
    data = statsapi.boxscore_data(gameID)
    myLineScore = statsapi.linescore(gameID)
    #print(data)

    #Convert the line score into a text table via tabulate.
    #myLineScoreLOL = parse_text_table(myLineScore)
    #lineScoreTable = tabulate(myLineScoreLOL, tablefmt='html', headers="firstrow")

    #Get team info.
    away_team = data['teamInfo']['away']['shortName']
    home_team = data['teamInfo']['home']['shortName']
    print("Logging " + away_team + " versus " + home_team)

    #All the Road Team Stuff
    roadPlayers = data['away']['players']
    roadBatters = data['awayBatters']
    roadBattingTotals = data['awayBattingTotals']
    roadBattingTable = build_hitter_list(roadBatters,roadBattingTotals,roadPlayers)
    roadBattingTable = append_hitter_notes(roadBattingTable,data['awayBattingNotes'])
    roadBattingTable = add_indent_to_asterisk_cells_in_table(roadBattingTable)
    roadBattingTable = append_other_notes(roadBattingTable,data['away']['info'])
    roadPitchers = data['awayPitchers']
    roadPitchingTotals = data['awayPitchingTotals']
    roadPitcherTable = build_pitcher_list(roadPitchers,roadPitchingTotals)

    #All the Home Team Stuff
    homePlayers = data['home']['players']
    homeBatters = data['homeBatters']
    homeBattingTotals = data['homeBattingTotals']
    homeBattingTable = build_hitter_list(homeBatters,homeBattingTotals,homePlayers)
    homeBattingTable = append_hitter_notes(homeBattingTable,data['homeBattingNotes'])
    homeBattingTable = add_indent_to_asterisk_cells_in_table(homeBattingTable)
    homeBattingTable = append_other_notes(homeBattingTable,data['home']['info'])
    homePitchers = data['homePitchers']
    homePitchingTotals = data['homePitchingTotals']
    homePitcherTable = build_pitcher_list(homePitchers,homePitchingTotals)

    #We have to add the game notes somewhere.
    homePitcherTable = add_game_notes(homePitcherTable,data['gameBoxInfo'])

    #Line Score next.
    gameScoring = statsapi.game_scoring_play_data(gameID)
    myMaxInning = get_max_inning(gameScoring['plays'])

    inningDetails = {}

    for i in range(0,myMaxInning):
        inningDetails[i + 1] = Inning()
        inningDetails[i + 1].inningNumber = i + 1

    inningDetails = log_runs(gameScoring['plays'],inningDetails)
    inningDetails = clean_table(inningDetails)

    myLineScore = make_linescore(inningDetails,away_team,home_team)
    myLineScore = add_totals_to_linescore(myLineScore,data)
    lineScoreTable = tabulate(myLineScore, tablefmt='html', headers="firstrow")
    lineScoreTable = fix_linescore_html(lineScoreTable)

    #We're going to build two at a time, so the first one, we'll store in differently-named tables.
    if j == len(yesterdayGameIDs) - 1 and j % 2 == 0:
        additionalHTML = f"""Mets
        <html>
        <head></head>
        <body>
        <div class="table-container">
        <table>
        <tr><td class="nested-table">{lineScoreTable}</td></tr>
        <tr><td class="nested-table">{roadBattingTable}</td></tr>
        <tr><td class="nested-table">{homeBattingTable}</td></tr>
        <tr><td class="nested-table">{roadPitcherTable}</td></tr>
        <tr><td class="nested-table">{homePitcherTable}</td></tr>
        <tr><td><br></td></tr>
        <tr><td><br></td></tr>
        </table>
        <table>
        <tr><td class="nested-table"></td></tr>
        <tr><td class="nested-table"></td></tr>
        <tr><td class="nested-table"></td></tr>
        <tr><td class="nested-table"></td></tr>
        <tr><td class="nested-table"></td></tr>
        <tr><td><br></td></tr>
        <tr><td><br></td></tr>
        </table>
        </div>
        </body>
        </html>
        """
        boxScoreHTML = merge_html(boxScoreHTML,additionalHTML)

    elif j % 2 == 0:
        lineScoreTable2 = copy.deepcopy(lineScoreTable)
        homeBattingTable2 = copy.deepcopy(homeBattingTable)
        roadBattingTable2 = copy.deepcopy(roadBattingTable)
        roadPitcherTable2 = copy.deepcopy(roadPitcherTable)
        homePitcherTable2 = copy.deepcopy(homePitcherTable)
    else:

    #This is how we're going to build the HTML.
    #There are a few things in here: table-container allows us to do two columns, and the "indented-cell" allows for indentation.
        additionalHTML = f"""
        <html>
        <head></head>
        <body>
        <div class="table-container">
        <table>
        <tr><td class="nested-table">{lineScoreTable2}</td></tr>
        <tr><td class="nested-table">{roadBattingTable2}</td></tr>
        <tr><td class="nested-table">{homeBattingTable2}</td></tr>
        <tr><td class="nested-table">{roadPitcherTable2}</td></tr>
        <tr><td class="nested-table">{homePitcherTable2}</td></tr>
        <tr><td><br></td></tr>
        <tr><td><br></td></tr>
        </table>
        <table>
        <tr><td class="nested-table">{lineScoreTable}</td></tr>
        <tr><td class="nested-table">{roadBattingTable}</td></tr>
        <tr><td class="nested-table">{homeBattingTable}</td></tr>
        <tr><td class="nested-table">{roadPitcherTable}</td></tr>
        <tr><td class="nested-table">{homePitcherTable}</td></tr>
        <tr><td><br></td></tr>
        <tr><td><br></td></tr>
        </table>
        </div>
        </body>
        </html>
        """

        #Some cleanup for the next iteration.
        del lineScoreTable
        del roadBattingTable
        del homeBattingTable
        del roadPitcherTable
        del homePitcherTable
        del lineScoreTable2
        del roadBattingTable2
        del homeBattingTable2
        del roadPitcherTable2
        del homePitcherTable2

        #Write the records to our HTML file.
        boxScoreHTML = merge_html(boxScoreHTML,additionalHTML)

with open(outputFileName + '.html','w') as file:
    file.write(boxScoreHTML)
