from requests_html import HTML, HTMLSession
from datetime import datetime
from bs4 import BeautifulSoup
import os
import csv

class SportsScraper(object):

    list_of_NBA_teams = ['NOH','TOR', 'BOS', 'PHI', 'BRK', 'NYK', 'DEN', 'UTA', 'OKC', 'POR', 'MIN', 'MIL', 'IND', 'CHI', 'DET', 'CLE', 'LAL', 'LAC', 'SAC', 'PHO', 'GSW', 'MIA', 'ORL', 'WAS', 'CHO', 'ATL', 'HOU', 'DAL', 'MEM', 'SAS']
    main_sites = {'NBA':'https://www.basketball-reference.com', 'NFL':'https://www.pro-football-reference.com',
        'MLB':'https://www.baseball-reference.com', 'NHL':'https://www.hockey-reference.com'}
    NBA_second_option = {'Scores':'/boxscores', 'Teams':'/teams', 'Players':'/players'}

    def __init__(self):
        '''Initialize an HTMLSession'''
        self.session = HTMLSession() 

    def call_website(self, link):
        """Receive website reponse

        Args:
            link (str): link to get response from.

        Returns:
            Response: Response object retrieved from site.
        """        
        return self.session.get(link)

    def get_boxscores(self, date, advanced=False, to_csv=False, expand_single_file=False, aggregate=False):
        """Retreieve advanced or basic NBA boxscores from specified date. Display scores only or display and save to CSVs

        Args:
            date (str): date string of format %b %d, %Y
            advanced (bool, optional): Provides advanced boxscores rather than basic. Defaults to False.
            to_csv (bool, optional): If True will write to csv. Defaults to False.
            expand_single_file (bool, optional): Writes all boxscores to single csv file rather than multiple. Defaults to False.
            aggregate (bool, optional): Aggregates boxscore to team totals. Defaults to False.
        """        
        #'''Retreieve advanced or basic NBA boxscores from specified date. Display scores only or display and save to CSVs'''
           

        # list of various column labels, depending on the output format chosen. 
        self._general_basic_column_labels = ['Player Name','MP','FG','FGA','FG%','3P','3PA','3P%','FT','FTA','FT%',
        'ORB','DRB','TRB','AST','STL','BLK','TOV','PF','PTS','+/-']
        self._general_advanced_column_labels = ['Player Name','MP','TS%','eFG%','3PAr','FTr','ORB%','DRB%','TRB%',
        'AST%','STL%','BLK%','TOV%','USG%','ORtg','DRtg','BPM']
        self._expanded_column_labels = ['Date', 'Team Name'] + self._general_basic_column_labels
        self._basic_team_total_columns = ['Date', 'Team Name'] + self._general_basic_column_labels[1:][:-1]
        self._advanced_team_total_columns =  ['Date', 'Team Name'] + self._general_advanced_column_labels[1:][:-1]


        date = datetime.strptime(date, '%b %d, %Y')                 # generate datetime object from input date.
        box_score_link = self._boxscore_format(date)                # find specific boxscore page using parsed input date
        self.website = self.call_website(box_score_link)            # call link returned form _boxscore_format()

        # grab embedded individual boxscore links. Stored as list: boxscore_links
        boxscore_links = self.website.html.find('table.teams tbody tr td a', containing='Final') 

        # depending on state of aggregate, the column labels submitted to _write_csv() are different.
        if (to_csv == True):
            if aggregate == True:
                aggregated_title = self._format_csv_title(date, advanced, expand_single_file, aggregate)
                if advanced == True:
                    self._write_csv(aggregated_title, self._advanced_team_total_columns)
                else:
                    self._write_csv(aggregated_title, self._basic_team_total_columns)
            elif expand_single_file == True:
                aggregated_title = self._format_csv_title(date, advanced, expand_single_file, aggregate)
                self._write_csv(aggregated_title, self._expanded_column_labels)


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

            #keyword argument for writing to csv. Place individual boxscores for that date in single csv if single_file == True.
            if all([to_csv, not aggregate, not expand_single_file]):
                csv_title = self._format_csv_title(date, advanced, expand_single_file, aggregate, team_names)
                if advanced == True:
                    self._write_csv(csv_title, ['Team Name'] + self._general_advanced_column_labels)
                else:
                    self._write_csv(csv_title, ['Team Name'] + self._general_basic_column_labels)

            # bs4's html search ability with input function is used to distinguish between advanced and basic tables 
            if advanced == False:
                tables = self.soup.find_all(self._get_boxscore_basic_table) 
            elif advanced == True:          
                tables = self.soup.find_all(self._get_boxscore_advanced_table)

            for pos, table in enumerate(tables):

                team_totals = ['Team Totals']       # footer that will appear at the end of each boxscore when displayed.
                totals = table.select('tfoot td.right')

                for total in totals:
                    team_totals.append(total.text)

                if all([to_csv, aggregate]):        # team totals are written to csv if aggregate and to_cav are True
                    self.agg_team_totals = [date.strftime('%b-%d-%Y') ,team_names[pos]] + team_totals[1:]
                    self._write_csv(aggregated_title, self.agg_team_totals) 


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

                    if all([to_csv, not aggregate]):
                        if expand_single_file == True:
                            self._write_csv(aggregated_title, [date.strftime('%b-%d-%Y'), team_names[pos]] + building_player) # agg_title is a static title based on date in initial function call
                        else:
                            self._write_csv(csv_title, [team_names[pos]] + building_player) # csv_title rotates and is based on team matchups

                self._display_boxscore(pos, team_scores, team_names, meta_game_info_div, player_data, team_totals, advanced)
                
    @staticmethod
    def _format_csv_title(date, advanced, expand_single_file, aggregate, team_names=None):
        """Generate the csv title depending on keyword arg inputs to get_boxscores()

        Args:
            date (datetime): datetime object 
            advanced (bool): True if the stats to be placed in csv file are advanced rather than basic.
            expand_single_file (bool): True if all stats are to be placed into a single csv file.
            aggregate (bool): True if csv is to have team totals stats rather than individual stats in single file.
            team_names (list, optional): List of team names whose stats are to be created in csv. Defaults to None.

        Returns:
            str: Unique title of csv.
        """        
        if advanced == True:
            if aggregate == True:
                csv_title = 'Team_Totals_Advanced_boxscores_' + date.strftime('%b_%d_%Y') + '.csv'
            elif expand_single_file == True:
                csv_title = 'Expanded_Advanced_boxscores_' + date.strftime('%b_%d_%Y') + '.csv'
            else:
                csv_title = 'Advanced_boxscore_' + date.strftime('%b_%d_%Y')+ '_'+ \
                        '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'

        elif advanced == False:
            if aggregate == True:
                csv_title = 'Team_Totals_Basic_boxscores_' + date.strftime('%b_%d_%Y') + '.csv'
            elif expand_single_file == True:
                csv_title = 'Expanded_Basic_boxscores_' + date.strftime('%b_%d_%Y') + '.csv'
            else:
                csv_title = 'Basic_boxscore_' + date.strftime('%b_%d_%Y') + '_' + \
                        '_'.join(team_names[0].split()) + '_' + '_'.join(team_names[1].split()) + '.csv'

        return csv_title 


    def _display_boxscore(self, pos, team_scores, team_names, meta_game_info_div, player_data, team_totals, advanced):
        """Prints team names followed by scores with additional game meta data before displaying player stats.

        Args:
            pos (int): index indicating which teams stats are being displayed
            team_scores (list): list of scores
            team_names (list): list of team names
            meta_game_info_div (list): list containining location and time of game
            player_data (list): player stats
            team_totals (list): team total stats
            advanced (bool): Whether or not advanced stats are being shown.
        """        
        for score, name in zip(team_scores, team_names):
            print(f'{name}: {score}') 
        print()
        print(meta_game_info_div[0].text) # meta game info: game time & location
        print(meta_game_info_div[1].text)
        print()

        print(team_names[pos])

        format_block = '{:5} '
        if advanced == False:
            formatter_string = format_block*(len(self._general_basic_column_labels)-1) # format block multiplied out to specific number of columns.
            print(('{:25} ' + formatter_string).format(*self._general_basic_column_labels))
        else:
            formatter_string = format_block*(len(self._general_advanced_column_labels)-1) # format block multiplied out to specific number of columns.
            print(('{:25} ' + formatter_string).format(*self._general_advanced_column_labels))

        for player in player_data:
            # unpacking player information and display to screen. try/except avoids error if player DNP and info is missing.
            try:
                print(('{:25} ' + formatter_string).format(*player))
            except:
                pass
        print(('{:25} ' + formatter_string).format(*team_totals)) # display footer at end of table
        print()

    def _boxscore_format(self, date):
        """Format URL ending based on date given in get_boxscores()

        Args:
            date (datetime): date of the scores being accessed

        Returns:
            str: URL ending specific for scores being accessed
        """        
        boxscore_format = '?month=' + date.strftime('%m') + '&day=' + date.strftime('%d') + '&year=' + date.strftime('%Y')
        return self.main_sites['NBA'] + self.NBA_second_option['Scores'] + boxscore_format

    @staticmethod
    def _get_boxscore_basic_table(tag):
        """Search for specified id tag containing 'basic'

        Args:
            tag (HTML tag): list of HTML tags

        Returns:
            HTML tag: return the specific tag if found
        """        
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("basic" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    @staticmethod
    def _get_boxscore_advanced_table(tag):
        """Search for specified id tag containing 'advanced'

        Args:
            tag (HTML tag): list of HTML tags

        Returns:
            HTML tag: return the specific tag if found
        """    
        tag_id = tag.get("id")
        tag_class = tag.get("class")
        return (tag_id and tag_class) and ("advanced" in tag_id and "section_wrapper" in tag_class and not "toggleable" in tag_class)

    @staticmethod
    def _write_csv(file_name, row):
        """Generate new csv if none exists. Append to already existing csv

        Args:
            file_name (str): name of file to be writtin or appended to
            row (list): list of items to be written to csv.
        """        
        if os.path.exists(file_name):
            append_write = 'a'          # if csv file exists append to it
        else:
            append_write = 'w'          # if not generate new one

        in_file = open(file_name, append_write, newline='', encoding='utf-8')
        csv_writer = csv.writer(in_file)
        if 'Expanded' in file_name:
            if len(row) > 2:
                csv_writer.writerow(row)
        elif len(row) > 1:
            csv_writer.writerow(row)
        in_file.close()
