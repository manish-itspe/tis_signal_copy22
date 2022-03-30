import smtplib
from config import *

def mailer(to, subject, content):
	gmail_user = GMAIL_USER
	gmail_pwd = GMAIL_PASS
	smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
	smtpserver.ehlo()
	smtpserver.starttls()
	smtpserver.login(gmail_user, gmail_pwd)
	msg = "\r\n".join(["From: "+gmail_user+"","To: "+", ".join(to)+"","Subject: "+subject+"","",content])
	smtpserver.sendmail(gmail_user, to, msg)
	smtpserver.close()

# to = ['rajesh.samudrala@itspe.co.in', 'parag.raipuria@itspe.co.in']
# subject = "Test Mail"
# content = "Why Me"
# mailer(to, subject, content)