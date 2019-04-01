# -*- coding: utf-8 -*-

import scrapy
from scrapy import Request
from jobbole.items import JobboleItem, PersonPageItem
from scrapy.mail import MailSender
from jobbole.utils.commen import get_md5
from jobbole.pipelines import COUNT_IMAGES_NUMS
import time
import re

class ArticlesSpider(scrapy.Spider):
    # 爬虫启动时间
    start = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    name = 'articles'
    allowed_domains = ['jobbole.com']
    url = 'http://blog.jobbole.com/all-posts/page/{}'

    def start_requests(self):
        # 初始化爬取链接
        for i in range(1, self.settings.get('MAX_PAGE') + 1):
            yield Request(url=self.url.format(str(i)),
                          callback=self.parse,
                          errback=self.error_back,
                          priority = 10)

    def parse(self, response):
        """
        解析文章列表页
        """
        # 文章详情页URL列表
        url_list = response.css('#archive .post.floated-thumb .post-thumb a::attr(href)').extract()
        # 文章标题列表
        title_list = response.css('#archive > div > div.post-thumb a::attr(title)').extract()
        if url_list:
            self.logger.debug("Article URL List: {}".format(url_list))
        for href in url_list:
            url = response.urljoin(href)
            yield Request(url=url,
                          callback=self.parse_article_detail,
                          errback=self.error_back,
                          priority=8,
                          meta={'title': title_list.pop(0)})
        """
         # 下一页
        href = response.css('#archive > div.navigation.margin-20 > a.next.page-numbers::attr(href)').extract_first()
        if href:
            next_page = response.urljoin(href)
            self.logger.debug('NextPage URL: %s' %(next_page))
            yield Request(url=next_page, callback=self.parse, errback=self.error_back)
        """

    def parse_article_detail(self, response):
        """
        解析文章详情页
        """
        try:
            # 使用Crawl api记录文章详情页请求成功的Request
            self.crawler.stats.inc_value("ArticleDetail_Success_Reqeust")
        except Exception as e:
            _ = e

        item = JobboleItem()
        # 文章标题
        item['title'] = get_md5(response.meta['title'])
        # 作者
        item['author'] = response.css('#author-bio > h3 > a::text').extract_first()
        # 原文出处
        if item['author'] is None:
            item['author'] = response.xpath('//*[@id="post-114638"]/div[3]/div[2]/a[1]/text()').extract_first('unknown')
        # 个人主页URL
        item['person_home_page'] = response.css('#author-bio > h3 > a::attr(href)').extract_first('unknown')
        # 正文
        item['content'] = re.sub('\s+', '',response.xpath('//div[@class="entry"]').xpath('string(.)').extract_first().strip())
        # 限制content长度
        if item['content']:
            if len(item['content']) > self.settings.get('CONTENT_LENGTH'):
                item['content'] = item['content'][0: self.settings.get('CONTENT_LENGTH')] + '...'
        # 发布时间
        item['publish_time'] = response.xpath('//p[@class="entry-meta-hide-on-mobile"]/text()').extract_first().split('·')[0].strip()
        vote_mark_comment = response.css('.post-adds')
        # 获赞数
        item['vote_total'] = vote_mark_comment.css('.btn-bluet-bigger.href-style.vote-post-up h10::text').extract_first('0')
        # 收藏数
        bookmark = vote_mark_comment.xpath('//*[contains(@class, "bookmark-btn")]/text()').extract_first()
        item['bookmark'] = bookmark.split()[0] if len(bookmark.split()) > 1 else 0
        # 评论数
        comment = vote_mark_comment.css('a > span::text').extract_first()
        item['comments'] = comment.split()[0] if len(comment.split()) > 1 else 0
        yield item

        # 个人主页Request
        if item['person_home_page'] != "unknown":
            yield Request(url=item['person_home_page'],
                          callback=self.parse_person_page,
                          errback=self.error_back,
                          dont_filter = False,
                          meta={'author': item['author']})

    def parse_person_page(self, response):
        """
        解析个人详情页
        """
        # 使用Crawl API记录请求个人主页成功的Request
        self.crawler.stats.inc_value("PersonPage_Success_Reqeust")
        item = PersonPageItem()
        # 作者
        item['author'] = response.meta['author']
        # 注册时间、城市、单位、网站
        member_info = response.xpath('//*[@id="wrapper"]/div[3]/div[1]/span')
        # print("INFO: %d" %len(member_info))
        member_info_dict = {'注册':'register_time', '城市':'city', '单位':'job', '网站':'website'}
        for info in member_info:
            verfi_text = info.xpath('./strong/text()').extract_first().strip()
            if verfi_text in member_info_dict.keys():
                if verfi_text != '网站':
                    item[member_info_dict[verfi_text]] = info.xpath('./text()').extract_first().strip().replace('：','')
                else:
                    item[member_info_dict[verfi_text]] = info.xpath('./a/@href').extract_first()

        # 声望值、勋章数、积分
        profile_points = response.css('#wrapper > div.grid-4 > div > div > div.profile-points')
        item['prestige'] = profile_points.xpath('./li[1]/strong/a/text()').extract_first()
        item['medal'] = profile_points.xpath('./li[2]/strong/text()').extract_first()
        item['integral'] = profile_points.xpath('./li[3]/strong/a/text()').extract_first()
        # 简介
        item['introduction'] = response.css('#wrapper > div.grid-4 > div > div > div.profile-bio').xpath('./text()').extract_first()
        # 关注者
        item['followers'] = response.xpath('//*[@id="wrapper"]/div[2]/div/div/div[4]/a[1]/text()').extract_first()
        # 粉丝
        item['fans'] = response.xpath('//*[@id="wrapper"]/div[2]/div/div/div[5]/a[1]/text()').extract_first()
        # 粉丝数
        fans_num = item['fans']
        self.logger.debug(item)
        yield item

        # 如果粉丝数量不为0, 获取用户粉丝列表页的URL, 返回Request并递归爬取粉丝的粉丝数据
        if fans_num:
            member_following_list_url = response.xpath('//*[@id="wrapper"]/div[2]/div/div/div[5]/a[1]/@href').extract_first()
            yield Request(url=member_following_list_url,
                          callback=self.parse_member_following_list,
                          errback=self.error_back,
                          priority=5,
                          dont_filter=False)


    def parse_member_following_list(self, response):
        """
        获取粉丝列表页的URL
        """
        following_list = response.css('div.member-status.box > ul > li > div.follow-icon > a::attr(href)').extract()
        # self.logger.debug('FOLLOWING_LIST: %s' % str(following_list))
        for person_page in following_list:
            yield Request(url=person_page,
                          callback=self.parse_person_page,
                          errback=self.error_back,
                          dont_filter=False,
                          meta={'author': person_page.split('/')[-1]})   # 从个人主页的URL中获取用户名称

        # 判断用户是否拥有一页以上的粉丝, 如果有则递归获取所有粉丝的个人主页URL
        next_page_url = response.css('div.member-status.box > ul > ul > a::attr(href)').extract_first()
        if next_page_url:
            # self.logger.debug('NEXT_PAGE_URL: %s'%next_page_url)
            yield Request(url=next_page_url,
                          callback=self.parse_member_following_list,
                          errback=self.error_back,
                          dont_filter=False
                          )

    def error_back(self, e):
        """
        使用Crawl API记录失败请求数量并Debug错误原因
        """
        self.logger.debug('Error: %s' % (e.reason))
        self.crawler.stats.inc_value("Failed_Reqeust")
        _ = self

    def close(self, reason):
        """
        爬虫邮件报告状态
        """
        # 结束时间
        fnished = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        # 创建邮件发送对象
        mail = MailSender.from_settings(self.settings)
        # 邮件内容
        spider_name = self.settings.get('BOT_NAME')
        start_time = self.start
        artice_success_request = self.crawler.stats.get_value("ArticleDetail_Success_Reqeust")
        personpage_success_request = self.crawler.stats.get_value("PersonPage_Success_Reqeust")
        failed_request = self.crawler.stats.get_value("Failed_Reqeust")
        # 若请求成功, 则默认为0
        if failed_request == None:
            failed_request = 0
        insert_into_success = self.crawler.stats.get_value("Success_InsertedInto_MySqlDB")
        failed_db = self.crawler.stats.get_value("Failed_InsertInto_DB")
        # 若插入成功, 则默认为0
        if failed_db == None:
            failed_db = 0
        fnished_time = fnished
        body = "爬虫名称: {}\n\n 开始时间: {}\n\n 文章请求成功总量：{}\n 个人信息获取总量：{}\n 请求失败总量：{} \n\n 数据库存储总量：{}\n 数据库存储失败总量：{}\n\n 结束时间  : {}\n".format(
            spider_name,
            start_time,
            artice_success_request,
            personpage_success_request,
            failed_request,
            insert_into_success,
            failed_db,
            fnished_time)
        try:
            # 发送邮件
            mail.send(to=self.settings.get('RECEIVE_LIST'), subject=self.settings.get('SUBJECT'), body=body)
        except Exception as e:
            self.logger.error("Send Email Existing Error, Reason: {}".format(e.args))