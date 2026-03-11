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
        self.led.value = False
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

    def getDateDisplayString(self, displayDatetime):
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

    def getTVDisplayString(self, tvBroadcasts):
        allowedNetworks = os.getenv('MY_CHANNELS').split(',')
        channelList = []
        for tv in tvBroadcasts:
            if tv['network'] in allowedNetworks:
                channelList.append(tv['network'])
        return 'On ' + ', '.join(channelList)

    def setDisplayGameNameText(self, text):
        self.game_label.text = text
        return

    def setDisplayGameTimeText(self, timeText):
        self.time_label.text = timeText
        return
    
    def setDisplayGameTimeDatetime(self, gameDatetime):
        self.time_label.text = self.getDateDisplayString(gameDatetime)
        return

    def setDisplayTVText(self, channelList):
        self.tv_label.text = self.getTVDisplayString(channelList)
        return