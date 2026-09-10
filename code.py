from adafruit_datetime import timedelta, timezone, datetime

import adafruit_logging as logging
import adafruit_ntp
import adafruit_requests
import os
import rtc
import socketpool
import ssl
import time
import wifi
import digitalio
import board
from Config import CONFIG, CONFIG_VALUES
from Display import Display
from ApiRequest import ApiRequest
from GameWaiter import GameWaiter

def configValid(logger):
    errString = f''
    if not os.getenv(CONFIG.WIFI_NAME) or os.getenv(CONFIG.WIFI_NAME) is None:
        errString = errString + '-WIFI_NAME MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.WIFI_PASSWORD) or os.getenv(CONFIG.WIFI_PASSWORD) is None:
        errString = errString + '-WIFI_PASSWORD MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.LOCAL_TIME_ZONE) or os.getenv(CONFIG.LOCAL_TIME_ZONE) is None:
        errString = errString + '-LOCAL_TIME_ZONE MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.WATCH_TEAM_CODE) or os.getenv(CONFIG.WATCH_TEAM_CODE) is None:
        errString = errString + '-WATCH_TEAM_CODE MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.NTP_SERVER_LIST) or os.getenv(CONFIG.NTP_SERVER_LIST) is None:
        errString = errString + '-NTP_SERVER_LIST MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.API_BASE) or os.getenv(CONFIG.API_BASE) is None:
        errString = errString + '-API_BASE MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.GOAL_ALERT_LENGTH) or os.getenv(CONFIG.GOAL_ALERT_LENGTH) is None:
        errString = errString + '-GOAL_ALERT_LENGTH MISSING OR NOT SET\n'

    if os.getenv(CONFIG.GOAL_ALERT_COLOR_1)=='' or os.getenv(CONFIG.GOAL_ALERT_COLOR_1) is None:
        errString = errString + '-GOAL_ALERT_COLOR_1 MISSING OR NOT SET\n'

    if os.getenv(CONFIG.GOAL_ALERT_COLOR_2)=='' or os.getenv(CONFIG.GOAL_ALERT_COLOR_2) is None:
        errString = errString + '-GOAL_ALERT_COLOR_2 MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.LOCAL_TIMEZONE_OFFSET) or os.getenv(CONFIG.LOCAL_TIMEZONE_OFFSET) is None:
        errString = errString + '-LOCAL_TIMEZONE_OFFSET MISSING OR NOT SET\n'

    if not os.getenv(CONFIG.SYNC_TIMEZONE_WITH_API) or os.getenv(CONFIG.SYNC_TIMEZONE_WITH_API) is None:
        errString = errString + '-SYNC_TIMEZONE_WITH_API MISSING OR NOT SET\n'

    if os.getenv(CONFIG.SYNC_TIMEZONE_WITH_API)==CONFIG_VALUES.true:
        if not os.getenv(CONFIG.TIMEZONE_API) or os.getenv(CONFIG.TIMEZONE_API) is None:
            errString = errString + '-SYNC_TIMEZONE_WITH_API IS "True" BUT TIMEZONE_API MISSING OR NOT SET\n'
        if not os.getenv(CONFIG.TIMEZONE_API_KEY) or os.getenv(CONFIG.TIMEZONE_API_KEY) is None:
            errString = errString + '-SYNC_TIMEZONE_WITH_API IS "True" BUT TIMEZONE_API_KEY MISSING OR NOT SET\n'

    if errString != '':
        logger.info(f'Config File invalid:\n{errString}')
        return False

    return True

def setup(logger, debug=False):
    if not configValid(logger):
        return False

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
    localtime = datetime.now().replace(tzinfo=localTz) + localTz.utcoffset(datetime.now())
    logger.info(f'Clock set')
    logger.info(f'Local time: {localtime}')
    logger.info('Setup complete')
    return True

def main():
    logger = logging.getLogger('log')
    logger.setLevel(logging.INFO)

    global apiRequest
    d = Display()
    d.init()
    if not setup(logger=logger):
        d.setBeaconValue(False)
        while True:
            pass

    while True:
        d.showInfo()
        global localTz
        waiter = GameWaiter(d, os.getenv(CONFIG.WATCH_TEAM_CODE), apiRequest=apiRequest, localTz=localTz, logger=logger, debug= os.getenv(CONFIG.GAME_WATCH_DEBUG_MODE)==CONFIG_VALUES.true)
        waiter.Wait()
        time.sleep(1)


if __name__ == "__main__":
    main()
