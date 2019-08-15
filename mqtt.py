import paho.mqtt.client as paho
import time


#Callbacks
def on_connect(client, userdata, flags, rc):
    print("Connected with code:" + str(rc))
    client.subscribe("gpshackerman/#")


def on_message(client, userdata, msg):
    #print(str(msg.payload.decode("utf-8")))
    lat, long = str(msg.payload.decode("utf-8")).split(",")
    print("lat", lat)
    print("long", long)

client = paho.Client()
client.on_connect = on_connect
client.on_message = on_message

client.username_pw_set("ovsntzkc","2qbB51uKR_PT")
client.connect("m24.cloudmqtt.com", 12882, 60)

#client.loop_forever()
client.loop_start()
time.sleep(1)
while True:
    client.publish("Tutorial", "alpha")
    print("Message sent")
    time.sleep(15)

client.loop_stop()
client.disconnect()


#mqtt
"""broker_address = "iot.eclipse.org"
broker_portno = 1883
client = paho.Client()
client.username_pw_set("Eder", "hackerman")
client.connect(broker_address, broker_portno, 60)
client.username_pw_set("ovsntzkc","2qbB51uKR_PT")
client.connect("m24.cloudmqtt.com", 12882, 60)"""

"""broker_address = "iot.eclipse.org"
broker_portno = 1883
broker_topic =  "gpshackerman"
client = paho.Client()
client.username_pw_set("Eder","hackerman")
client.connect(broker_address, broker_portno, 60)
coords = client.subscribe("gpshackerman")
print("coords", coords)
client.loop_forever()"""
#client.publish("gpshackerman", payload=json_string, qos=0, retain=True)
"""mqtt
                    mqtt_string = str(latitude) + ", " + str(longitude)
                    print("mqtt", mqtt_string)
                    client.publish("gpshackerman", payload=mqtt_string, qos=0, retain=True)"""