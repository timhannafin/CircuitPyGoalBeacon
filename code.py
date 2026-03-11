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

from Config import CONFIG, CONFIG_VALUES
from Display import Display
from ApiRequest import ApiRequest
from GameWaiter import GameWaiter

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
    localtime = datetime.now().replace(tzinfo=localTz) + localTz.utcoffset(datetime.now())
    logger.info(f'Clock set')
    logger.info(f'Local time: {localtime}')
    logger.info('Setup complete')
    return

def main():
    logger = logging.getLogger('log')
    logger.setLevel(logging.INFO)

    global apiRequest
    d = Display()
    d.init()
    setup(logger=logger)

    while True:
        d.showInfo()
        global localTz
        waiter = GameWaiter(d, os.getenv(CONFIG.WATCH_TEAM_CODE), apiRequest=apiRequest, localTz=localTz, logger=logger, debug= os.getenv(CONFIG.GAME_WATCH_DEBUG_MODE)==CONFIG_VALUES.true)
        waiter.Wait()
        time.sleep(1)


if __name__ == "__main__":
    main()
