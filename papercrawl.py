# -*- coding: utf-8 -*-
# python3

import os
import sys
import ssl
import urllib.request as rt
import logging
from multiprocessing import Pool
from bs4 import BeautifulSoup

logging.getLogger().setLevel(logging.INFO)
import pdb

ssl._create_default_https_context = ssl._create_unverified_context

def dowload(url, savepath, title):
    try :
        rt.urlretrieve(url, savepath)
        logging.info("Saved paper '{}'".format(title))
    except Exception as e:
        print(e)
        return False
    return True

def is_related(title, keywords):
    title = title.lower()
    for kw in keywords:
        if kw.lower() in title:
            return True
    return False

def download_nlp_paper(conference, year, keywords=None, savedir=None, poolnum=8):
    '''
    conference: ACL/EMNLP/NAACL (supported conference in ACL Anthology)
    year: 2019
    keywords: find the paper only related with your keywords, such as 'summarization-dialog'
    savedir: saved path, default: current path
    poolnum: the number of thread
    '''
    conference = conference.lower()
    if not savedir:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), '{0}{1}'.format(conference.upper(), year))
    if not os.path.isdir(savedir):
        os.mkdir(savedir)
    url = 'https://www.aclanthology.org/events/{0}-{1}/'.format(conference, year)
    with rt.urlopen(url) as f:
        html = f.read()
    html = BeautifulSoup(html, features="html.parser")
    keywords = keywords.split('-') if keywords else None
    
    if "acl" in conference:
        categories = [f"{year}{conference}-long", f"{year}{conference}-short", 
                    f"{year}findings-{conference}"]
    else:
        categories = [f"{year}{conference}-main",  f"{year}findings-{conference}"]

    available_paper_list = []
    for cat in categories:
        
        items = html.find("div", {"id": cat}).findAll("p", {'class':'align-items-stretch'})
        logging.info('{0} papers have been found in {1}'.format(len(items), cat))
        related_paper_num = 0
        sub_dir = os.path.join(savedir, cat)
        if not os.path.isdir(sub_dir):
            os.mkdir(sub_dir)
        for item in items:
            info = item.findAll('a', {'class': 'align-middle'})[-1]
            title, paper_info = info.text, info.attrs['href']
            download_url = 'https://www.aclanthology.org{}.pdf'.format(paper_info[:-1])
    
            if not keywords or is_related(title, keywords):
                related_paper_num += 1
                if 'W' in paper_info:
                    filename = '[{0}{1}WorkShop] {2}.pdf'.format(conference, year, title)
                else:
                    filename = '[{0}{1}] {2}.pdf'.format(conference, year, title)
                savedfile = os.path.join(savedir, filename)
                if not os.path.exists(savedfile):
                    available_paper_list.append((download_url, savedfile, title))
    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')

    pool = Pool(poolnum)
    status = []
    for item in available_paper_list:
        status.append(pool.apply_async(dowload, args=(item[0], item[1], item[2],)))
    pool.close()
    pool.join()
    result = [ele.get() for ele in status]
    error_num, error_item = 0, []
    for res, item in zip(result, available_paper_list):
        if not res:
            error_num += 1
            error_item.append(item)

    if error_num > 0:
        with open(os.path.join(savedir, 'error_id.txt'), 'w', encoding='utf-8') as file:
            for item in error_item:
                file.write('\t'.join(item) + '\n')
                logging.info('{} papers dowloading failed, see error_id.txt for details'.format(error_num))
    else:
        logging.info('Dowloading success'.format(error_num))
    return


if __name__ == '__main__':
    # download_nlp_paper('naacl', 2000, 'summari')
    for i in range(2000, 2020):
        download_nlp_paper('cl', i, 'summar')
