# -*- coding: utf-8 -*-

# Scrapy settings for jobbole project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://doc.scrapy.org/en/latest/topics/settings.html
#     https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://doc.scrapy.org/en/latest/topics/spider-middleware.html

# 爬虫名称
BOT_NAME = 'jobbole'

SPIDER_MODULES = ['jobbole.spiders']
NEWSPIDER_MODULE = 'jobbole.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'jobbole (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# 设置了异步存储, 所以设置同时请求数量为100
CONCURRENT_REQUESTS = 100

# Configure a delay for requests for the same website (default: 0)
# See https://doc.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# 经测试，伯乐在线基本不存在反爬。所以这里设置下载时延很小。
DOWNLOAD_DELAY = 0.1

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See https://doc.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'jobbole.middlewares.JobboleSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See https://doc.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    # 'jobbole.middlewares.ProxyMiddleware': 544,
    'jobbole.middlewares.DownloadRetryMiddleware': 545
}

# Enable or disable extensions
# See https://doc.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See https://doc.scrapy.org/en/latest/topics/item-pipeline.html
# 选择一种保存方式即可
ITEM_PIPELINES = {
    # 'jobbole.pipelines.ImagePipeline': 200,
    'jobbole.pipelines.MysqlTwistedPipeline': 300,
}

# 图片存储位置
# IMAGES_STORE = './images'

# 文章最大长度
CONTENT_LENGTH = 1000

# 最大下载页数
MAX_PAGE = 500

# 下载超时时间
DOWNLOAD_TIMEOUT = 10

# MonogDB Settings
MONGO_URL = 'localhost'
MONGO_DB = 'bole'

# MYSQL SEETINGS
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '123456'
MYSQL_DB = 'bole'
MYSQL_PORT = 3306

# 代理服务器
PROXY_SERVER = "http://http-dyn.abuyun.com:9020"
# 代理服务器隧道验证信息
PROXY_USER = "HR827T805WJ4667D"
PROXY_PASS = "124D18494FF76D09"

# 邮件相关设置
MAIL_FROM = 'northxw@163.com'
MAIL_HOST = 'smtp.163.com'
MAIL_PORT = 25
MAIL_USER = 'northxw@163.com'
# 邮箱授权码
MAIL_PASS = 'AuthCode'

# 邮件接收者列表
RECEIVE_LIST = ['northxw@qq.com', 'northxw@sina.com']

# 邮件主题
SUBJECT = '爬虫状态报告'