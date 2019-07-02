import feedparser
import json
import boto3
import dateutil.parser as parser
import time
import datetime
import re

# https://www.us-cert.gov/ncas/alerts/TA15-119A

urlSecurityWeek = "https://feeds.feedburner.com/securityweek"
url2 = "https://tools.cisco.com/security/center/psirtrss20/AlertRSS.xml"
url3 = 'https://nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-modified.json.zip'

# processSecurityWeek()

"""
zip_ref = zipfile.ZipFile("nvdcve-1.0-modified.json.zip", 'r')
zip_ref.extractall(".")
zip_ref.close()

score = 0
cve_id = ""
cve_des = ""
publishedDate = ""

with open('nvdcve-1.0-modified.json') as f:
  data = json.load(f)
  for cve in data["CVE_Items"]:
      cve_id = cve["cve"]["CVE_data_meta"]["ID"]
      cve_publishedDate = cve["publishedDate"]
      if "impact" in cve:
          if "baseMetricV3" in cve["impact"]:
              score = cve["impact"]["baseMetricV3"]["cvssV3"]["baseScore"]
      else:
          score = 0
      cve_des = cve["cve"]["description"]["description_data"][0]["value"]
      print("<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>".format(cve_id,score,cve_publishedDate))
"""

def processSCMagazine():
    url = "https://www.securitymagazine.com/rss/15"
    d = feedparser.parse(url)
    for new in d['entries']:
        date = parser.parse(new['published'])
        addDatabaseNews("SCMagazine",new['title'], new['link'],date.isoformat())

def processFeedburnerFeeds():
    processFeedburnerFeed("SecurityWeek")
    processFeedburnerFeed("TheHackersNews")

def processFeedburnerFeed(feed):
    url = "https://feeds.feedburner.com/"+feed
    d = feedparser.parse(url)
    for new in d['entries']:
        date = parser.parse(new['published'])
        addDatabaseNews(feed,new['title'], new['links'][0]['href'],date.isoformat())

def processSecurityNow():
    url = "http://feeds.twit.tv/sn.xml"
    parsedFeed = feedparser.parse(url)
    episode = parsedFeed['entries'][0]
    print(episode['title'])
    print(episode['published'])
    return (episode['content'][0]['value'].split("<p><strong>Hosts:")[0])


def generateSANSWebcast():
    url = "https://www.sans.org/webcasts/rss"

    parsedFeed = feedparser.parse(url)
    webcasst = parsedFeed['entries'][0:5]

    html = """<div class="page-header">
        <h1>SANS Upcoming Webcasts</h1>
        </div>
      <div class="row">
        <div class="col-md-12">
          <table class="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Title</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
    """
    for episode in webcasst:
        html += "<tr><td>"+episode['published']+"</td>\n"
        html += "<td>"+episode['title'].split(" - ")[0]+"</td>\n"
        html += "<td>"+episode['description'].replace("{{!","").replace("}}","")+"</td></tr>\n"

    html += """
            </tbody>
            </table>
            </div>
            </div>
            </div><!-- /.col-sm-6 -->

    """
    return html

def processStormDailyPodcast():
    url = "https://isc.sans.edu/dailypodcast.xml"

    parsedFeed = feedparser.parse(url)
    podcasts = parsedFeed['entries'][0:6]
    mp3 = podcasts[0]['id']

    table = """      <audio controls="controls">"""
    table += "       <source src=\""+mp3+"\" type=\"audio/mp3\" />"
    table += "       Votre navigateur n'est pas compatible </audio>"

    table += """<table class="table">
       <thead>
         <tr>
           <th>Episode</th>
           <th>Content</th>
         </tr>
       </thead>
       <tbody>
    """

    for episode in podcasts:
        table += "<tr><td>"+episode['title'].split("ISC StormCast for ")[1]+"</td>\n"
        table += "<td>"+episode['subtitle'].replace(";","<br>").split("@")[0]+"</td></tr>\n"

    table += """
            </tbody>
            </table>
    """
    return table


def addDatabaseNews(source, title, link, date):
    client = boto3.client('dynamodb')
    client.put_item(TableName='news',
        Item={
            "source":{
                "S":source
            },
            "title":{
                "S":title
            },
            "link":{
                "S":link
            },
            "date":{
                "S":date
            }
        })
    time.sleep(1)


def uploadIndex():
    s3_resource = boto3.resource('s3')
    s3_resource.meta.client.upload_file(
    Filename="index.html", Bucket="securityadvisor",
    Key="index.html")
    response = s3_resource.meta.client.put_object_acl(ACL='public-read',
    Bucket="securityadvisor",
    Key="index.html")
    response = s3_resource.meta.client.put_public_access_block(Bucket='securityadvisor',
    PublicAccessBlockConfiguration={
        'RestrictPublicBuckets': False
    })


