import adafruit_logging as logging
import adafruit_ntp
import adafruit_requests
import json

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