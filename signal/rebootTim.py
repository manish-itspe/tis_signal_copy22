import urllib2, base64

request = urllib2.Request("http://192.168.75.202/reboot.php")
base64string = base64.encodestring('%s:%s' % ("admin", "itspe")).replace('\n', '')
request.add_header("Authorization", "Basic %s" % base64string)
result = urllib2.urlopen(request)
