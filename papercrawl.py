# -*- coding: utf-8 -*-
# python3

import os
import sys
import ssl
import urllib.request as rt
import logging
from multiprocessing import Pool
from bs4 import BeautifulSoup
from typing import Optional, List, Any
import time
import argparse

logging.getLogger().setLevel(logging.INFO)
import pdb
try:
    from selenium import webdriver 
    from selenium.webdriver.chrome.options import Options
except Exception as e:
    print("download ACM paper need selenium...")

ssl._create_default_https_context = ssl._create_unverified_context

def fetch_html(url: str):
    with rt.urlopen(url) as f:
        html = f.read()
    html = BeautifulSoup(html, features="html.parser")
    return html

def fetch_html_by_driver(url: str, driver: Any):
    driver.get(url)
    html = driver.page_source
    html = BeautifulSoup(html, features="html.parser")
    return html

def download(url: str, savepath: str, title: str) -> bool:
    """
    Downloads a file from a URL and saves it to a specified path.
    
    Args:
        url (str): The URL of the file to be downloaded.
        savepath (str): The path where the file should be saved.
        title (str): The title of the file being downloaded (for logging).
        
    Returns:
        bool: True if the download was successful, False otherwise.
    """
    try :
        rt.urlretrieve(url, savepath)
        logging.info("Saved paper '{}'".format(title))
    except Exception as e:
        print(e)
        return False
    return True

def is_related(title: str, keywords: List[str]) -> bool:
    """
    Checks if the title contains any of the keywords.
    
    Args:
        title (str): The title to check.
        keywords (List[str]): The list of keywords to search for.
        
    Returns:
        bool: True if the title contains any of the keywords, False otherwise.
    """
    title = title.lower()
    return any(kw.lower() in title for kw in keywords)

def download_nlp_paper(conference: str, year: int, keywords: Optional[str] = None,
                       savedir: Optional[str] = None, poolnum: int = 8) -> None:
    """
    Downloads papers from the ACL Anthology website based on the conference and year.
    
    Args:
        conference (str): The conference name (e.g., 'ACL', 'EMNLP', 'NAACL').
        year (int): The year of the conference.
        keywords (Optional[str]): Keywords to filter papers by title. such as 'summarization-dialog'
        savedir (Optional[str]): Directory to save the downloaded papers. default: current path
        poolnum (int): The number of parallel download threads.
        
    Returns:
        None
    """
    conference = conference.lower()
    if savedir is None:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), f'{conference.upper()}{year}')
    if not os.path.isdir(savedir):
        os.makedirs(savedir)
    url = f'https://www.aclanthology.org/events/{conference}-{year}/'
    html = fetch_html(url)
    keywords = keywords.split('-') if keywords else None
    
    if "acl" in conference:
        categories = [f"{year}{conference}-long", f"{year}{conference}-short", 
                    f"{year}findings-{conference}"]
    else:
        categories = [f"{year}{conference}-main",  f"{year}findings-{conference}"]

    related_paper_num = 0
    available_paper_list = []
    for cat in categories:
        
        items = html.find("div", {"id": cat}).findAll("p", {'class':'align-items-stretch'})
        logging.info('{0} papers have been found in {1}'.format(len(items), cat))
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
                savedfile = os.path.join(sub_dir, filename)
                if not os.path.exists(savedfile):
                    available_paper_list.append((download_url, savedfile, title))
    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')

    with Pool(poolnum) as pool:
        status = [pool.apply_async(download, args=(item[0], item[1], item[2])) for item in available_paper_list]
        result = [res.get() for res in status]
        
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

