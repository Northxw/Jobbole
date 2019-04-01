# -*-coding:utf-8 -*-

from scrapy.exporters import JsonItemExporter
from twisted.enterprise import adbapi
from scrapy import Request
from scrapy.exceptions import DropItem
from scrapy.pipelines.images import ImagesPipeline
import logging
import pymysql
import codecs
import json

# 统计下载图片的总量
COUNT_IMAGES_NUMS = {'IMAGES_NUMS': 0}

class MysqlPipeline(object):
    def __init__(self, host, database, user, password, port):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        # 设置保存文章内容的最大长度
        self.limit = 1000

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            host=crawler.settings.get('MYSQL_HOST'),
            database=crawler.settings.get('MYSQL_DB'),
            user=crawler.settings.get('MYSQL_USER'),
            password=crawler.settings.get('MYSQL_PASSWORD'),
            port=crawler.settings.get('MYSQL_PORT')
        )

    def open_spider(self, spider):
        self.db = pymysql.connect(self.host, self.user, self.password, self.database, self.port)
        self.cursor = self.db.cursor()

    def process_item(self, item, spider):
        data = dict(item)
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = "INSERT INTO {table} ({keys}) VALUES ({values}) ON DUPLICATE KEY UPDATE".format(
            table=item.table, keys=keys, values=values)
        update = ','.join([" {key} = %s".format(key=key) for key in data])
        sql += update
        try:
            if self.cursor.execute(sql, tuple(data.values())*2):
                # 记录成功插入的数据总量
                spider.crawler.stats.inc_value('Success_InsertedInto_MySqlDB')
                self.db.commit()
        except Exception as e :
            logging.error("Failed Insert Into, Reason: {}".format(e.args))
            # 记录插入失败的数据总量
            spider.crawler.stats.inc_value('Failed_InsertInto_DB')
            self.db.rollback()
        return item

    def close_spider(self, spider):
        self.db.close()

class JsonPepeline(object):
    # 自定义JSON文件导出
    def open_spider(self, spider):
        self.file = codecs.open('article.json', 'w', encoding='utf-8')
        self.file.write(b'[\n')

    def process_item(self, item, spider):
        # 序列化数据
        lines = json.dumps(dict(item), indent=2, ensure_ascii=False) + '\n'
        self.file.write(lines)
        return item

    def close_spider(self, spider):
        self.file.write(b']')
        self.file.close()


class MysqlTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_crawler(cls, crawler):
        params = dict(
            host=crawler.settings.get('MYSQL_HOST'),
            database=crawler.settings.get('MYSQL_DB'),
            user=crawler.settings.get('MYSQL_USER'),
            password=crawler.settings.get('MYSQL_PASSWORD'),
            port=crawler.settings.get('MYSQL_PORT'),
            cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True,
        )
        dbpool = adbapi.ConnectionPool("pymysql", **params)
        # 返回类的实例
        return cls(dbpool)

    def process_item(self, item, spider):
        # 利用Twisted提供的adbapi实现Mysql的异步插入数据
        query = self.dbpool.runInteraction(self.do_insert, item, spider)
        # 异常处理
        query.addErrback(self.handle_error, spider)

    def handle_error(self, failure, spider):
        # 接收并记录插入失败的数据总量
        spider.crawler.stats.inc_value('Failed_InsertInto_DB')
        _ = failure

    def do_insert(self, cursor, item, spider):
        # 存在就更新, 不存在就插入
        data = dict(item)
        keys = ', '.join(data.keys())
        values = ', '.join(['%s'] * len(data))
        sql = "INSERT INTO {table} ({keys}) VALUES ({values}) ON DUPLICATE KEY UPDATE".format(
            table=item.table, keys=keys, values=values)
        update = ', '.join([" {key} = %s".format(key=key) for key in data])
        sql += update
        cursor.execute(sql, tuple(data.values())*2)
        # self.db.commit()   adbapi会自动提交数据的插入事实
        # 记录成功插入数据库的数据总量
        try:
            spider.crawler.stats.inc_value('Success_InsertedInto_MySqlDB')
        except Exception as e:
            _ = e

class ImagePipeline(ImagesPipeline):
    def file_path(self, request, response=None, info=None):
        url = request.url
        file_name = url.split('/')[-1]
        return file_name

    def item_completed(self, results, item, info):
        image_paths = [x['path'] for ok, x in results if ok]
        if not image_paths:
            raise DropItem('Image Downloaded Failed')
        else:
            COUNT_IMAGES_NUMS['IMAGES_NUMS'] += 1
            return item

    def get_media_requests(self, item, info):
        yield Request(item['avatar'])