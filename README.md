# Human-Tracker

This is my Human Tracker program, the main program "Human Tracker.py" requires OpenCV and a graphics card.
The camera program is designed for the AIthinker ESP32-cam, WiFi credentials are hard coded so they must be filled in before uploading to the device.
"floorPlan.py" is a file I wrote for creating and manipulating the floorPlan class which is used in "Human Tracker.py".
I didn't write "centroidTracker.py" the website I got it from is found in the first line of the file, it is included here because "Human Tracker.py" requires it in order to function.
"my_floor_plan.floorplan" is just there to serve as an example for what a floorplan should look like, a floorplan can either be written by hand or created with the functions included in "floorPlan.py".
