from adafruit_datetime import timedelta, timezone, datetime
import time
import os
from Config import CONFIG, CONFIG_VALUES
from GameWatcher import GameWatcher

class GameWaiter:
    def __init__(self, display, team, apiRequest, localTz, logger=None, debug=False):
        self.active = False

        self.debug = debug
        self.apiRequest = apiRequest
        self.team = team
        self.display = display
        self.logger = logger
        self.localTz = localTz
        self.setGame( self.getNextGame() )
        self.setGameDisplayCountdown()
        return

    def setGame(self, game):
        self.game = game
        self.startTime = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
        return

    def Wait(self):
        self.active = True
        utcTime = datetime.now().replace(tzinfo=timezone.utc)

        if self.debug:
            self.startTime = utcTime

        self.logger.info(f'Next game starts at {self.startTime}')
        self.logger.info('Waiting for game to start...')


        gameStartDelta = (self.startTime-utcTime)

        while self.active:
            sleepTime = 60 #default 1 minute
            if self.startTime > utcTime:
                utcTime = datetime.now().replace(tzinfo=timezone.utc)
                gameStartDelta = (self.startTime - utcTime)

                if self.logger: self.logger.info(f'Game starts in {gameStartDelta}')

                if gameStartDelta < timedelta(hours = 1):
                    if self.logger: self.logger.info(f'{utcTime.now()} Game is in the next hour')
                    sleepTime = 60 #game is within an hour only sleep a minute at a time
                elif gameStartDelta < timedelta(hours = 2):
                    if self.logger: self.logger.info(f'{utcTime.now()} Game is in next 2 hours')
                    sleepTime = 1200 #game is within 2 hours sleep 20 minutes at a time
                elif gameStartDelta < timedelta(days = 1):
                    if self.logger: self.logger.info(f'{utcTime.now()} Game is today')
                    sleepTime = 3600 #game is today sleep an hour at a time
                elif gameStartDelta > timedelta(days = 1):
                    if self.logger: self.logger.info(f'{utcTime.now()} Game is not today')
                    sleepTime = 10800 #more than a day away, sleep 3 hours at a time
                pass
            else:
                if self.logger: self.logger.info(f'{utcTime} Game is live')

                self.display.setDisplayGameTimeText('In Progress')
                watcher = GameWatcher(self.display, self.game, self.team, self.apiRequest, logger=self.logger, debug=self.debug)
                watcher.Watch()
                return

            time.sleep(sleepTime)

    def getNextGame(self):
        today = self.utcToLocalTime(datetime.now())
        today = today.date()
        scheduleEndpoint = f'{os.getenv(CONFIG.API_BASE)}/club-schedule/{os.getenv(CONFIG.WATCH_TEAM_CODE)}/week/{today.year}-{today.month:02}-{today.day:02}'
        schedule = self.apiRequest.requestJson(scheduleEndpoint)
        gameStateList = ['FUT', 'LIVE', 'PRE', 'CRIT']
        for game in schedule['games']:
            if game['gameState'] in gameStateList:
                return game
        return None
    
    def utcToLocalTime(self, utcDatetime):
        return utcDatetime.replace(tzinfo=self.localTz) + self.localTz.utcoffset(utcDatetime)
    
    def setGameDisplayCountdown(self):
        if self.game == None:
            self.display.setDisplayGameNameText('No games found')
            self.display.setDisplayGameTimeText('')
            self.display.setDisplayTVText( '' )
            return

        gameName = f'{self.game['awayTeam']['commonName']['default']} @ {self.game['homeTeam']['commonName']['default']}'

        startDateTime = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
        startDateTime = self.utcToLocalTime(startDateTime)

        self.display.setDisplayGameNameText(gameName)
        self.display.setDisplayGameTimeDatetime(startDateTime)
        self.display.setDisplayTVText( self.game['tvBroadcasts'])
        return