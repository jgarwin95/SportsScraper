class SportsScraper:

    list_of_NBA_teams = ['NOH','TOR', 'BOS', 'PHI', 'BRK', 'NYK', 'DEN', 'UTA', 'OKC', 'POR', 'MIN', 'MIL', 'IND', 'CHI', 'DET', 'CLE', 'LAL', 'LAC', 'SAC', 'PHO', 'GSW', 'MIA', 'ORL', 'WAS', 'CHO', 'ATL', 'HOU', 'DAL', 'MEM', 'SAS']
    main_sites = {'NBA':'https://www.basketball-reference.com', 'NFL':'https://www.pro-football-reference.com',
        'MLB':'https://www.baseball-reference.com', 'NHL':'https://www.hockey-reference.com'}
    NBA_second_option = {'Scores':'/boxscores', 'Teams':'/teams', 'Players':'/players'}

    def __init__(self):
        from requests_html import HTML, HTMLSession
        '''Initialize an HTMLSession'''
        self.session = HTMLSession() 

    def call_website(self, link):
        '''Receive website reponse'''
        return self.session.get(link)

    def get_boxscores(self, date, advanced=False, to_csv=False):
        '''Retreieve advanced or basic NBA boxscores from specified date. Display scores only or display and save to CSVs'''
        from datetime import datetime
        from bs4 import BeautifulSoup

        date = datetime.strptime(date, '%b %d, %Y')                 # generate datetime object from input date.
        box_score_link = self._boxscore_format(date)                # find specific boxscore page using parsed input date
        self.website = self.call_website(box_score_link)            # call link returned form _boxscore_format()

        # grab embedded individual boxscore links. Stored as list: boxscore_links
        boxscore_links = self.website.html.find('table.teams tbody tr td a', containing='Final') 

        for link in boxscore_links:                     # accessing each individual boxscore page
            r = self.call_website(self.main_sites['NBA'] + link.attrs['href']).content
            self.soup = BeautifulSoup(r, 'lxml')        # BeautifulSoup used preferentially to use search functionality with function
            
            # Below block formats header that is displayed to screen upon print (will not appear in csv).
            score_box = self.soup.select('div.scorebox')[0]
            names = score_box.find_all('strong')                       
            scores = score_box.select('div.score')
            meta_game_info = score_box.select('div.scorebox_meta')
            meta_game_info_div = meta_game_info[0].select('div')
            
            team_scores = [] 
            for score in scores:
                team_scores.append(score.text.strip())  # cleanup header whitespace present in team scores
            team_names = []
            for name in names:
                team_names.append(name.text.strip())    # cleanup header whitespace present in team names

            # Prints team names followed by scores with additional game meta data before displaying player stats.
            for score, name in zip(team_scores, team_names):
                print(f'{name}: {score}') 
            print()
            print(meta_game_info_div[0].text) # meta game info: game time & location
            print(meta_game_info_div[1].text)
            print()

            
            if advanced == False:
                #tables: list containing home and away teams boxscore in html text format
                tables = self.soup.find_all(self._get_boxscore_basic_table) # implement bs4's search functionality with input function
            elif advanced == True:          # switch if keyword argument 'advanced' is True
                tables = self.soup.find_all(self._get_boxscore_advanced_table)

            columns = tables[0].select('thead tr [scope=col]') # grab just the column headers of the basic box score
            column_labels = []
            for column in columns:
                column_labels.append(column.text)
            column_labels = ['Player Name'] + column_labels[1:] # generating column labels for display and csv

            if to_csv == True: # to_csv switch keyword argument.
                if advanced == True:
                    csv_title = 'Advanced_boxscore_' + date.strftime('%b_%d_%Y')+ '_'+ \
                    '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'
                else:
                    csv_title = 'Basic_boxscore_' + date.strftime('%b_%d_%Y') + '_' + \
                    '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'
                
                self._write_csv(csv_title, ['Team Name'] + column_labels)

            for pos, table in enumerate(tables):

                team_totals = ['Team Totals']           # footer that will appear at the end of each boxscore when displayed.
                totals = table.select('tfoot td.right')

                for total in totals:
                    team_totals.append(total.text)

                # generate two dimensional list 'player_data'
                rows = table.select('tbody tr') # grabb rows within table
                player_data = []
                for row in rows:
                    building_player = []                # individual player stats to be appended to total player_data with each loop
                    player_name = row.th.text           # player name needs to be grabbed seperately due to a unique 'th' tag.
                    if 'Reserves' not in player_name:   # 'Reserves' is row in html does not match surrounding rows and throws off scrape
                        building_player.append(player_name)

                    stats = row.select('td.right')      # list of html text containing stats

                    for stat in stats:
                        building_player.append(stat.text)

                    player_data.append(building_player) # end of each loop,append to 2D matrix 'player_data'

                    if to_csv == True:
                        self._write_csv(csv_title, [team_names[pos]] + building_player) # write each row to csv 

                # formatting and printing to the screen.
                format_block = '{:5} '
                formatter_string = format_block*(len(column_labels)-1) # format block multiplied out to specific number of columns.

                print(team_names[pos])

                print(('{:25} ' + formatter_string).format(*column_labels))
                for player in player_data:
                    # unpacking player information and display to screen. try/except avoids error if player DNP and info is missing.
                    try:
                        print(('{:25} ' + formatter_string).format(*player))
                    except:
                        pass
                print(('{:25} ' + formatter_string).format(*team_totals)) # display footer at end of table
                print()
    
    def _boxscore_format(self, date):
        '''Format URL ending based on date given in get_boxscores()'''
        boxscore_format = '?month=' + date.strftime('%m') + '&day=' + date.strftime('%d') + '&year=' + date.strftime('%Y')
        return self.main_sites['NBA'] + self.NBA_second_option['Scores'] + boxscore_format

    @staticmethod
    def _get_boxscore_basic_table(tag):
        '''Search for specified id tag containing "basic"'''
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("basic" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    @staticmethod
    def _get_boxscore_advanced_table(tag):
        '''Search for specified id tag containing "advanced"'''
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("advanced" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    @staticmethod
    def _write_csv(file_name, row):
        '''Generate new csv if none exists. Append to already existing csv'''
        import os
        import csv

        if os.path.exists(file_name):
            append_write = 'a' 
        else:
            append_write = 'w' 

        with open(file_name, append_write, newline='', encoding='utf-8') as in_file:
            csv_writer = csv.writer(in_file)
            if len(row) > 1:
                csv_writer.writerow(row)

    
scrape2 = SportsScraper()
scrape2.get_boxscores('Jan 13, 2018', advanced=False, to_csv=True)

scrapy = SportsScraper()
scrapy.get_boxscores('Mar 11, 2020', advanced=False, to_csv=True)