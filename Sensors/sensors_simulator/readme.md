IDEA : 

2 type of sensors : 
1) RADAR : 5km range, will report the position of the detected drones in its area.
   An icon of the sensor will always be present on the map.
   When a drone is reported, we see " radar_A (1)", indicating that one drone is currently flying in the area.
   when the user clicks on the icon, he will see a list with the coordinates of the different drones present in the area in a scrolling list.
   When click on coordinates : an icon "drone" appears on the map on the indicated coordinates.
   
3)  CAMERA : range = visual range of the camera, take a picture (optical or/and infrared) of the detected aerial vehicle (imagine IA recognize it and take a picture),
    then when you click on the logo of the camera on the map, you can see the drones detected in the last 24hours (picture + time) in a scrolling list.


IMPLEMENTATION : 

FEED : 
A function will create apparition at random time and random coordinates --> each apparition = a JSON file. 
for RADAR : JSON file contains : position, altitude, speed (via doppler effect), time reporting
for CAMERA JSON file contains : picture, time reporting

DATABASE : 
JSON files will be sent to the database and stocked in different sources for the 2 type of JSON files and repartition in the different radars/cameras already registred  on the database.

PLOT ON THE MAP : 

Same as for the other feed.  Just need to implement the small IDEA described above.



   
NB : No feed available for these kind of sensors, so the feed will be artifical (create drones randomly).
