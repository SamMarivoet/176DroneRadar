The work was done on Docker. 
The main idea is : pick up data from a website,  giving infos for all the airplaines around. The data are collected each X sec,
transformed into a JSON file, then send towards a specific directory. 


1) pick up data from a feeder website : Opensky is used
2)  adsb-dev-collector contains a python script (main.py) which will open the website, collect the infos, create a JSON file for each airplane, and send it out on a specific directory (adsb-dev-uploader). Actually, we don't have any directory because no access yet to a database. So we only plot the received data in adsb-pipeline/data. 
3) 

example of JSON file : 
-----------------------------------------
msg_id	"e383e44e79887623678d9ae9"
source	"opensky"
icao	"46b826"
flight	"AEE6003"
country	"Greece"
ts_unix	1760433315
lat	50.6545
lon	4.8988
alt	4724.4
spd	203.99
heading	125.45
vr	13.98
alt_geom	4953
squawk	"0106"
on_ground	0
-------------------------------------------
NB : 
The timestamp ts_unix is in Unix time, which counts the number of seconds since January 1, 1970, 00:00:00 UTC.
