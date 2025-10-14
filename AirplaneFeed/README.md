The work was done on Docker. 
The main idea is : pick up data from a website which  gives infos for all the airplaines around (250NM around the RMA in this case). The data are collected each X sec,
transformed into a JSON file, then send towards a specific directory. 


1) pick up data from a feeder website : Opensky is used
2)  adsb-dev-collector contains a python script (main.py) which will open the website, collect the infos, create a JSON file for each airplane, and send it out on a specific directory (adsb-dev-uploader). Actually, we don't have any directory because no access yet to a database. So we only plot the received data (adsb-pipeline/data).
NB: to send the JSON files to the database --> change in adsb-dev-uploader

EXAMPLE OF JSON FILE  : 

msg_id	"e383e44e79887623678d9ae9" // 
source	"opensky" //
icao	"46b826" //  
flight	"AEE6003" // 
counTry	"Greece"  // 
ts_unix	1760433315  //
lat	50.6545  //
lon	4.8988 //
alt	4724.4  //
spd	203.99  //
heading	125.45 //
vr	13.98 //
alt_geom	4953  //
squawk	"0106"  //
on_ground	0  //

NB : 

The timestamp ts_unix is in Unix time, which counts the number of seconds since January 1, 1970, 00:00:00 UTC.

1) msg_id: "e383e44e79887623678d9ae9"

This is a unique identifier for the message sent by the aircraft. Think of it like a “message serial number.”

2) source: "opensky"

Indicates where the data came from, in this case the OpenSky Network.

3) icao: "46b826"

The ICAO 24-bit address of the aircraft.

This is a unique identifier for the airplane, assigned by the International Civil Aviation Organization.

4) flight: "AEE6003"

The flight number as reported by the aircraft or airline.

Here it’s flight Aegean Airlines 6003.

5) country: "Greece"

Country of registration of the aircraft.

6) ts_unix: 1760433315

The timestamp in Unix time (seconds since 1970-01-01 UTC) when this data point was recorded.

You can convert it to human-readable time:

1760433315 → Thursday, October 14, 2025, 18:55:15 UTC

7) lat: 50.6545

Latitude of the aircraft at the recorded timestamp in decimal degrees.

8) lon: 4.8988

Longitude of the aircraft at the recorded timestamp in decimal degrees.

9) alt: 4724.4

Barometric altitude in meters (altitude reported by the aircraft’s pressure sensor, corrected for standard atmosphere).

10) spd: 203.99

Ground speed in meters per second.

This is the speed over the ground, not airspeed.

11) heading: 125.45

Direction of motion in degrees from north (clockwise).

Here, the plane is flying roughly southeast.

12) vr: 13.98

Vertical rate in meters per second.

Positive values indicate climbing, negative values indicate descending.

So here, the plane is climbing at ~14 m/s.

13) alt_geom: 4953

Geometric altitude in meters (altitude above mean sea level from GPS).

Slightly different from alt because barometric and geometric altitudes can differ.

14) squawk: "0106"

Transponder code assigned by air traffic control (ATC).

Helps controllers identify the aircraft on radar.

15) on_ground: 0

Boolean: 0 = airborne, 1 = on the ground.





