# papercrawler
Python script to download conference paper automatically, including the conferences and journals listed in https://aclweb.org/anthology/, such as ACL/EMNLP/NAACL/COLING/CL.

# Requirement
python 3.6

# Example
To download summarization-related papers in ACL2020
```python
download_nlp_paper('acl', 2020, 'summari')
```
If some papers fail to download, just run this script again.

# command

You can download all the conferences by: 
``` python
python papercrawl.py --conference all --year 2024 --keywords "keywords one-keywords two" --driver /path/to/chromedriver
``` 
or download one conference (only sigir need chrome driver):
``` python
python papercrawl.py --conference acl --year 2024 --keywords "keywords one-keywords two"
``` 
