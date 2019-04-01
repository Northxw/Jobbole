#  Crawl Jobble - 伯乐在线全站爬虫

## 爬取思路
- 以 [全部文章](http://blog.jobbole.com/all-posts/) 的首页为爬取起始点，获取每页所有文章详情页URL。
- 进入文章详情页，获取文章的标题、发布时间、转发收藏评论数、文章正文等，并获取文章的作者昵称及个人主页链接。
- 进入个人主页获取注册时间、城市、单位、网站和粉丝数、关注者等信息，并获取粉丝列表页URL。
- 进入粉丝列表页，获取所有粉丝的个人主页URL。
- 将粉丝个人主页URL返回至个人主页解析函数，递归爬取粉丝的粉丝，直至粉丝的粉丝数量为零。

## 爬取流程图

![爬取流程图](https://github.com/Northxw/Crawl_Jobbole/blob/master/jobbole/utils/%E6%B5%81%E7%A8%8B%E5%9B%BE.png)

## 第三方库依赖列表
库名称 | 安装方式
:---:|:---:
<b>Twisted</b> | <b>推荐：[LFD镜像网站下载对应版本库](https://www.lfd.uci.edu/~gohlke/pythonlibs/)</b>
<b>Pywin32</b> | <b>[pywin32 官网](https://sourceforge.net/projects/pywin32/files/pywin32/Build%20221/)

## 难点分析
### 1.文章标题
&emsp; 文章标题在文章详情页不好获取，可以选择在文章列表页获取后使用Reqeust的meta参数传递给下级解析函数。如下：
```Python
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
```

### 2.文章作者及个人主页URL
&emsp; 经判断，伯乐在线大部分文章来源于引用，也就是说实际用户数量不是很多。所以，当引用文章和真实博文处于同一页，就得想办法做区分。
```Python
 # 作者
item['author'] = response.css('#author-bio > h3 > a::text').extract_first()
# 原文出处
if item['author'] is None:
    item['author'] = response.xpath('//*[@id="post-114638"]/div[3]/div[2]/a[1]/text()').extract_first('unknown')
    # 个人主页URL
    item['person_home_page'] = response.css('#author-bio > h3 > a::attr(href)').extract_first('unknown')
```

### 3. 个人详情页注册信息
&emsp; 注册信息可算是个Bug吧。有的用户只填写了城市，有的用户把包括城市在内的单位、个人网站等全部填写。所以，必须自己实现算法来区分。
```Python
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
```

### 4. 递归获取粉丝的粉丝信息
&emsp; 当解析完用户的个人主页后，会得到粉丝列表页URL，只需遍历后将个人主页链接 yield 给解析函数即可实现递归爬取网站所有用户信息。
```Python
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
```

### 5. MysqlTwistedPipeline - 异步存储数据
&emsp; 由于Spider的爬取速度高于数据库存储速度，为避免数据拥塞，实现基于 **twisted.enterprise.adbapi** 的异步存储。需要实现的主要方法如下：
```Python
class MysqlTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_crawler(cls, crawler):
        # 部分代码已省略
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
        # 部分代码已省略
        pass
```
&emsp; 同样实现了常规数据库存储、Json文件存储等管道。另外，设置了请求最大数量为100，只需要在settings.py中设置即可。
```Python
# Obey robots.txt rules
ROBOTSTXT_OBEY = False
```

### 6. RetryMiddleware - 重试中间件
&emsp; 伯乐在线的用户信息偏少，下载失败后重试。这里继承已有的Retry中间件，仅作微小改动。

### 7. 数据表字段设置
&emsp; 经测试，文章的内容长度普遍大于1000，而且充满制表符换行符。这里使用正则去除空白并设置了保存的最大长度值，超过就截取。如下：
```Python
    item['content'] = re.sub('\s+', '',response.xpath('//div[@class="entry"]').xpath('string(.)').extract_first().strip())
    # 限制content长度
    if item['content']:
        if len(item['content']) > self.settings.get('CONTENT_LENGTH'):
            item['content'] = item['content'][0: self.settings.get('CONTENT_LENGTH')] + '...'
```

### 8.爬虫状态报告
&emsp; 状态报告邮件应该是必不可少的。所以，在之后的每次实战我都将添加该模块功能。

## 结果

&emsp; **爬虫状态邮件**

![email_jobbole](https://github.com/Northxw/Crawl_Jobbole/blob/master/jobbole/utils/email_jobbole.png)

&emsp; **文章信息表**

![db_article](https://github.com/Northxw/Crawl_Jobbole/blob/master/jobbole/utils/db_article.png)

&emsp; **个人信息表**

![db_person](https://github.com/Northxw/Crawl_Jobbole/blob/master/jobbole/utils/db_person.png)

## 更新列表
&emsp; 暂无
