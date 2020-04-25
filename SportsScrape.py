from requests_html import HTML, HTMLSession
from bs4 import BeautifulSoup 

class SportsScraper:

    list_of_NBA_teams = ['NOH','TOR', 'BOS', 'PHI', 'BRK', 'NYK', 'DEN', 'UTA', 'OKC', 'POR', 'MIN', 'MIL', 'IND', 'CHI', 'DET', 'CLE', 'LAL', 'LAC', 'SAC', 'PHO', 'GSW', 'MIA', 'ORL', 'WAS', 'CHO', 'ATL', 'HOU', 'DAL', 'MEM', 'SAS']
    main_sites = {'NBA':'https://www.basketball-reference.com', 'NFL':'https://www.pro-football-reference.com',
        'MLB':'https://www.baseball-reference.com', 'NHL':'https://www.hockey-reference.com'}
    NBA_second_option = {'Scores':'/boxscores', 'Teams':'/teams', 'Players':'/players'}

    def __init__(self):
        '''Initialize an HTMLSession'''
        self.session = HTMLSession() #putting this here since I believe it only needs to be called once. Felt like a good choice for initializing the class instance

    def call_website(self, link):
        '''Receive website reponse'''
        return self.session.get(link) #whenever you need to call a website you can access the instances HTMLSession() variable

    def get_boxscores(self, date, advanced=False, to_csv=[False, False]): #second boolean operator in to_csv will be fore single csv or individual
        from datetime import datetime

        self.date = datetime.strptime(date, '%b %d, %Y') #strip input date
        self.box_score_link = self.boxscore_format() #find specific boxscore page using parsed input date
        self.website = self.call_website(self.box_score_link) #call returned link

        boxscore_links = self.website.html.find('table.teams tbody tr td a', containing='Final') #grabbing links to each individual boxscores

        for link in boxscore_links: #accessing each individual score page
            r = self.call_website(self.main_sites['NBA']+link.attrs['href']).content #use beautifulsoup here to give ability to search html with functions
            self.soup = BeautifulSoup(r, 'lxml')
            
            score_box = self.soup.select('div.scorebox')[0]
            names = score_box.find_all('strong')
            scores = score_box.select('div.score')
            meta_game_info = score_box.select('div.scorebox_meta')
            meta_game_info_div = meta_game_info[0].select('div')
            
            team_scores = []
            for score in scores:
                team_scores.append(score.text.strip())

            team_names = []
            for name in names:
                team_names.append(name.text.strip())

            # Print team names followed by scores with additional game meta data before displaying player stats.
            for score, name in zip(team_scores, team_names):
                print(f'{name}: {score}') #prints team and points scored by that team.
            print()
            print(meta_game_info_div[0].text) #prints game time and location
            print(meta_game_info_div[1].text)
            print()

            #Switch if keyword argument 'advanced' is True
            if advanced == False:
                tables = self.soup.find_all(self.get_boxscore_basic_table) #grab box score tables on page.
            elif advanced == True:
                tables = self.soup.find_all(self.get_boxscore_advanced_table)

            #Select column header html, append to list column_labels
            columns = tables[0].select('thead tr [scope=col]') #Grab just the column headers of the basic box score
            column_labels = []
            for column in columns:
                column_labels.append(column.text)
            column_labels = ['Player Name'] + column_labels[1:]

            #Write to csv to switch keyword 'to_csv' is True.
            if to_csv[0] == True:
                if advanced == True:
                    csv_title = 'Advanced_boxscore_' + self.date.strftime('%b_%d_%Y')+ '_'+ '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'
                else:
                    csv_title = 'Basic_boxscore_' + self.date.strftime('%b_%d_%Y') + '_' + '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'
                
                self.write_csv(csv_title, ['Team Name'] + column_labels)

            for pos, table in enumerate(tables):

                team_totals = ['Team Totals']
                totals = table.select('tfoot td.right')

                for total in totals:
                    team_totals.append(total.text)

                #below block is grabbing players name and stat info and building out a list of lists containing this info.
                #which could then be used to write to csv or display on screen, etc.
                rows = table.select('tbody tr') #Grabbing a smaller block that is just the body.
                player_data = []
                for row in rows:
                    building_player = [] #containing individual player stats in list to be appended to total player_data with each loop
                    player_name = row.th.text #Have to grab name seperately since it is under a unique 'th' tag.
                    if 'Reserves' not in player_name: #reserves row in html does not match surrounding rows and throws off scrape
                        building_player.append(player_name)

                    stats = row.select('td.right')

                    for stat in stats:
                        building_player.append(stat.text)

                    player_data.append(building_player)

                    if to_csv[0] == True:
                        self.write_csv(csv_title, [team_names[pos]] + building_player)

                #below block if formatting and printing to the screen.
                format_block = '{:5} '
                formatter_string = format_block*(len(column_labels)-1)

                print(team_names[pos])

                print(('{:25} ' + formatter_string).format(*column_labels))
                for player in player_data:
                    try:
                        print(('{:25} ' + formatter_string).format(*player))
                    except:
                        continue
                print(('{:25} ' + formatter_string).format(*team_totals))
                print()
    
    @staticmethod
    def get_boxscore_basic_table(tag):
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("basic" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    def get_boxscore_advanced_table(self, tag):
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("advanced" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    def boxscore_format(self):
        '''Format URL ending based on date given in get_boxscores()'''
        boxscore_format = '?month=' + self.date.strftime('%m') + '&day=' + self.date.strftime('%d') + '&year=' + self.date.strftime('%Y')
        return self.main_sites['NBA'] + self.NBA_second_option['Scores'] + boxscore_format

    def display_team_codes(self):
        print(self.list_of_NBA_teams)

    def write_csv(self, file_name, row):
        import os
        import csv

        if os.path.exists(file_name):
            append_write = 'a' # append if already exists
        else:
            append_write = 'w' # make a new file if not

        with open(file_name, append_write, newline='', encoding='utf-8') as in_file:
            csv_writer = csv.writer(in_file)
            if len(row) > 1:
                csv_writer.writerow(row)

    


scrape = SportsScraper()
scrape.get_boxscores('Mar 11, 2020', advanced=False, to_csv=True)