def generateNewsTable():
    newsHTML = """<div class="page-header">
        <h1>News</h1>
        </div>
      <div class="row">
        <div class="col-md-12">
          <table class="table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th>News</th>
              </tr>
            </thead>
            <tbody>
    """

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('news')
    response = table.scan()

    for i in response['Items']:
        i['date'] = parser.parse(i['date'])
        i['date'] = int(round(i['date'].timestamp()))

    sorted_list = (sorted(response['Items'], key = lambda i: i['date'],reverse=True))

    for i in sorted_list[:20]:
        print(time.ctime(i['date'])+"  "+i['source']+"  "+i['title'])

        newsHTML += "<tr><td>"+time.ctime(i['date'])+"</td>\n"
        newsHTML += "<td>"+i['source']+"</td>\n"
        newsHTML += "<td><a href=\""+i['link']+"\">"+i['title']+"</a></td></tr>\n"

    return newsHTML


def generatePodcastsPanels():

    podcastsPanelsHTML = ""
    htmlHeadPodcasts="""<div class="page-header">
                          <h1>Podcasts</h1>
                        </div>
                        <div class="row">
    """
    htmlHeadPodcastsSecurityNow = """<div class="col-sm-6">
            <div class="panel panel-default">
              <div class="panel-heading">
                <h3 class="panel-title">Security Now</h3>
              </div>
              <div class="panel-body">
    """
    htmlHeadPodcastsStormDailyPodcast = """
        <div class="col-sm-6">
            <div class="panel panel-default">
              <div class="panel-heading">
                <h3 class="panel-title">SANS Podcasts</h3>
              </div>
              <div class="panel-body">
    """

    contentSecurityNow = """
    <iframe width="504" height="283" src="https://www.youtube.com/embed/JuQSgzj3k6A"
    frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
    </iframe>
    """
    contentSecurityNow += processSecurityNow()

    htmlbottomEachPodcasts="""
               </div>
             </div>
           </div><!-- /.col-sm-6 -->
    """

    podcastsPanelsHTML += htmlHeadPodcasts
    podcastsPanelsHTML += htmlHeadPodcastsSecurityNow
    podcastsPanelsHTML += contentSecurityNow
    podcastsPanelsHTML += htmlbottomEachPodcasts
    podcastsPanelsHTML += htmlHeadPodcastsStormDailyPodcast
    podcastsPanelsHTML += processStormDailyPodcast()
    podcastsPanelsHTML += htmlbottomEachPodcasts

    return podcastsPanelsHTML


def main():

    html = ""
    headHTML = """<!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="description" content="">
        <meta name="author" content="">

        <title>Theme Template for Bootstrap</title>

        <!-- Bootstrap core CSS -->
        <link href="css/bootstrap.min.css" rel="stylesheet">
        <!-- Bootstrap theme -->
        <link href="css/bootstrap-theme.min.css" rel="stylesheet">

        <!-- Custom styles for this template -->
        <link href="css/theme.css" rel="stylesheet">

        <!-- IE10 viewport hack for Surface/desktop Windows 8 bug -->
        <script src="js/ie10-viewport-bug-workaround.js"></script>

        <!-- HTML5 shim and Respond.js IE8 support of HTML5 elements and media queries -->
        <!--[if lt IE 9]>
          <script src="https://oss.maxcdn.com/html5shiv/3.7.2/html5shiv.min.js"></script>
          <script src="https://oss.maxcdn.com/respond/1.4.2/respond.min.js"></script>
        <![endif]-->
      </head>

      <body role="document">

        <!-- Fixed navbar -->
        <div class="navbar navbar-inverse navbar-fixed-top" role="navigation">
          <div class="container">
            <div id="navbar" class="navbar-collapse collapse">
              <ul class="nav navbar-nav">
                <li class="active"><a href="#">Home</a></li>
                <li><a href="#about">News</a></li>
                <li><a href="#contact">Podcasts</a></li>
              </ul>
            </div><!--/.nav-collapse -->
          </div>
        </div>

        <div class="container theme-showcase" role="main">

          <!-- Main jumbotron for a primary marketing message or call to action -->
    """
    bottomNewsHTML = """
                </tbody>
              </table>
            </div>
    		</div>
    """
    bottomHTML="""
        </div>
        </div>
        </div> <!-- /container -->
        <!-- Bootstrap core JavaScript
        ================================================== -->
        <!-- Placed at the end of the document so the pages load faster -->
        <script src="../bootstrap-without-jquery.min.js"></script>
      </body>
    </html>
    """

    processSCMagazine()
    processFeedburnerFeeds()

    securityNow = processSecurityNow()
    processStormDailyPodcast()

    html += headHTML
    html += generatePodcastsPanels()
    html += generateNewsTable()
    html += bottomNewsHTML
    html += generateSANSWebcast()
    html += bottomHTML

    file = open("index.html","w")
    file.write(html)
    file.close()

    uploadIndex()


main()

#
