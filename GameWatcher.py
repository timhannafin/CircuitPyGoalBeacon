import os
import time
import random
from Config import CONFIG

class GameWatcher:
    def __init__(self, display, game, team, apiRequest, logger=None, debug=False):
        self.game = game
        self.teamScore = None
        self.team = team
        self.display = display
        self.active = False
        self.prevGameState = None
        self.TeamHomeAway = 'awayTeam' if game['awayTeam']['abbrev'] == self.team else 'homeTeam'
        self.apiRequest = apiRequest
        self.debug = debug
        API_BASE = os.getenv(CONFIG.API_BASE)
        self.boxScoreApiUrl = f'{API_BASE}/gamecenter/{game['id']}/boxscore'
        self.scheduleApiUrl = f'{API_BASE}/club-schedule/{self.team}/week/{game['gameDate']}'
        self.logger = logger
        self.gameState = 'FUT'

    def Watch(self):
        if self.logger:
            self.logger.info(f'Watcher started.')

        self.active = True
        while self.active:
            #self.readScoreFromBoxScore()
            self.readScoreFromSchedule()

            if self.gameState == 'FINAL':
                return
            time.sleep(1)

    def processScore(self, latestScore):
        if self.debug is True:
            if random.randrange(0, 9) == 0:
                latestScore = self.teamScore + 1
            pass

        if self.teamScore == None: #This is our first time through, initialize to the current score without alerting
            self.teamScore = latestScore
        else:
            if latestScore > self.teamScore:
                if self.logger:
                    self.logger.info(f'Goal Scored')
                self.display.showGoalAlert()
                self.teamScore = latestScore
        return

    def readScoreFromSchedule(self):
        schedule = self.apiRequest.requestJson(self.scheduleApiUrl)
        if schedule != None:
            game = schedule['games'][0]
            latestScore = game[self.TeamHomeAway]['score'] if 'score' in game[self.TeamHomeAway] else 0
            self.processScore(latestScore)
            self.gameState = game['gameState']
        return

    def readScoreFromBoxScore(self):
        boxScore = self.apiRequest.requestJson(self.boxScoreApiUrl)
        if boxScore != None: #if boxScore is None then there was a problem with the API call, try again on the next tick
            latestScore = boxScore[self.TeamHomeAway]['score'] if 'score' in boxScore[self.TeamHomeAway] else 0
            self.processScore(latestScore)
            self.gameState = boxScore['gameState']
        return