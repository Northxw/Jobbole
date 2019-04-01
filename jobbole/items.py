# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field
from scrapy.loader import ItemLoader


class JobboleItem(Item):
    table = 'article'
    title = Field()
    author = Field()
    content = Field()
    person_home_page = Field()
    publish_time = Field()
    vote_total = Field()
    bookmark = Field()
    comments = Field()

class PersonPageItem(Item):
    table = 'person'
    author = Field()
    register_time = Field()
    city = Field()
    job = Field()
    website = Field()
    prestige = Field()
    medal = Field()
    integral = Field()
    introduction = Field()
    followers = Field()
    fans = Field()
    person_home_page = Field()