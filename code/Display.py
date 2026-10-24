from adafruit_datetime import datetime, date
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.rect import Rect
from adafruit_display_text import label
from adafruit_st7789 import ST7789
import adafruit_imageload
import time
import displayio

import digitalio
import board
import os
import math
from fourwire import FourWire

from Config import CONFIG, CONFIG_VALUES

class Display:
    def __init__(self):
        self.displayHeight = 135
        self.displayWidth = 240

        self.display_group = displayio.Group()
        self.alert_group = displayio.Group()
        self.text_color = 0xFFFFFF
        self.background_color = 0x000000
        self.font = bitmap_font.load_font("/fonts/Helvetica-Bold-16.bdf")
        self.large_font = bitmap_font.load_font("/fonts/FiraSans-Numerals-ExtraBold-68.bdf")
        self.led = digitalio.DigitalInOut(board.A2)
        self.led.direction = digitalio.Direction.OUTPUT
        self.GOAL_ALERT_COLOR_1 = os.getenv(CONFIG.GOAL_ALERT_COLOR_1)
        self.GOAL_ALERT_COLOR_2 = os.getenv(CONFIG.GOAL_ALERT_COLOR_2)
        self.live_display_group = None
        return

    def init(self):
        # Release any resources currently in use for the displays
        displayio.release_displays()

        spi = board.SPI()
        display_bus = FourWire(spi, command=board.A1, chip_select=board.A0)
        self.display = ST7789(
            display_bus, rotation=270, width=240, height=135, rowstart=40, colstart=53
        )

        self.game_label_background_rectangle = Rect(0, 0, self.displayWidth, math.floor(self.displayHeight*.25), fill=0xFFFF00)
        self.display_group.append(self.game_label_background_rectangle)

        placeholder_text = '#' * 25

        self.game_label = label.Label(self.font, text=placeholder_text, color=0x000000)
        self.game_label.anchor_point = (0.5, 0.0)
        self.game_label.anchored_position = (self.displayWidth/2, 10)

        self.time_label = label.Label(self.font, text=placeholder_text, color=self.text_color)
        self.time_label.anchor_point = (0.0, 0.0)
        self.time_label.anchored_position = (10, 50)

        self.tv_label = label.Label(self.font, text=placeholder_text, color=self.text_color)
        self.tv_label.anchor_point = (0.0, 0.0)
        self.tv_label.anchored_position = (10, 95)

        self.display_group.append(self.game_label)
        self.display_group.append(self.time_label)
        self.display_group.append(self.tv_label)

        bitmap, self.alertPalette = adafruit_imageload.load(
            "sprites/goal_sprite.bmp",
            bitmap=displayio.Bitmap,
            palette=displayio.Palette
        )
        self.alert_group = group = displayio.Group()
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=self.alertPalette)
        self.alert_group.append(tile_grid)
        self.led.value = False

        self.initLiveGameDisplay()
        return

    def initLiveGameDisplay(self):
        self.live_display_group = displayio.Group()
        self.game_label_background_rectangle = Rect(0, 0, self.displayWidth, math.floor(self.displayHeight*.25), fill=0xFFFF00)
        self.live_display_group.append(self.game_label_background_rectangle)

        self.home_team_label = label.Label(self.font, text='###', color=0x000000)
        self.home_team_label.anchor_point = (0.5, 0.0)
        self.home_team_label.anchored_position = (self.displayWidth/4, 10)

        self.away_team_label = label.Label(self.font, text='###', color=0x000000)
        self.away_team_label.anchor_point = (0.5, 0.0)
        self.away_team_label.anchored_position = (self.displayWidth-(self.displayWidth/4), 10)


        self.home_score_label = label.Label(self.large_font, text='0', color=self.text_color)
        self.home_score_label.anchor_point = (0.5, 0.0)
        self.home_score_label.anchored_position = ((self.displayWidth/4), 50)

        self.away_score_label = label.Label(self.large_font, text='0', color=self.text_color)
        self.away_score_label.anchor_point = (0.5, 0.0)
        self.away_score_label.anchored_position = (self.displayWidth-(self.displayWidth/4), 50)

        period_label = label.Label(self.font, text='Per:', color=self.text_color)
        period_label.anchor_point = (0.0, 1.0)
        period_label.anchored_position = (10, self.displayHeight-10)

        self.period_number_label = label.Label(self.font, text='1', color=self.text_color)
        self.period_number_label.anchor_point = (0.0, 1.0)
        self.period_number_label.anchored_position = (50, self.displayHeight-10)

        self.live_tv_label = label.Label(self.font, text='', color=self.text_color)
        self.live_tv_label.anchor_point = (1.0, 1.0)
        self.live_tv_label.anchored_position = (self.displayWidth, self.displayHeight-10)

        self.live_display_group.append(self.home_team_label)
        self.live_display_group.append(self.away_team_label)
        self.live_display_group.append(self.home_score_label)
        self.live_display_group.append(self.away_score_label)
        self.live_display_group.append(period_label)
        self.live_display_group.append(self.period_number_label)
        self.live_display_group.append(self.live_tv_label)

        return

    def setHomeScore(self, score):
        if not isinstance(score, str):
            score = str(score)
        self.home_score_label.text = score
        return

    def setAwayScore(self, score):
        if not isinstance(score, str):
            score = str(score)
        self.away_score_label.text = score
        return

    def setHomeTeam(self, team):
        self.home_team_label.text = team
        return

    def setAwayTeam(self, team):
        self.away_team_label.text = team
        return

    def setPeriod(self, period_number):
        if period_number < 4:
            period = str(period_number)
        else:
            period = 'OT'

        self.period_number_label.text = period
        return

    def showLiveGameDisplay(self):
        self.display.root_group = self.live_display_group
        return

    def showInfo(self):
        self.display.root_group = self.display_group
        return

    def showGoalAlert(self):
        self.led.value = True
        self.display.root_group = self.alert_group
        for i in range( 1, os.getenv(CONFIG.GOAL_ALERT_LENGTH) ):
            self.alertPalette[0]=self.GOAL_ALERT_COLOR_1
            self.alertPalette[1]=self.GOAL_ALERT_COLOR_2
            time.sleep(.25)
            self.alertPalette[1]=self.GOAL_ALERT_COLOR_1
            self.alertPalette[0]=self.GOAL_ALERT_COLOR_2
            time.sleep(.25)
        self.led.value = False
        self.showLiveGameDisplay()
        pass

    def getDateDisplayString(self, display_datetime):
        if display_datetime.date() == datetime.now().date():
            date_string = 'Today'
        else:
            pieces = display_datetime.ctime().split(' ')
            dayName = pieces[0]
            monthName = pieces[1]
            date = pieces[2] if pieces[2] != '' else pieces[3]
            date_string = f'{dayName}, {monthName} {date}'

        ampm = 'AM' if display_datetime.time().hour <= 12 else 'PM'
        hour = display_datetime.time().hour if display_datetime.time().hour <= 12 else display_datetime.time().hour-12
        time_string = f'{hour}:{display_datetime.time().minute:02}{ampm}'

        return f'{date_string} @ {time_string}'

    def setDisplayGameNameText(self, text):
        self.game_label.text = text
        return

    def setDisplayGameTimeText(self, timeText):
        self.time_label.text = timeText
        return

    def setDisplayGameTimeDatetime(self, game_datetime):
        self.time_label.text = self.getDateDisplayString(game_datetime)
        return

    def setDisplayTVString(self, value):
        self.tv_label.text = value
        self.live_tv_label.text = value
        return

    def setBeaconValue(self, value):
        self.led.value = value
        return
