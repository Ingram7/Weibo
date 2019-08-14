# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html


# import json
# import logging
# import requests
import random
import pymongo
from Weibo.settings import LOCAL_MONGO_HOST, LOCAL_MONGO_PORT, DB_NAME


# 阿布云 ip代理
import base64
# 代理服务器
proxyServer = "http://http-dyn.abuyun.com:9020"
# 代理隧道验证信息
proxyUser = "  "
proxyPass = "  "
proxyAuth = "Basic " + base64.urlsafe_b64encode(bytes((proxyUser + ":" + proxyPass), "ascii")).decode("utf8")
class ProxyMiddleware(object):
    def process_request(self, request, spider):
        request.meta["proxy"] = proxyServer
        request.headers["Proxy-Authorization"] = proxyAuth


# 代理ip
# class ProxyMiddleware():
#     def __init__(self, proxy_url):
#         self.logger = logging.getLogger(__name__)
#         self.proxy_url = proxy_url
#
#     def get_random_proxy(self):
#         try:
#             # response = requests.get(self.proxy_url)
#             # if response.status_code == 200:
#             #     proxy = response.text
#
#             response = requests.get(self.proxy_url)
#             if response.status_code == 200:
#                 proxy_d = random.choice(json.loads(response.text))
#                 ip = proxy_d.get('ip')
#                 port = proxy_d.get('port')
#                 proxy = ip + ':' + port
#
#                 return proxy
#         except requests.ConnectionError:
#             return False
#
#     def process_request(self, request, spider):
#         # if request.meta.get('retry_times'):
#             proxy = self.get_random_proxy()
#             if proxy:
#                 uri = 'https://{proxy}'.format(proxy=proxy)
#                 self.logger.debug('使用代理 ' + proxy)
#                 request.meta['proxy'] = uri
#
#     @classmethod
#     def from_crawler(cls, crawler):
#         settings = crawler.settings
#         return cls(
#             proxy_url=settings.get('PROXY_URL')
#         )

# cookie池
class CookiesMiddleware(object):
    """
    每次请求都随机从账号池中选择一个账号去访问
    """
    def __init__(self):
        client = pymongo.MongoClient(LOCAL_MONGO_HOST, LOCAL_MONGO_PORT)
        self.account_collection = client[DB_NAME]['account']

    def process_request(self, request, spider):
        all_count = self.account_collection.find({'status': 'success'}).count()
        if all_count == 0:
            raise Exception('当前账号池为空')
        random_index = random.randint(0, all_count - 1)
        random_account = self.account_collection.find({'status': 'success'})[random_index]
        request.headers.setdefault('Cookie', random_account['cookie'])
        request.meta['account'] = random_account




