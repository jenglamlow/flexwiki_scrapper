"""FlexWiki Soap Web Services Client

Usage:
  flexsoap url URL [-o DESTINATION]
  flexsoap namespace NAMESPACE HOST [-o DESTINATION] [--start=INDEX]

Options:
  -h --help         Show this screen
  --version         Show version
  URL               Export resources from URL
  NAMESPACE         Export all resource from namespace
  HOST              Hostname
  -o DESTINATION    Export output destination
  --start=INDEX     Start scrapping resources from INDEX, else it will scrape all namspace resources
"""

import requests
import os
import sys
import html
import getopt
from docopt import docopt
from urllib.parse import urlparse
import urllib.request
from bs4 import BeautifulSoup
from requests_kerberos import HTTPKerberosAuth, REQUIRED


class FlexSoap:
    def __init__(self, host, auth=None):
        self.__host = host
        self.__auth = auth
        self.__webservice = "http://" + self.__host + '/wiki/editservice.asmx?WSDL'
        self.__header = {"content-type": "application/soap+xml; charset=utf-8"}

    def test_connect(self, page=None):
        if page:
            url = page
        else:
            url = self.__webservice
        r = requests.get(url, auth=auth)
        return r.status_code == 200

    def scrape_by_url(self, url, out):

        o = urlparse(url)

        namespace = o.path.split("/")[-2]
        name = o.path.split("/")[-1].split(".")[0]
        name = name.replace("%20", " ")

        # Get Wiki Text For Topic
        body = """<?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <GetTextForTopic xmlns="http://www.flexwiki.com/webservices/">
              <topicName>""" + \
                  "<Name>" + name + "</Name>" + \
                  "<Namespace>" + namespace + "</Namespace>" + \
              """</topicName>
            </GetTextForTopic>
          </soap12:Body>
        </soap12:Envelope>"""

        r = requests.post(self.__webservice, data=body, headers=self.__header, auth=self.__auth)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Change working directory
        old_dir = os.getcwd()
        os.chdir(out)

        wiki_folder = "pages"
        attachment_folder = "attachments"

        if not os.path.exists(wiki_folder):
            os.mkdir(wiki_folder)
        if not os.path.exists(attachment_folder):
            os.mkdir(attachment_folder)

        os.chdir(wiki_folder)

        # Get wiki format
        wiki_filename = name
        result = soup.find_all('gettextfortopicresult')

        for t in result:
            s = "\n".join(t.text.split("\r\n"))
            with open(wiki_filename, 'wb') as f:
                f.write(s.encode('utf8'))

        # Make name folder as current working directory
        os.chdir("..\\" + attachment_folder)

        # Get Image
        body="""<?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <GetHtmlForTopic xmlns="http://www.flexwiki.com/webservices/">
              <topicName>""" + \
                  "<Name>" + name + "</Name>" + \
                  "<Namespace>" + namespace + "</Namespace>" + \
              """</topicName>
            </GetHtmlForTopic>
          </soap12:Body>
        </soap12:Envelope>"""

        r = requests.post(self.__webservice, data=body, headers=self.__header, auth=self.__auth)
        soup = BeautifulSoup(html.unescape(r.text), "lxml")

        result = soup.find_all('img')

        for img in result:
            imgsrc = img['src']
            if imgsrc[0] == "/":
                imgsrc = 'http://' + self.__host + imgsrc
            try:
                r = requests.get(imgsrc, auth=self.__auth)
                if r.status_code == 200:
                    i = urlparse(img['src'])
                    img_file = i.path.split("/")[-1]
                    f = open(img_file, 'wb')
                    f.write(r.content)
                    f.close()
            except:
                pass
                print("Failed to get img source: ", imgsrc)

        # Change the working directory back to parent directory
        os.chdir(old_dir)

    def scrape_by_namespace(self, namespace, out, **kwargs):
        # Get all the wiki page related to the namespace
        body="""<?xml version="1.0" encoding="utf-8"?>
        <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
          <soap12:Body>
            <GetAllTopics xmlns="http://www.flexwiki.com/webservices/">
              <cb>""" + \
                "<Namespace>" + namespace + "</Namespace>" + \
              """</cb>
            </GetAllTopics>
          </soap12:Body>
        </soap12:Envelope>"""
        r = requests.post(self.__webservice, data=body, headers=self.__header, auth=self.__auth)
        soup = BeautifulSoup(html.unescape(r.text), "lxml")
        result = soup.find_all('name')

        start_index = int(kwargs['start'])
        result = result[start_index:]

        for name in result:
            url = "http://" + self.__host + '/wiki/default.aspx/' + namespace + '/' + name.string + '.html'
            print("Scrapping " + name.string)
            self.scrape_by_url(url, out)

    def scrape_wiki(self, mode, source, out, **kwargs):
        if mode == "url":
            self.scrape_by_url(source, out)
        elif mode == "namespace":
            self.scrape_by_namespace(source, out, **kwargs)

def main(arg):
    # URL mode
    if arg["url"]:
        mode = "url"
        o = urlparse(arg["URL"])
        host = o.netloc
        source = arg["URL"]
    elif arg["namespace"]:
        mode = "namespace"
        host = arg["HOST"]
        source = arg["NAMESPACE"]

    # Optional argument -o exist
    out = os.getcwd()

    if arg["-o"]:
        out = os.path.normpath(arg["-o"])

    auth = HTTPKerberosAuth(force_preemptive=True)

    FlexWiki = FlexSoap(host, auth=auth)

    start_index = arg["--start"] or '0'
    FlexWiki.scrape_wiki(mode, source, out, start=start_index)


if __name__ == "__main__":
    arg = docopt(__doc__, version='flexsoap 1.0')
    main(arg)