def download_neurips_paper(year: int, keywords: Optional[str] = None,
                           savedir: Optional[str] = None, poolnum: int = 8) -> None:
    """
    Downloads papers from the neurips website based on the year.
    
    Args:
        year (int): The year of the conference.
        keywords (Optional[str]): Keywords to filter papers by title. such as 'summarization-dialog'
        savedir (Optional[str]): Directory to save the downloaded papers. default: current path
        poolnum (int): The number of parallel download threads.
        
    Returns:
        None
    """
    if savedir is None:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), f'neurips{year}')
    if not os.path.isdir(savedir):
        os.makedirs(savedir)
    url = f'https://proceedings.neurips.cc/paper_files/paper/{year}'
    html = fetch_html(url)
    keywords = keywords.split('-') if keywords else None

    
    available_paper_list = []
    items = html.find("ul", {"class": "paper-list"}).findAll("li")
    logging.info('{0} papers have been found in {1}'.format(len(items), f"neurips{year}"))
    related_paper_num = 0
    for item in items:
        info = item.find("a")
        title, paper_info = info.text, info.attrs["href"]
        paper_id = paper_info.split('/')[-1].split('-')[0]
        download_url = f'https://proceedings.neurips.cc/paper_files/paper/{year}/file/{paper_id}-Paper-Conference.pdf'
        if not keywords or is_related(title, keywords):
            related_paper_num += 1
            filename = f'[Neurips{year}] {title}.pdf'
            savedfile = os.path.join(savedir, filename)
            if not os.path.exists(savedfile):
                available_paper_list.append((download_url, savedfile, title))
    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')
    
    with Pool(poolnum) as pool:
        status = [pool.apply_async(download, args=(item[0], item[1], item[2])) for item in available_paper_list]
        result = [res.get() for res in status]
        
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

def download_icml_paper(year: int, keywords: Optional[str] = None,
                        savedir: Optional[str] = None, poolnum: int = 8) -> None:
    """
    Downloads papers from the icml website based on the year.
    
    Args:
        year (int): The year of the conference.
        keywords (Optional[str]): Keywords to filter papers by title. such as 'summarization-dialog'
        savedir (Optional[str]): Directory to save the downloaded papers. default: current path
        poolnum (int): The number of parallel download threads.
        
    Returns:
        None
    """
    if savedir is None:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), f'icml{year}')
    if not os.path.isdir(savedir):
        os.makedirs(savedir)
    url = f'https://icml.cc/Downloads/{year}'
    html = fetch_html(url)
    keywords = keywords.split('-') if keywords else None

    
    available_paper_list = []
    items = html.find("div", {"class": "list_html"}).find("ul").findAll("li")
    logging.info('{0} papers have been found in {1}'.format(len(items), f"icml{year}"))
    related_paper_num = 0
    for item in items:
        info = item.find("a")
        title = info.text
        if not keywords or is_related(title, keywords):
            related_paper_num += 1
            filename = f'[ICML{year}] {title}.pdf'
            suffix_url = info.attrs["href"]
            sub_url = f"https://icml.cc{suffix_url}"
            sub_html = fetch_html(sub_url)
            tmp_list = sub_html.find("div", {"class": "text-center"}).findAll("a")
            paper_url = [ele for ele in tmp_list if "PDF" in ele.text][0].attrs["href"]
            paper_html = fetch_html(paper_url)
            download_info = paper_html.find("div", {"id": "extras"}).findAll("li")
            download_url = [ele for ele in download_info if "Download PDF" in ele.text][0].find('a').attrs["href"]
            savedfile = os.path.join(savedir, filename)
            if not os.path.exists(savedfile):
                available_paper_list.append((download_url, savedfile, title))
    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')
    
    with Pool(poolnum) as pool:
        status = [pool.apply_async(download, args=(item[0], item[1], item[2])) for item in available_paper_list]
        result = [res.get() for res in status]
        
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

