import smtplib
from email.message import EmailMessage
def sendmail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)     #Secure Sockets Layer
    server.login('vidyasrilagudu@gmail.com','tkmx zqyu worh qxgh')
    msg=EmailMessage()
    msg['FROM']='vidyasrilagudu@gmail.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    server.close()