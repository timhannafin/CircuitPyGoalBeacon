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
        if self.game == None:
            self.startTime = None
        else:
            self.startTime = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
        return

    def Wait(self):
        self.active = True
        utcTime = datetime.now().replace(tzinfo=timezone.utc)

        if self.debug:
            self.startTime = utcTime


        self.logger.info('Waiting for game to start...')

        while self.active:
            sleepTime = 3600 #long sleep if there was no scheduled game found
            if self.game != None:
                sleepTime = 60 #default 1 minute
                self.logger.info(f'Next game starts at {self.startTime}')
                if self.game['gameState'] in ['FUT']:
                    utcTime = datetime.now().replace(tzinfo=timezone.utc)
                    gameStartDelta = (self.startTime - utcTime)

                    if self.logger: self.logger.info(f'Game starts in {gameStartDelta}')

                    sleepTime = round(gameStartDelta.seconds * .25) #sleep for 25% of the interval until the next game
                    if self.logger: self.logger.info(f'Sleep for {sleepTime} seconds')
                else:
                    if self.logger: self.logger.info(f'{utcTime} Game is live')

                    self.display.setDisplayGameTimeText('In Progress')
                    watcher = GameWatcher(self.display, self.game, self.team, self.apiRequest, logger=self.logger, debug=self.debug)
                    watcher.Watch()
                    return

            time.sleep(sleepTime)
            self.setGame( self.getNextGame() )
            self.setGameDisplayCountdown()

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
            self.display.setDisplayTVString( '' )
            return

        gameName = f'{self.game['awayTeam']['commonName']['default']} @ {self.game['homeTeam']['commonName']['default']}'

        startDateTime = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
        startDateTime = self.utcToLocalTime(startDateTime)

        self.display.setDisplayGameNameText(gameName)
        self.display.setDisplayGameTimeDatetime(startDateTime)
        self.display.setDisplayTVText( self.game['tvBroadcasts'])
        return
