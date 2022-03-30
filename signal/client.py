# from websocket import create_connection

# def sendSocketMessage(message):
#        ws = create_connection("ws://localhost:9090/chat")
#        ws.send(message)
#        ws.close()


import paho.mqtt.publish as publish

def sendSocketMessage(site_id,message):
	site_id = "/" + str(site_id)
	if message[-4:] == "pass":
		publish.single(site_id, message[:-4], hostname="10.116.0.36")
