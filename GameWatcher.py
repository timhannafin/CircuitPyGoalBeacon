import os
import time
import random
from Config import CONFIG

class GameWatcher:
    def __init__(self, display, game, team, apiRequest, logger=None, debug=False):
        self.game = game
        self.team_score = None
        self.team = team
        self.display = display
        self.active = False
        self.prev_game_state = None
        self.home_away_designator = 'awayTeam' if game['awayTeam']['abbrev'] == self.team else 'homeTeam'
        self.apiRequest = apiRequest
        self.debug = debug
        API_BASE = os.getenv(CONFIG.API_BASE)
        self.box_score_api_url = f'{API_BASE}/gamecenter/{game['id']}/boxscore'
        self.schedule_api_url = f'{API_BASE}/club-schedule/{self.team}/week/{game['gameDate']}'
        self.logger = logger
        self.game_state = 'FUT'

    def Watch(self):
        if self.logger:
            self.logger.info(f'Watcher started.')

        self.active = True
        while self.active:
            #self.readScoreFromBoxScore()
            self.readScoreFromSchedule()

            if self.game_state == 'FINAL':
                return
            time.sleep(1)

    def processScore(self, latestScore):
        if self.debug is True:
            if random.randrange(0, 9) == 0:
                latestScore = self.team_score + 1
            pass

        if self.team_score == None: #This is our first time through, initialize to the current score without alerting
            self.team_score = latestScore
        else:
            if latestScore > self.team_score:
                if self.logger:
                    self.logger.info(f'Goal Scored')
                self.display.showGoalAlert()
                self.team_score = latestScore
        return

    def readScoreFromSchedule(self):
        schedule = self.apiRequest.requestJson(self.schedule_api_url)
        if schedule != None:
            game = schedule['games'][0]
            latestScore = game[self.home_away_designator]['score'] if 'score' in game[self.home_away_designator] else 0
            self.processScore(latestScore)
            self.game_state = game['gameState']
        return

    def readScoreFromBoxScore(self):
        boxScore = self.apiRequest.requestJson(self.box_score_api_url)
        if boxScore != None: #if boxScore is None then there was a problem with the API call, try again on the next tick
            latestScore = boxScore[self.home_away_designator]['score'] if 'score' in boxScore[self.home_away_designator] else 0
            self.processScore(latestScore)
            self.game_state = boxScore['gameState']
        return