import json
from tabulate import tabulate
from bs4 import BeautifulSoup
import statsapi
import copy

def parse_text_table(text_table):
    #We need to make two-word team names into one name for these purposes.
    text_table = text_table.replace('White Sox','WhiteSox')
    text_table = text_table.replace('Red Sox','RedSox')
    text_table = text_table.replace('Blue Jays','BlueJays')
    lines = text_table.strip().split('\n')
    data = [line.split() for line in lines]
    return data

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
    myRow.append(myItem['ops'])
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
yesterdaysGames = statsapi.schedule(date='2024-06-13', team="", opponent="", sportId=1, game_id=None)
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
    myLineScoreLOL = parse_text_table(myLineScore)
    lineScoreTable = tabulate(myLineScoreLOL, tablefmt='html', headers="firstrow")

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

    #We're going to build two at a time, so the first one, we'll store in differently-named tables.
    if j % 2 == 0:
        lineScoreTable2 = copy.deepcopy(lineScoreTable)
        homeBattingTable2 = copy.deepcopy(homeBattingTable)
        roadBattingTable2 = copy.deepcopy(roadBattingTable)
        roadPitcherTable2 = copy.deepcopy(roadPitcherTable)
        homePitcherTable2 = copy.deepcopy(homePitcherTable)
    else:

    #This is how we're going to build the HTML.
    #There are a few things in here: table-container allows us to do two columns, and the "indented-cell" allows for indentation.
        styled_html_table = f"""
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
                td, th {{ padding-top: 1px;
                        padding-bottom: 1px;
                        padding-left: 7px;
                        padding-right: 7px;
                        border: 0px solid black;
                        font-size: 8px; /* Adjust font size as needed */
                        font-family: 'Arial';
                        word-wrap: break-word;
                    overflow-wrap: break-word; }}
                .nested-table {{
                                width: 100%}}
                .indented-cell {{
                        padding-top: 1px;
                        padding-bottom: 1px;
                        padding-left: 12px;
                        padding-right: 7px;
                        border: 0px solid black;
                        font-size: 8px; /* Adjust font size as needed */
                        font-family: 'Arial';
                        word-wrap: break-word;
                    overflow-wrap: break-word;}}

            </style>
        </head>
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
        with open('sampleBox.html','a') as file:
            file.write(styled_html_table)

#print(yesterdayGameIDs)

# Load the JSON data
#with open('myJSON.json') as f:
#    data = json.load(f)

# class Player:
#     def __init__(self,a):
#         self.isHome = ''
#         self.playerID = a['person']['id']
#         self.fullName = a['person']['fullName']
#         self.position = a['position']
#         self.battingOrder = ''
#         self.gameBattingStats = a['stats']['batting']
#         self.seasonBattingStats = a['seasonStats']['batting']
#         self.gamePitchingStats = a['stats']['pitching']
#         self.seasonPitchingStats = a['seasonStats']['pitching']

    # away_score = data['away']['teamStats']['batting']['runs']
    # home_score = data['home']['teamStats']['batting']['runs']
    #
