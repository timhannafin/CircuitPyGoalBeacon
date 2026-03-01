from adafruit_bitmap_font import bitmap_font
from adafruit_datetime import timedelta, timezone, datetime, date
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_st7789 import ST7789
from fourwire import FourWire

import adafruit_imageload
import adafruit_logging as logging
import adafruit_ntp
import adafruit_requests
import bitmaptools
import board
import digitalio
import displayio
import ipaddress
import json
import math
import os
import random
import rtc
import socketpool
import ssl
import terminalio
import time
import wifi


class CONFIG_VALUES:
    false = 'False'
    true = 'True'

class CONFIG:
    WIFI_NAME = 'WIFI_NAME'
    WIFI_PASSWORD = 'WIFI_PASSWORD'
    WATCH_TEAM_CODE = 'WATCH_TEAM_CODE'
    MY_CHANNELS = 'MY_CHANNELS'
    GAME_WATCH_DEBUG_MODE = 'GAME_WATCH_DEBUG_MODE'
    NTP_SERVER_LIST = 'NTP_SERVER_LIST'
    SKIP_TIME_SYNC = 'SKIP_TIME_SYNC'
    SYNC_TIMEZONE_WITH_API = 'SYNC_TIMEZONE_WITH_API'
    LOCAL_TIME_ZONE = 'LOCAL_TIME_ZONE'
    LOCAL_TIMEZONE_OFFSET = 'LOCAL_TIMEZONE_OFFSET'
    TIMEZONE_API = 'TIMEZONE_API'
    TIMEZONE_API_KEY = 'TIMEZONE_API_KEY'
    API_BASE = 'API_BASE'
    GOAL_ALERT_COLOR_1 = 'GOAL_ALERT_COLOR_1'
    GOAL_ALERT_COLOR_2 = 'GOAL_ALERT_COLOR_2'
    GOAL_ALERT_LENGTH = 'GOAL_ALERT_LENGTH'

class Display:
    def __init__(self):
        self.displayHeight = 135
        self.displayWidth = 240

        self.displayGroup = displayio.Group()
        self.alertGroup = displayio.Group()
        self.textColor = 0xFFFFFF
        self.bgColor = 0x000000
        self.font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
        self.led = digitalio.DigitalInOut(board.A2)
        self.led.direction = digitalio.Direction.OUTPUT
        self.GOAL_ALERT_COLOR_1 = os.getenv(CONFIG.GOAL_ALERT_COLOR_1)
        self.GOAL_ALERT_COLOR_2 = os.getenv(CONFIG.GOAL_ALERT_COLOR_2)
        return

    def init(self):
        TEXT_COLOR = 0xFFFF00

        # Release any resources currently in use for the displays
        displayio.release_displays()

        spi = board.SPI()
        tft_cs = board.A0
        tft_dc = board.A1

        display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs)
        self.display = ST7789(
            display_bus, rotation=270, width=240, height=135, rowstart=40, colstart=53
        )

        self.game_label_background_rectangle = Rect(0, 0, self.displayWidth, math.floor(self.displayHeight*.25), fill=0xFFFF00)
        self.displayGroup.append(self.game_label_background_rectangle)

        placeholder_text = '#' * 25

        self.game_label = label.Label(self.font, text=placeholder_text, color=0x000000)
        self.game_label.anchor_point = (0.5, 0.0)
        self.game_label.anchored_position = (self.displayWidth/2, 10)

        self.time_label = label.Label(self.font, text=placeholder_text, color=self.textColor)
        self.time_label.anchor_point = (0.0, 0.0)
        self.time_label.anchored_position = (10, 50)

        self.tv_label = label.Label(self.font, text=placeholder_text, color=self.textColor)
        self.tv_label.anchor_point = (0.0, 0.0)
        self.tv_label.anchored_position = (10, 95)

        self.displayGroup.append(self.game_label)
        self.displayGroup.append(self.time_label)
        self.displayGroup.append(self.tv_label)


        bitmap, self.alertPalette = adafruit_imageload.load(
            "sprites/goal_sprite.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette
        )
        self.alertGroup = group = displayio.Group()
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=self.alertPalette)
        self.alertGroup.append(tile_grid)

        return


    def showInfo(self):
        self.display.root_group = self.displayGroup

    def showGoalAlert(self):
        self.led.value = True
        self.display.root_group = self.alertGroup
        for i in range( 1, os.getenv(CONFIG.GOAL_ALERT_LENGTH) ):
            self.alertPalette[0]=self.GOAL_ALERT_COLOR_1
            self.alertPalette[1]=self.GOAL_ALERT_COLOR_2
            time.sleep(.25)
            self.alertPalette[1]=self.GOAL_ALERT_COLOR_1
            self.alertPalette[0]=self.GOAL_ALERT_COLOR_2
            time.sleep(.25)
        self.led.value = False
        self.showInfo()
        pass

    def setDisplayGameNameText(self, text):
        self.game_label.text = text
        return

    def setDisplayGameTimeText(self, text):
        self.time_label.text = text
        return

    def setDisplayTVText(self, text):
        self.tv_label.text = text
        return



