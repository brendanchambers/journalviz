# -*- coding: utf-8 -*-
"""

Quick port form a jupyter notebook
For running the PLoS CB scraper from the command line

"""

import sys, signal
from PyQt4 import QtCore, QtGui, QtWebKit
import json
import sqlite3
import urllib
from bs4 import BeautifulSoup




# class for handling the JavaScript rendering
class WebPage(QtWebKit.QWebPage):  
    def __init__(self, db):
        self._db = db
        QtWebKit.QWebPage.__init__(self)
        self.mainFrame().loadFinished.connect(self.handleLoadFinished)

    def process(self, items):
        self._items = iter(items)
        self.fetchNext() 
    
    def fetchNext(self):
        try:
            self._url, self._func = next(self._items)
            self.mainFrame().load(QtCore.QUrl(self._url))
        except StopIteration:
            return False
        return True
    
    def handleLoadFinished(self):
        self._func(self._url, self.mainFrame().toHtml())
        if not self.fetchNext():
            print('CONGRATULATIONS # processing complete')
            QtGui.qApp.quit()

# load the list of editions conveniently saved as json
load_path = "data/ploscompbio_editions.json"

with open(load_path, 'r') as infile:  
    list_of_editions = json.load(infile)


# initialize database
db = sqlite3.connect('data/plos_cb_abstracts1.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE plos_cb_abstracts1(id INTEGER PRIMARYKEY,
                    url TEXT, authors TEXT, date TEXT, title TEXT, abstract TEXT, author_summary TEXT)
                    ''')
db.commit()

##### logic for scraping editions and articles within editions
# note - using global db variable here
def process_url(url,html):
    print(url)
    print('testing database entry...')
    
    # get the list of articles from the edition
    r = str(html.toAscii())
    edition_soup = BeautifulSoup(r,"lxml")
    edition_sections = edition_soup.select('.section')
    for section in edition_sections:
        sectionID = section.select('a')[0]['id']
        print(sectionID)
        if sectionID == "Research_Article":
            research_articles_section = section
    research_articles = research_articles_section.select('.item')
        
    #try:
    #    research_articles_section = edition_soup.select('.section')[4]
    #except:
    #    research_articles_section = edition_soup.select('.section')[3] # for the javascript loaded pages
    #research_articles = research_articles_section.select('.item')

    for sample_article in research_articles:
        url = sample_article.select('a')[1].text
        print(url)
        
        authors = sample_article.select('p')[0].text
        #authors = authors.split(',') # todo normalize names for whitespace, \n, etc # wait, no do this on removal from database

        date = sample_article.select('p')[1].text.split('|')[0]
        date = date.split('\n')[1] # todo express this as a datetime object (check formatting across articles)

        title = sample_article.select('a')[0].text
        journal = "PLOS Computational Biology" 
        
        print("requesting article...")
        # go the the article url and read text
        r = urllib.urlopen(url).read()
        article_soup = BeautifulSoup(r,"lxml")
        try:
            abstract = article_soup.select("div.abstract")[0].text[8:] # get abstract from html & pick off first 8 characters,
                                        # these characters read, "Abstract"
        except:
            abstract = "No abstract found"  # todo - the abstract is probably just in another section of unlabeled text
        try:
            author_summary = article_soup.select("div.abstract")[1].text[15:] # "author summary" 
        except: # a few articles don't have author summaries
            author_summary = "No author summary found" # todo - the author summary is probably just in another section of unlabeled text
        
        article_data_object = {"url":url, "authors":authors, "date":date, "title":title,"abstract":abstract,
                                  "author_summary":author_summary}
        
        # add article data object to a database        
        cursor.execute('''INSERT INTO plos_cb_abstracts1(url, authors, date, title, abstract, author_summary)
                VALUES(:url, :authors, :date, :title, :abstract, :author_summary)''',
                article_data_object)

        db.commit()
        print('entry added to database')

# main -        
edition_urls = [ed['url'] for ed in list_of_editions]
edition_urls = edition_urls

items = [ (url,process_url) for url in edition_urls]

signal.signal(signal.SIGINT, signal.SIG_DFL)
print('press ctrl+c to quit\n')
app = QtGui.QApplication(sys.argv)
webpage = WebPage(db)
webpage.process(items)
sys.exit(app.exec_())

db.close()
print('database closed')



#### notes:
# PLOS provides another way to get this data: https://www.plos.org/text-and-data-mining
# accessing the plos provided sqlite database - http://conference.scipy.org/proceedings/scipy2018/pdfs/elizabeth_seiver.pdf
