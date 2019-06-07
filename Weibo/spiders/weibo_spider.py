# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
from ..items import *

import json
from pyquery import PyQuery as pq


class WeiboSpiderSpider(scrapy.Spider):
    name = 'weibo_spider'
    allowed_domains = ['m.weibo.cn']
    # start_urls = ['http://m.weibo.cn/']

    # 用户
    user_url = 'https://m.weibo.cn/api/container/getIndex?uid={uid}&type=uid&value={uid}&containerid=100505{uid}'
    # 微博
    weibo_url = 'https://m.weibo.cn/api/container/getIndex?uid={uid}&type=uid&page={page}&containerid=107603{uid}'
    # 关注
    follow_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_followers_-_{uid}&page={page}'
    # 粉丝     注意 粉丝页码参数是since_id=,而不是关注页码中page=
    fan_url = 'https://m.weibo.cn/api/container/getIndex?containerid=231051_-_fans_-_{uid}&since_id={page}'



    start_uids = [
        '2803301701',  # 人民日报
        # '1699432410',  # 新华社
        # '1974576991',  # 环球时报
        # '5476386628',  # 侠客岛
    ]

    def start_requests(self):
        for uid in self.start_uids:
            yield Request(self.user_url.format(uid=uid), callback=self.parse_user)

    # 解析用户信息
    def parse_user(self, response):

        self.logger.debug(response)
        result = json.loads(response.text)
        if result.get('data').get('userInfo'):
            user_info = result.get('data').get('userInfo')
            user_item = UserItem()
            user_item['id'] = user_info.get('id')  # 用户id
            user_item['name'] = user_info.get('screen_name')  # 昵称
            user_item['profile_image'] = user_info.get('profile_image_url')  # 头像图片
            user_item['cover_image'] = user_info.get('profile_image_url')  # 背景图片
            user_item['verified_reason'] = user_info.get('verified_reason')  # 微博认证
            user_item['description'] = user_info.get('description')  # 简介
            user_item['weibos_count'] = user_info.get('statuses_count')  # 微博数
            user_item['fans_count'] = user_info.get('followers_count')  # 粉丝
            user_item['follows_count'] = user_info.get('follow_count')  # 关注数
            user_item['mbrank'] = user_info.get('mbrank')  # 会员等级
            user_item['verified'] = user_info.get('verified')  # 是否认证
            user_item['verified_type'] = user_info.get('verified_type')  # 认证类型
            user_item['verified_type_ext'] = user_info.get('verified_type_ext')  # 以下不知道是啥
            user_item['gender'] = user_info.get('gender')
            user_item['mbtype'] = user_info.get('mbtype')
            user_item['urank'] = user_info.get('urank')

            yield user_item

            uid = user_info.get('id')
            # 关注
            yield Request(self.follow_url.format(uid=uid, page=1), callback=self.parse_follows,
                          meta={'page': 1, 'uid': uid})
            # 粉丝
            yield Request(self.fan_url.format(uid=uid, page=1), callback=self.parse_fans,
                          meta={'page': 1, 'uid': uid})
            # 微博
            yield Request(self.weibo_url.format(uid=uid, page=1), callback=self.parse_weibos,
                          meta={'page': 1, 'uid': uid})

    # 解析微博列表
    def parse_weibos(self, response):

        result = json.loads(response.text)
        if result.get('ok') and result.get('data').get('cards'):
            weibos = result.get('data').get('cards')
            for weibo in weibos:
                mblog = weibo.get('mblog')
                # 判断是否存在mblog，有时不存在
                if mblog:
                    weibo_item = WeiboItem()

                    weibo_item['id'] = mblog.get('id')  # 微博id
                    weibo_item['idstr'] = mblog.get('idstr')
                    weibo_item['edit_count'] = mblog.get('edit_count')
                    weibo_item['created_at'] = mblog.get('created_at')
                    weibo_item['version'] = mblog.get('version')
                    weibo_item['thumbnail_pic'] = mblog.get('thumbnail_pic')
                    weibo_item['bmiddle_pic'] = mblog.get('bmiddle_pic')
                    weibo_item['original_pic'] = mblog.get('original_pic')
                    weibo_item['source'] = mblog.get('source')
                    weibo_item['user'] = response.meta.get('uid') # 用户id

                    # 检测有没有阅读全文:
                    all_text = mblog.get('text')
                    if '>全文<' in all_text:
                        # 微博全文页面链接
                        all_text_url = 'https://m.weibo.cn/statuses/extend?id=' + mblog.get('id')
                        yield Request(all_text_url, callback=self.parse_all_text, meta={'item': weibo_item})

                    # 判断是否是转发微博
                    elif pq(mblog.get('text')).text() == '转发微博':
                        if '>全文<' in mblog.get('retweeted_status').get('text'):
                            # 微博全文页面链接
                            all_text_url2 = 'https://m.weibo.cn/statuses/extend?id=' + mblog.get(
                                'retweeted_status').get('id')
                            yield Request(all_text_url2, callback=self.parse_all_text, meta={'item': weibo_item})
                        else:
                            weibo_item['text'] = pq(mblog.get('retweeted_status').get('text')).text().replace('\n', '')
                            yield weibo_item

                    else:
                        weibo_item['text'] = pq(mblog.get('text')).text().replace('\n', '')
                        yield weibo_item

            # 下一页微博
            uid = response.meta.get('uid')
            page = response.meta.get('page') + 1
            yield Request(self.weibo_url.format(uid=uid, page=page), callback=self.parse_weibos,
                          meta={'uid': uid, 'page': page})

    # 有阅读全文的情况，获取全文
    def parse_all_text(self, response):
        result = json.loads(response.text)
        if result.get('ok') and result.get('data'):
            all_text = result.get('data').get('longTextContent')
            weibo_item = response.meta['item']
            weibo_item['text'] = pq(all_text).text().replace('\n', '')
            # print(weibo_item['text'])
            yield weibo_item

    # 解析用户关注列表
    def parse_follows(self, response):

        result = json.loads(response.text)
        if result.get('ok') and result.get('data').get('cards') and len(result.get('data').get('cards')) and result.get(
                'data').get('cards')[-1].get('card_group'):
            # 解析用户
            follows = result.get('data').get('cards')[-1].get('card_group')
            # for follow in follows:
            #     if follow.get('user'):
            #         uid = follow.get('user').get('id')
            #         yield Request(self.user_url.format(uid=uid), callback=self.parse_user)

            uid = response.meta.get('uid')
            # 关注列表
            user_relation_item = UserRelationItem()
            follows = [{'id': follow.get('user').get('id'), 'name': follow.get('user').get('screen_name')} for follow in
                       follows]
            user_relation_item['id'] = uid
            user_relation_item['follows'] = follows
            user_relation_item['fans'] = []
            yield user_relation_item
            # 下一页关注
            page = response.meta.get('page') + 1
            yield Request(self.follow_url.format(uid=uid, page=page),
                          callback=self.parse_follows, meta={'page': page, 'uid': uid})

    # 解析用户粉丝列表
    def parse_fans(self, response):

        result = json.loads(response.text)
        if result.get('ok') and result.get('data').get('cards') and len(result.get('data').get('cards')) and result.get(
                'data').get('cards')[-1].get('card_group'):
            # 解析用户
            fans = result.get('data').get('cards')[-1].get('card_group')
            # for fan in fans:
            #     if fan.get('user'):
            #         uid = fan.get('user').get('id')
            #         yield Request(self.user_url.format(uid=uid), callback=self.parse_user)

            uid = response.meta.get('uid')
            # 粉丝列表
            user_relation_item = UserRelationItem()
            fans = [{'id': fan.get('user').get('id'), 'name': fan.get('user').get('screen_name')} for fan in
                    fans]
            user_relation_item['id'] = uid
            user_relation_item['fans'] = fans
            user_relation_item['follows'] = []
            yield user_relation_item
            # 下一页粉丝
            page = response.meta.get('page') + 1
            yield Request(self.fan_url.format(uid=uid, page=page),
                          callback=self.parse_fans, meta={'page': page, 'uid': uid})
