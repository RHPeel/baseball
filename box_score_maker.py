import json
from tabulate import tabulate
from bs4 import BeautifulSoup
import statsapi
import copy
import re

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

            </style>
        </head>
        <body>
        </body>
        </html>
        """
class Inning:
    def __init__(self):
        self.inningNumber = 0
        self.topRunsStart = 0
        self.topRunsEnd = 0
        self.bottomRunsStart = 0
        self.bottomRunsEnd = 0

def get_max_inning(a):
    maxInning = 9
    for item in a:
        if item['about']['inning'] > maxInning:
            maxInning = item['about']['inning']
    return maxInning

def log_runs(a,b):
    for item in a:
        checkInning = item['about']['inning']
        if item['result']['awayScore'] > b[checkInning].topRunsEnd:
            b[checkInning].topRunsEnd = item['result']['awayScore']
        if item['result']['homeScore'] > b[checkInning].bottomRunsEnd:
            b[checkInning].bottomRunsEnd = item['result']['homeScore']
    return b

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
    return a

def make_linescore(a,road_team,home_team):
    linescoreLOL = []
    linescoreList = [""]
    roadList = [road_team]
    homeList = [home_team]
    for key in a:
        linescoreList.append(a[key].inningNumber)
        roadList.append(a[key].topRunsEnd - a[key].topRunsStart)
        homeList.append(a[key].bottomRunsEnd - a[key].bottomRunsStart)
    linescoreLOL.append(linescoreList)
    linescoreLOL.append(roadList)
    linescoreLOL.append(homeList)
    return linescoreLOL

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

def extract_and_clean_parentheses_text(input_string):
    # Find all text within parentheses
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

def create_boxscore_row(myItem):
    myRow = []
    if myItem['substitution']:
        myRow.append("***" + myItem['namefield'])
    else:
        myRow.append(myItem['namefield'])
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

def build_hitter_list(hitterData,hitterTotals):
    hitterChart = []
    for item in hitterData:
        hitterRow = create_boxscore_row(item)
        hitterChart.append(hitterRow)
    hitterRow = create_boxscore_row(hitterTotals)
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

gameDate = '2024-06-17'
outputFileName = 'box_scores-' + gameDate
yesterdaysGames = statsapi.schedule(date=gameDate, team="", opponent="", sportId=1, game_id=None)
yesterdayGameIDs = []

for item in yesterdaysGames:
    yesterdayGameIDs.append(item['game_id'])

#Loop through all of the game_IDs we just added.
for j in range(0,len(yesterdayGameIDs)):
#for j in range(0,2):
    gameID = yesterdayGameIDs[j]
    #gameID = 745807
    #Get the boxscore data and line score.
    data = statsapi.boxscore_data(gameID)
    myLineScore = statsapi.linescore(gameID)

    #Convert the line score into a text table via tabulate.
    #myLineScoreLOL = parse_text_table(myLineScore)
    #lineScoreTable = tabulate(myLineScoreLOL, tablefmt='html', headers="firstrow")

    #Get team info.
    away_team = data['teamInfo']['away']['shortName']
    home_team = data['teamInfo']['home']['shortName']
    print("Logging " + away_team + " versus " + home_team)

    #All the Road Team Stuff
    roadBatters = data['awayBatters']
    roadBattingTotals = data['awayBattingTotals']
    roadBattingTable = build_hitter_list(roadBatters,roadBattingTotals)
    roadBattingTable = append_hitter_notes(roadBattingTable,data['awayBattingNotes'])
    roadBattingTable = add_indent_to_asterisk_cells_in_table(roadBattingTable)
    roadBattingTable = append_other_notes(roadBattingTable,data['away']['info'])
    roadPitchers = data['awayPitchers']
    roadPitchingTotals = data['awayPitchingTotals']
    roadPitcherTable = build_pitcher_list(roadPitchers,roadPitchingTotals)

    #All the Home Team Stuff
    homeBatters = data['homeBatters']
    homeBattingTotals = data['homeBattingTotals']
    homeBattingTable = build_hitter_list(homeBatters,homeBattingTotals)
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
