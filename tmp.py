from pathlib import Path

from extract_emails import DefaultFilterAndEmailFactory as Factory
from extract_emails import DefaultWorker
from extract_emails.browsers.requests_browser import RequestsBrowser as Browser
from extract_emails.data_savers import CsvSaver


websites = [
    "https://highleads.co/",
    "https://1337.ma/",
]

browser = Browser()
data_saver = CsvSaver(save_mode="a", output_path=Path("output.csv"))

for website in websites:
    factory = Factory(
        website_url=website, browser=browser, depth=5, max_links_from_page=1
    )
    worker = DefaultWorker(factory)
    data = worker.get_data()
    data_saver.save(data)
