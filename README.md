404 Founder
-----------------------

404 founder is a simple multi-thread tool to check if there are resources in a page return "404 not found".    
All 404 will be logged to "founder_report.log"."parser.log" will record some debug info.    

**All page link that returns content-type "text/html" will be parsed further and checked.**    

Have fun:)

##Usage

```python
python 404founder.py localhost  # check from the "http:/localhost/"
```

Script will start from "/" to test urls found in html document recursively.

##support tags
+ a
+ link
+ script
+ tags with "ng-include" property