def download_iclr_paper(year: int, keywords: Optional[str] = None,
                        savedir: Optional[str] = None, poolnum: int = 8) -> None:
    """
    Downloads papers from the iclr website based on the year.
    
    Args:
        year (int): The year of the conference.
        keywords (Optional[str]): Keywords to filter papers by title. such as 'summarization-dialog'
        savedir (Optional[str]): Directory to save the downloaded papers. default: current path
        poolnum (int): The number of parallel download threads.
        
    Returns:
        None
    """
    conference = "iclr"
    if savedir is None:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), f'{conference}{year}')
    if not os.path.isdir(savedir):
        os.makedirs(savedir)
    url = f'https://iclr.cc/Conferences/{year}/Schedule'
    html = fetch_html(url)
    keywords = keywords.split('-') if keywords else None

    
    available_paper_list = []
    items = html.find("div", {"class": "row"}).findAll("div", {"onclick": True})
    logging.info('{0} papers have been found in {1}'.format(len(items), f"{conference}{year}"))
    related_paper_num = 0
    for item in items:
        try:
            title = item.find("div", {"class": "maincardBody"}).text.strip()
        except Exception as e:
            continue
        if "Workshop" in item.text: continue
        if not keywords or is_related(title, keywords):
            related_paper_num += 1
            
            filename = f'[{conference}{year}] {title}.pdf'
            openreview_url = [ele for ele in item.findAll('a') if "OpenReview" in ele.text][0].attrs["href"]  # https://openreview.net/forum?id=QUaDoIdgo0
            paper_id = openreview_url.split("?")[-1].strip()
            download_url = f"https://openreview.net/pdf?{paper_id}"
            savedfile = os.path.join(savedir, filename)
            if not os.path.exists(savedfile):
                available_paper_list.append((download_url, savedfile, title))
    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')
    
    with Pool(poolnum) as pool:
        status = [pool.apply_async(download, args=(item[0], item[1], item[2])) for item in available_paper_list]
        result = [res.get() for res in status]
        
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

def download_sigir_paper(year: int, keywords: Optional[str] = None,
                         savedir: Optional[str] = None, poolnum: int = 8,
                         driverpath: str=None, downtime: int=3) -> None:
    """
    Downloads papers from the sigir website based on the year.
    
    Args:
        year (int): The year of the conference.
        keywords (Optional[str]): Keywords to filter papers by title. such as 'summarization-dialog'
        savedir (Optional[str]): Directory to save the downloaded papers. default: current path
        poolnum (int): The number of parallel download threads.
        downtime (int): time waiting for downloading paper
        
    Returns:
        None
    """
    driver = webdriver.Chrome(driverpath)

    
    conference = "sigir"
    if savedir is None:
        savedir = os.getcwd()
    savedir = os.path.join(os.path.abspath(savedir), f'{conference}{year}')
    if not os.path.isdir(savedir):
        os.makedirs(savedir)
    # 配置Chrome的下载选项
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": savedir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True
    })
    # 启动浏览器
    pdf_download_driver = webdriver.Chrome(driverpath, options=chrome_options)
    url = f'https://sigir.org/sigir{year}/program/proceedings/'
    html = fetch_html(url)
    keywords = keywords.split('-') if keywords else None

    available_paper_list = []
    items = html.find("div", {"id": "DLcontent"}).findAll("h3")
    logging.info('{0} papers have been found in {1}'.format(len(items), f"{conference}{year}"))
    related_paper_num = 0
    for item in items:
        item_info = item.find('a')
        title = item_info.text.strip()
        if not keywords or is_related(title, keywords):
            related_paper_num += 1
            
            filename = f'[{conference}{year}] {title}.pdf'
            doi_url = item_info.attrs["href"]
            doi_html = fetch_html_by_driver(doi_url, driver)
            download_icon = doi_html.find("div", {"class": "info-panel__formats info-panel__item"}).findAll("a")[0]
            download_url = download_icon.attrs["href"]
            paper_id =download_url.split('/')[-1]
            file_name = paper_id + '.pdf' if '.pdf' not in paper_id else paper_id
            try:
                pdf_download_driver.get(download_url)
                time.sleep(downtime)
                original_file_path = os.path.join(savedir, file_name)
                os.rename(original_file_path, os.path.join(savedir, filename))
                logging.info("Saved paper '{}'".format(title))
            except Exception as e:
                logging.info("Dowload failed for paper '{}'".format(title))

    logging.info('Found {} papers related'.format(related_paper_num))
    logging.info('Start dowloading')
    
    driver.quit()
    pdf_download_driver.quit()
    return

