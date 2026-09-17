from adafruit_datetime import timedelta, timezone, datetime, date
import time
import os
from Config import CONFIG, CONFIG_VALUES
from GameWatcher import GameWatcher

class GameWaiter:
    def __init__(self, display, team, apiRequest, local_tz, logger=None, debug=False):
        self.active = False

        self.debug = debug
        self.apiRequest = apiRequest
        self.team = team
        self.display = display
        self.logger = logger
        self.local_tz = local_tz
        self.setGame( self.getNextGame() )
        self.setGameDisplayCountdown()
        self.is_team_home = True
        return

    def setGame(self, game):
        self.game = game
        if self.game == None:
            self.start_time = None
        else:
            self.start_time = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
            self.is_team_home = False if game['awayTeam']['abbrev'] == self.team else True
        return

    def Wait(self):
        self.active = True
        utcTime = datetime.now().replace(tzinfo=timezone.utc)

        if self.debug:
            self.logger.info(f'DEBUG MODE IS ENABLED. SIMULATING GAME HAS STARTED.')
            self.start_time = utcTime
            self.game['gameState'] = 'LIVE'



        self.logger.info('Waiting for game to start...')

        while self.active:
            sleep_time = 3600 #long sleep if there was no scheduled game found
            if self.game != None:
                sleep_time = 60 #default 1 minute
                self.logger.info(f'Next game starts at {self.start_time}')
                if self.game['gameState'] in ['FUT']:
                    utcTime = datetime.now().replace(tzinfo=timezone.utc)
                    gameStartDelta = (self.start_time - utcTime)

                    if self.logger: self.logger.info(f'Game starts in {gameStartDelta}')

                    sleep_time = round(gameStartDelta.seconds * .25) #sleep for 25% of the interval until the next game
                    if self.logger: self.logger.info(f'Sleep for {sleep_time} seconds')
                else:
                    if self.logger: self.logger.info(f'{utcTime} Game is live')

                    self.display.setDisplayGameTimeText('In Progress')
                    watcher = GameWatcher(self.display, self.game, self.team, self.apiRequest, logger=self.logger, debug=self.debug)
                    watcher.Watch()
                    return

            time.sleep(sleep_time)
            self.setGame( self.getNextGame() )
            self.setGameDisplayCountdown()

    def getNextGame(self):
        today = self.utcToLocalTime(datetime.now())
        today = today.date()
        for i in range(0,31,6):
            today = date.fromordinal(today.toordinal() + i)
            schedule_endpoint = f'{os.getenv(CONFIG.API_BASE)}/club-schedule/{os.getenv(CONFIG.WATCH_TEAM_CODE)}/week/{today.year}-{today.month:02}-{today.day:02}'
            schedule = self.apiRequest.requestJson(schedule_endpoint)
            game_state_list = ['FUT', 'LIVE', 'PRE', 'CRIT']
            for game in schedule['games']:
                if game['gameState'] in game_state_list:
                    return game
        return None

    def utcToLocalTime(self, utc_datetime):
        return utc_datetime.replace(tzinfo=self.local_tz) + self.local_tz.utcoffset(utc_datetime)

    def setGameDisplayCountdown(self):
        if self.game == None:
            self.display.setDisplayGameNameText('No games found')
            self.display.setDisplayGameTimeText('')
            self.display.setDisplayTVString( '' )
            return

        game_name = f'{self.game['awayTeam']['commonName']['default']} @ {self.game['homeTeam']['commonName']['default']}'

        start_datetime = datetime.fromisoformat(f'{self.game['startTimeUTC'][:-1]}+00:00')
        start_datetime = self.utcToLocalTime(start_datetime)

        tv_market = 'H' if self.is_team_home==True else 'A'
        channel_list = []
        channel_white_list = os.getenv(CONFIG.TV_CHANNEL_LIST)

        if not channel_white_list or channel_white_list is None: #no channel white list defined, get the broadcast for the defined team
            for tv_broadcast in self.game['tvBroadcasts']:
                if tv_broadcast['market'] == tv_market:
                    channel_list.append(tv_broadcast['network'])
                if tv_broadcast['market'] == 'N' and tv['countryCode']==CONFIG.COUNTRY_CODE:
                    channel_list.append(tv['network'])
        else:                                                    #channel white list is defined, only show channels from the list
            channel_white_list = [channel.strip().lower() for channel in channel_white_list.split(',')]
            for tv_broadcast in self.game['tvBroadcasts']:
                if tv_broadcast['network'].lower() in channel_white_list:
                    channel_list.append(tv_broadcast['network'])


        tv_string = ''
        if len(channel_list) > 0:
            tv_string = 'On ' + ', '.join(channel_list)

        self.display.setDisplayGameNameText(game_name)
        self.display.setDisplayGameTimeDatetime(start_datetime)
        self.display.setDisplayTVString(tv_string)
        return
