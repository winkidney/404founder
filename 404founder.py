# coding: utf-8
import logging
from threading import Thread, Event
import requests
import urlparse
from pyquery import PyQuery as PQ
from Queue import Queue
import time
from requests.exceptions import InvalidSchema
import sys
import thread

__author__ = 'winkidney'

logging.basicConfig(level=logging.DEBUG)

class Parser(Thread):
    def __init__(self, target_obj):
        super(Parser, self).__init__()
        self.target_obj = target_obj
        self.pending = False

    def run(self):
        self.parser(self.target_obj)

    def parser(self, target_obj):
        while True:
            self.pending = True
            task = target_obj.parse_queue.get()
            self.pending = False
            if "html" in task[1].lower():
                paths = target_obj.find_url(task[0], task[-1])
                for path in paths:
                    target_obj.url_queue.put(path)

        print "parser exit!"

class ContentGetter(Thread):

    def __init__(self, target_obj):
        super(ContentGetter, self).__init__()
        self.target_obj = target_obj
        self.pending = False

    def run(self):
        self.content_getter(self.target_obj)

    def content_getter(self, target_obj):
        while not target_obj.task_done:
            self.pending = True
            path = target_obj.url_queue.get()
            self.pending = False
            result = target_obj.get_content(path)
            if result is not None:
                content, mimetype = result
                target_obj.parse_queue.put((path, mimetype, content))
        print "getter exit!"

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.info("Thread %s exit!" % self.ident)


class Founder(object):

    def __init__(self, root_path, hostname, ignore_other_host=True, worker_count=2,
                 out_file_name="founder_report.log", parser_log="parser.log"):
        self.hostname = hostname
        self.root_path = root_path
        self.s = requests
        self.url_queue = Queue(maxsize=10000)
        self.parse_queue = Queue(maxsize=10000)
        self.out_file_name = out_file_name
        self.ignore_other_host = ignore_other_host
        self.task_done = False
        self.visited_urls = set()
        self.log = open(out_file_name, "w")
        self.parser_log = open(parser_log, "w")
        self.worker_count = worker_count

    def same_host(self, url):
        if urlparse.urlparse(url).netloc == self.hostname:
            return True
        else:
            return False

    def write_log(self, info):
        self.log.write(info.encode("utf-8") + "\n")

    def write_parser_log(self, info):
        self.parser_log.write(info.encode("utf-8") + "\n")

    def run(self):
        task_done = False
        getters = [ContentGetter(self) for x in range(self.worker_count)]

        self.url_queue.put(self.root_path)
        for getter in getters:
            getter.setDaemon(True)
            getter.start()

        parser = Parser(self)
        parser.setDaemon(True)
        parser.start()
        while True:
            logging.info(
                "Getter task remaining: {getter}. parser task remaining: {parser}".format(
                    getter=self.url_queue.qsize(),
                    parser=self.parse_queue.qsize(),
                ),
            )
            time.sleep(3)
            if self.url_queue.empty() and self.parse_queue.empty():
                if parser.pending:
                    for getter in getters:
                        if not getter.pending:
                            task_done = False
                            break
                        else:
                            task_done = True
            if task_done:
                break

        self.log.close()
        self.parser_log.close()

        logging.info("All task done, program will now exit.")
        logging.info("\nView log file `%s`, `%s`" % (self.log.name, self.parser_log.name))

    def find_url(self, current_path, html_content):

        urls = set()

        dom = PQ(html_content)
        scripts = dom("script")
        links = dom("a")
        csses = dom("link")
        ng_includes = dom("[ng-include]")

        element_set_list = (scripts, links, csses, ng_includes)
        property_column = ("src", "href", "href", "ng-include")
        custom_method = (None, None, None, lambda x: x.strip("'"))

        for ele_sets in zip(element_set_list, property_column, custom_method):
            self.filter_path(ele_sets[0], ele_sets[1], ele_sets[2], current_path, urls)
        self.write_parser_log(current_path + " has been parsed")
        self.write_parser_log("found: " + "||".join(urls))
        return urls

    def filter_path(self, element_list, attr_name, custom_method, current_path, url_set):
        if custom_method is None:
            custom_method = lambda x: x
        for element in element_list:
            attr_value = element.attrib.get(attr_name)
            if attr_value is not None:
                path = self.gen_path(current_path, custom_method(attr_value))
                if path is not None and path not in self.visited_urls:
                    url_set.add(path)
                    self.visited_urls.add(path)
        return url_set

    def gen_path(self, current_path, new_path):
        """
        :type current_path: str
        :type new_path: str
        """
        new_path = new_path.split("#")[0]
        if new_path.startswith("/"):
            return new_path
        elif new_path.lower().startswith("http"):
            if self.same_host(new_path):
                return new_path
            elif self.ignore_other_host:
                return None
            else:
                return new_path
        else:
            return urlparse.urljoin(current_path, new_path)

    def get_content(self, path):
        url = urlparse.urljoin("http://" + self.hostname, path)
        try:
            response = self.s.get(url)
            if response.status_code == 200:
                logging.info("URL Returns 200: %s", url)
                return response.content, response.headers['content-type']
            else:
                warning = "URL Returns %s: %s" % (response.status_code, url)
                self.write_log(warning)
                logging.warn(warning)
        except requests.HTTPError:
            logging.error("URL meet HTTPError: %s" % (url, ))
        except InvalidSchema:
            logging.warn("This is not a valid url. %s", url)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: 404founder.py host\n" + "Example: 404founder.py localhost \n"
    else:
        f = Founder("/", hostname=sys.argv[1])
        f.run()