class ApiRequest:
    def __init__(self, requests, logger=None):
        self.requests = requests
        self.logger = logger

    def requestJson(self, url, encoding='utf-8', headers=None):

        if self.logger:
            self.logger.info(url)

        response = self.requests.request('GET', url, stream=True, headers=headers)
        data_string = ''
        try:
            for p in response.iter_content(chunk_size=1000):
                data_string += p.decode(encoding)
            obj = json.loads(data_string)
        except e:
            self.logger.error(e)
            return None
        response.close()
        return obj

def setup(debug=False, logger=None):
    ssid = os.getenv(CONFIG.WIFI_NAME)
    logger.info(f'Connecting to {ssid}...')
    wifi.radio.connect(ssid, os.getenv(CONFIG.WIFI_PASSWORD))
    logger.info(f'Connected to {ssid}')
    logger.info(f'My IP address is {wifi.radio.ipv4_address}')
    global pool
    pool = socketpool.SocketPool(wifi.radio)
    # global requests
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
        else:
            tz_offset = os.getenv(CONFIG.LOCAL_TIMEZONE_OFFSET)

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
        schedule = apiRequest.requestJson(self.scheduleApiUrl)
        if schedule != None:
            game = schedule['games'][0]
            latestScore = game[self.TeamHomeAway]['score'] if 'score' in game[self.TeamHomeAway] else 0
            self.processScore(latestScore)
            self.gameState = game['gameState']
        return

    def readScoreFromBoxScore(self):
        boxScore = apiRequest.requestJson(self.boxScoreApiUrl)
        if boxScore != None: #if boxScore is None then there was a problem with the API call, try again on the next tick
            latestScore = boxScore[self.TeamHomeAway]['score'] if 'score' in boxScore[self.TeamHomeAway] else 0
            self.processScore(latestScore)
            self.gameState = boxScore['gameState']
        return

def utcToLocalTime(utcDatetime):
    global localTz
    return utcDatetime.replace(tzinfo=localTz) + localTz.utcoffset(utcDatetime)

def getDateDisplayString(displayDatetime):
    if displayDatetime.date() == datetime.now().date():
        dateString = 'Today'
    else:
        pieces = displayDatetime.ctime().split(' ')
        dayName = pieces[0]
        monthName = pieces[1]
        date = pieces[2] if pieces[2] != '' else pieces[3]
        dateString = f'{dayName}, {monthName} {date}'

    ampm = 'AM' if displayDatetime.time().hour <= 12 else 'PM'
    hour = displayDatetime.time().hour if displayDatetime.time().hour <= 12 else displayDatetime.time().hour-12
    timeString = f'{hour}:{displayDatetime.time().minute:02}{ampm}'

    return f'{dateString} @ {timeString}'

def getTVDisplayString(tvBroadcasts):
    allowedNetworks = os.getenv('MY_CHANNELS').split(',')
    channelList = []
    for tv in tvBroadcasts:
        if tv['network'] in allowedNetworks:
            channelList.append(tv['network'])
    return 'On ' + ', '.join(channelList)

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
    display.setDisplayGameTimeText(getDateDisplayString(startDateTime))
    display.setDisplayTVText( getTVDisplayString(game['tvBroadcasts']))
    return

def main():

    logger = logging.getLogger('log')
    logger.setLevel(logging.INFO)


    setup(logger=logger)


    global apiRequest
    d = Display()
    d.init()

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
