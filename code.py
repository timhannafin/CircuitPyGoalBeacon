from adafruit_datetime import timedelta, timezone, datetime, date

import adafruit_logging as logging
import adafruit_ntp
import adafruit_requests
import os
import rtc
import socketpool
import ssl
import time
import wifi

from Config import CONFIG, CONFIG_VALUES
from Display import Display
from ApiRequest import ApiRequest
from GameWatcher import GameWatcher

def setup(debug=False, logger=None):
    ssid = os.getenv(CONFIG.WIFI_NAME)
    logger.info(f'Connecting to {ssid}...')
    wifi.radio.connect(ssid, os.getenv(CONFIG.WIFI_PASSWORD))
    logger.info(f'Connected to {ssid}')
    logger.info(f'My IP address is {wifi.radio.ipv4_address}')
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())

    global apiRequest
    apiRequest = ApiRequest(requests, logger)


    tz_string = os.getenv(CONFIG.LOCAL_TIME_ZONE)

    if os.getenv(CONFIG.SKIP_TIME_SYNC)==CONFIG_VALUES.true:
        logger.info('Synchronzing clock')
        logger.info('Clock synchronized')
        global localTz
        tz_offset = os.getenv(CONFIG.LOCAL_TIMEZONE_OFFSET)
    else:
        if rtc.RTC().datetime.tm_year == 2000:
            logger.info('Synchronzing clock')

            ntpServerList = os.getenv(CONFIG.NTP_SERVER_LIST).split(',')

            for ntpServer in ntpServerList:
                try:
                    logger.info(f'Syncing time with {ntpServer}')
                    ntp = adafruit_ntp.NTP(pool, tz_offset=0, server=ntpServer)
                    rtc.RTC().datetime = ntp.datetime
                    break
                except Exception as e:
                    logger.error(e)
                    continue

            logger.info('Clock synchronized')
            logger.info(rtc.RTC().datetime)

        if os.getenv(CONFIG.SYNC_TIMEZONE_WITH_API)==CONFIG_VALUES.true:
            logger.info('Getting timezone info')
            tz_api = os.getenv(CONFIG.TIMEZONE_API)
            tz_api = tz_api.strip('/')
            headers = { 'x-rapidapi-key': os.getenv(CONFIG.TIMEZONE_API_KEY) }
            tz_info = apiRequest.requestJson(f'{tz_api}/{tz_string}', headers=headers)
            tz_offset = tz_info['raw_offset']

            if datetime.fromisoformat(tz_info['dst_from']) < datetime.now().replace(tzinfo=timezone.utc) < datetime.fromisoformat(tz_info['dst_until']):
                logger.info(f'DST is in effect')
                tz_offset = tz_offset + tz_info['dst_offset']

        else:
            tz_offset = os.getenv(CONFIG.LOCAL_TIMEZONE_OFFSET)
        logger.info(f'Local timezone offset is {tz_offset} seconds')
    global localTz
    localTz = timezone(offset=timedelta(seconds=int(tz_offset)), name=tz_string)
    localtime = utcToLocalTime(datetime.now())
    logger.info(f'Clock set')
    logger.info(f'Local time: {localtime}')
    logger.info('Setup complete')
    return

class GameWaiter:
    def __init__(self, display, game, team, apiRequest, logger=None, debug=False):
        self.active = False

        self.debug = debug
        self.apiRequest = apiRequest
        self.team = team
        self.display = display
        self.logger = logger
        self.setGame(game)
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

def utcToLocalTime(utcDatetime):
    global localTz
    return utcDatetime.replace(tzinfo=localTz) + localTz.utcoffset(utcDatetime)

def getNextGame(apiRequest):
    today = utcToLocalTime(datetime.now())
    today = today.date()
    scheduleEndpoint = f'{os.getenv(CONFIG.API_BASE)}/club-schedule/{os.getenv(CONFIG.WATCH_TEAM_CODE)}/week/{today.year}-{today.month:02}-{today.day:02}'
    schedule = apiRequest.requestJson(scheduleEndpoint)
    gameStateList = ['FUT', 'LIVE', 'PRE', 'CRIT']
    for game in schedule['games']:
        if game['gameState'] in gameStateList:
            return game
    return None

def setGameDisplayCountdown(display, game):

    if game == None:
        display.setDisplayGameNameText('No games found')
        display.setDisplayGameTimeText('')
        display.setDisplayTVText( '' )
        return

    gameName = f'{game['awayTeam']['commonName']['default']} @ {game['homeTeam']['commonName']['default']}'

    startDateTime = datetime.fromisoformat(f'{game['startTimeUTC'][:-1]}+00:00')
    startDateTime = utcToLocalTime(startDateTime)

    display.setDisplayGameNameText(gameName)
    display.setDisplayGameTimeText(startDateTime)
    display.setDisplayTVText( game['tvBroadcasts'])
    return

def main():

    logger = logging.getLogger('log')
    logger.setLevel(logging.INFO)

    global apiRequest
    d = Display()
    d.init()
    setup(logger=logger)

    while True:
        game = getNextGame(apiRequest)
        setGameDisplayCountdown(d, game)
        d.showInfo()
        if game != None:
            waiter = GameWaiter(d, game, os.getenv(CONFIG.WATCH_TEAM_CODE), apiRequest, logger=logger, debug= os.getenv(CONFIG.GAME_WATCH_DEBUG_MODE)==CONFIG_VALUES.true)
            waiter.Wait()
            time.sleep(1)
        else:
            time.sleep(3600)


if __name__ == "__main__":
    main()