def download_papers(conference: str, year: int, keywords: Optional[str], savedir: str, 
                    poolnum: int, driverpath: Optional[str] = None, downtime: Optional[int] = None) -> None:
    """
    根据会议类型下载相应的论文。

    :param conference: 会议名称 (例如 'acl', 'neurips', 'icml', 'iclr', 'sigir')
    :param year: 会议年份
    :param keywords: 用于筛选论文的关键字
    :param savedir: 保存文件的目录
    :param poolnum: 线程池数目
    :param driverpath: 下载 SIGIR 会议论文时需要的浏览器驱动路径 (仅适用于 'sigir')
    :param downtime: 每次下载之间的等待时间 (仅适用于 'sigir')
    :return: None
    """
    try:
        if conference in ['acl', 'emnlp', 'naacl', 'eacl']:  # 处理 NLP 相关的会议
            print(f"downloading paper in {conference} {year}...")
            download_nlp_paper(conference=conference, year=year, 
                            keywords=keywords, savedir=savedir, poolnum=poolnum)
        elif 'neurips' in conference:
            print(f"downloading paper in {conference} {year}...")
            download_neurips_paper(year=year, keywords=keywords, savedir=savedir, poolnum=poolnum)
        elif 'icml' in conference:
            print(f"downloading paper in {conference} {year}...")
            download_icml_paper(year=year, keywords=keywords, savedir=savedir, poolnum=poolnum)
        elif 'iclr' in conference:
            print(f"downloading paper in {conference} {year}...")
            download_iclr_paper(year=year, keywords=keywords, savedir=savedir, poolnum=poolnum)
        elif 'sigir' in conference:
            print(f"downloading paper in {conference} {year}...")
            download_sigir_paper(year=year, keywords=keywords, savedir=savedir, poolnum=poolnum, 
                                driverpath=driverpath, downtime=downtime)
        else:
            raise ValueError(f"Unsupported conference: {conference}")
    except Exception:
        logging.info(f"downloading {conference} {year} failed, please check it's availablity...")

# 处理 'all' 会议情况
def process_all_conferences(year: int, keywords: Optional[str], savedir: str, 
                            poolnum: int, driverpath: Optional[str], downtime: Optional[int]) -> None:
    """
    处理 'all' 情况，下载所有支持的会议的论文。

    :param year: 会议年份
    :param keywords: 用于筛选论文的关键字
    :param savedir: 保存文件的目录
    :param poolnum: 线程池数目
    :param driverpath: 下载 SIGIR 会议论文时需要的浏览器驱动路径
    :param downtime: 每次下载之间的等待时间
    :return: None
    """
    for conf in ['acl', 'emnlp', 'naacl', 'neurips', 'icml', 'iclr', 'sigir']:
        try:
            download_papers(conference=conf, year=year, keywords=keywords, 
                            savedir=savedir, poolnum=poolnum, 
                            driverpath=driverpath, downtime=downtime)
        except Exception as e:
            logging.info(f"downloading {conf} {year} failed, please check it's availablity...")

def main():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description='PaperCrawler')

    # 添加命令行参数
    parser.add_argument('--conference', type=str, help='name of AI conference, including acl* icml, iclr, neurips, sigir')  # 必选参数
    parser.add_argument('--year', type=int, help='the year of publication') 
    parser.add_argument('--keywords', type=str, help='only keep the papar contained the keywords (concatenated by -)')
    parser.add_argument('--savedir', type=str, default=None, help='dir to save paper')
    parser.add_argument('--poolnum', type=int, default=8, help='multi thread')
    parser.add_argument('--driver', type=str, default=None, help='the path of chrome driver')
    parser.add_argument('--time', type=int, default=5, help='time to wait for each download')
    args = parser.parse_args()
    print(args.keywords)
    
    conference = args.conference.lower()
    if conference == 'all':
        process_all_conferences(year=args.year, keywords=args.keywords, savedir=args.savedir, 
                                poolnum=args.poolnum, driverpath=args.driver, downtime=args.time)
    else:
        download_papers(conference=conference, year=args.year, keywords=args.keywords, 
                        savedir=args.savedir, poolnum=args.poolnum, driverpath=args.driver, downtime=args.time)

    

if __name__ == '__main__':
    # download_nlp_paper('naacl', 2024, 'summari')
    # download_nlp_paper('acl', 2024, 'generative retrieval')
    # download_neurips_paper(2023, "generative retrieval")
    # download_icml_paper(2024, 'generative')
    # download_iclr_paper(2023, 'Autonomous Driving')
    # download_sigir_paper(2023, "generative retriev")
    # download_nlp_paper("acl", 2024, "generative retriev")
    main()
    


