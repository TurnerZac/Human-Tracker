# -*- coding: utf-8 -*-
"""
Server program for Human Tracker
Any connecting ESP32-cams must capture 640x480 images


@author: Zac
"""
import socket
import threading
import numpy as np
import cv2
from collections import OrderedDict
import tkinter as tk
from PIL import Image, ImageTk

import centroidtracker as ct
import floorPlan as fp

# this class keeps track of any required information for each connected ESP32-cam
class connectedDevice:
    def __init__(self, MAC, connection):
        self.image = None
        self.PhotoImage = None
        self.personLocations = None
        self.humanTraffic = []
        self.previousObjects = OrderedDict()
        self.MAC = MAC
        self.connection = connection
        self.tracker = ct.CentroidTracker(3) # The argument is the number of frames before a tracked object is considered lost

# Global Variables
connections = [] # list of connectedDevices
connectionsLock = threading.Lock() # prevents connections from being accessed by multiple threads at the same time
listeningThreadRunning = False
handoutThreadRunning = False
workThreadRunning = False
iterator = 0 # used by the UI to cycle through cameras
plan = None # floorPlan that will be used to display where people are
roomPeopleCount = [] # used by the UI to add UI elements based on the floorPlan that gets loaded

listeningThread = threading.Thread()
handoutThread = threading.Thread()
workThread = threading.Thread()

# Constantly listens on port 25425 for new connections
# accepts any new connections
# new connections are expected to immediately send their MAC address
# new connections should only be ESP32-cams
def listen():
    print("listeningThread started")
    
    port = 25425
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.settimeout(1)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(('', port))
    listener.listen(5)
    
    global connections
    while listeningThreadRunning:
        connection = None
        try:
            connection = listener.accept()
            connection[0].settimeout(2)
        except:
            continue
        print(str(connection[1][0]) + " connected on port " + str(connection[1][1]))
        try:
            mac = connection[0].recv(65535).decode('utf-8')
        except:
            connection[0].close()
            continue
        reconnect = False
        for device in connections:
            if device.MAC == mac:
                device.connection = connection
                reconnect = True
                print(mac, " reconnected successfully")
                break
        if reconnect == False:
            device = connectedDevice(mac, connection)
            connectionsLock.acquire()
            connections.append(device)
            connectionsLock.release()
    listener.close()

# constantly listens on port 25426 for requests for the brain's IP address.
# Clients can make use of this by sending a UDP broadcast via the IP 192.168.1.255
# Message format:
#         Incoming: "brain address?"
#         Server responds: "brain address:192.168.1.xxx"
def handoutAddress():
    print("handoutThread started")
    
    IPDistributorPort = 25426
    IPDistributor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    IPDistributor.settimeout(1)
    IPDistributor.bind(('', IPDistributorPort))
    
    while(handoutThreadRunning):
        try:
            (message, clientAddress) = IPDistributor.recvfrom(100)
            if (message.decode('utf-8') == "brain address?"):
                print("Giving brain IP address to " + str(clientAddress))
                IP = socket.gethostbyname(socket.gethostname())
                message = "brain address:" + str(IP)
                print(message)
                IPDistributor.sendto(message.encode(), clientAddress)
        except:
            continue
    
    IPDistributor.close()

# Simple function used for determining if a centroid is in the left, center, or right side of an image
# image resolution is always 640x480
def getDirection(x):
    if x < 213:
        return "Left"
    elif x < 427:
        return "Middle"
    else:
        return "Right"

# detectHumans takes an image and a neural network and passes the image through the network
# the network returns everything it detects in the image
# the results are stored in connection.image of the connection that was passed to this function
# labels is simply for converting the nets numeric ouput into a word ex: 0 -> person
def detectHumans(image, net, connection):
    layerNames = net.getLayerNames()
    layerNames = [layerNames[i[0] - 1] for i in net.getUnconnectedOutLayers()]
    
    height, width = image.shape[:2]
    
    #blob is the object that the DNN will accept
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (height, width), swapRB=True, crop=False)
    net.setInput(blob)
    outputs = net.forward(layerNames)
    
    boxes = []
    confidences = []
    classIDs = []
    requiredConfidence = 0.6
    
    for output in outputs:
        for detection in output:
            scores = detection[5:]
            classID = np.argmax(scores)
            confidence = scores[classID]
            
            if confidence > requiredConfidence:
                if classID == 0: # 0 = person, we don't care about anything else that gets detected
                    box = detection[0:4] * np.array([width, height, width, height])
                    centerX, centerY, w, h = box.astype('int')
                    x = int(centerX - (w / 2))
                    y = int(centerY - (h / 2))
                    boxes.append([x, y, int(w), int(h)])
                    confidences.append(float(confidence))
                    classIDs.append(classID)
    
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, requiredConfidence, 0.3) # 0.5 = minimum required confidence, 0.3 = threshold for non Max suppresion
    
    personLocations = []
    
    if len(idxs) > 0:
        for i in idxs.flatten():
            x, y, w, h = boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3]
            
            color = (0, 255, 0)
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            text = "Person" + " " + str(round(confidences[i],4))
            cv2.putText(image, text, (x, y -5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            centerX = x + w/2
            centerY = y + h/2
            personLocations.append((x, y, x + w, y + h))
    
    connectionsLock.acquire()
    #connection.image = image.copy() # OpenCV uses BGR arrays for images
    connection.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) # most other things use RGB arrays so it must be converted
    connection.personLocations = personLocations.copy()
    
    # Centroid tracking starts
    rects = []
    for box in personLocations:
        rects.append(np.array(box))
    try:
        objects = connection.tracker.update(rects)
        
        for (object, centroid) in connection.previousObjects.items():   # Check if any people disappeared
            if object not in objects:
                direction = getDirection(centroid[0])
                print("Object ", object, " exited ", direction, " at ", centroid)
                connection.humanTraffic.append(("exit", direction))
        for (object, centroid) in objects.items():                      # Check if any people appeared
            if object not in connection.previousObjects:
                direction = getDirection(centroid[0])
                print("Object ", object, " entered ", direction, " at ", centroid)
                connection.humanTraffic.append(("enter", direction))
        connection.previousObjects = objects.copy()
        
        for (objectID, centroid) in objects.items():
            cv2.putText(connection.image, "ID " + str(objectID), (centroid[0] - 10, centroid[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(connection.image, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)
        # Centroid tracking finishes
    except:
        print("tracker crashed")
    connectionsLock.release()

# work first initializes the YOLO deep neural network, this is done once because it takes some time to setup
# it then continuously loops through the list of active connections and asks for an image
# when it receives an image it spawns a new thread that will detect any people in the image
# it then asks for the next image and waits for the previous thread to finish, this is done because receiving the image and detecting people both take over 100ms 
#   so it makes sense to run them in parallel
# it then applies a centoid tracker to the post detection image which gives an id number to any detection and keeps track of where they move
# when a person disappears it reports where they were last seen
def work():
    print("workThread started")
    
    global connections
    
    net = cv2.dnn.readNetFromDarknet('YOLO/yolov4.cfg', 'YOLO/yolov4.weights')
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
    
    detectionThread = threading.Thread()
    
    while workThreadRunning:
        if len(connections) == 0:
            continue
        for connection in connections:
            if connection.connection == None:
                continue
            try:
                #print("Requesting image from: ", connection.MAC)
                connection.connection[0].send("send image".encode("utf-8"))
            except:
                print(connection.MAC, " connection closed because request failed")
                connection.connection[0].close()
                connection.connection = None
                continue
            imageData = None
            imageComplete = False
            connectionDied = False
            
            while imageComplete == False:
                try:
                    dataReceived = connection.connection[0].recv(8192)
                except:
                    print(connection.MAC, " timed out")
                    connection.connection[0].close()
                    connection.connection = None
                    connectionDied = True
                    break
                if len(dataReceived) == 0:
                    print(connection.MAC, " connection closed because no data received")
                    connectionDied = True
                    connection.connection[0].close()
                    connection.connection = None
                    break
                if imageData == None:
                    imageData = dataReceived
                else:
                    imageData += dataReceived
                for i in range(len(dataReceived)):
                        if dataReceived[i] == 255:
                            if i != len(dataReceived) - 1:
                                if dataReceived[i + 1] == 217:
                                    imageComplete = True
                                    
            #print("image captured from: ", connection.MAC)
                                    
            if detectionThread.is_alive():
                detectionThread.join()
            
            if connectionDied:
                continue
            
            if type(imageData) != None:
                if len(imageData):
                    image = cv2.imdecode(np.frombuffer(imageData, np.uint8), cv2.IMREAD_UNCHANGED)
                    if type(image) != type(None):
                        detectionThread = threading.Thread(target=detectHumans, args=(image, net, connection)) # detectionThread created
                        detectionThread.start()
            
    if detectionThread.is_alive():
        detectionThread.join()



"""
User Interface stuff starts here
"""

# UI function, toggles the listeningThread and updates the UI to show that it is running
def toggleListeningThread():
    global listeningThread
    global listeningThreadRunning
    if listeningThreadRunning == False:
        listeningThreadRunning = True
        listeningThread = threading.Thread(target=listen, daemon=True)
        listeningThread.start()
        toggleListener["text"] = "Listening Thread: On"
    else:
        listeningThreadRunning = False
        if listeningThread.is_alive():
            print("waiting for listeningThread to join")
            listeningThread.join()
            print("listeningThread joined")
        else:
            print("listeningThread not running")
        toggleListener["text"] = "Listening Thread: Off"
    
# UI function, toggles the handoutThread and updates the UI to show that it is running
def toggleHandoutThread():
    global handoutThread
    global handoutThreadRunning
    if handoutThreadRunning == False:
        handoutThreadRunning = True
        handoutThread = threading.Thread(target=handoutAddress, daemon=True)
        handoutThread.start()
        toggleHandouter["text"] = "Handout Thread: On"
    else:
        handoutThreadRunning = False
        if handoutThread.is_alive():
            print("waiting for handoutThread to join")
            handoutThread.join()
            print("handoutThread joined")
        else:
            print("handoutThread not running")
        toggleHandouter["text"] = "Handout Thread: Off"

# UI function, toggles the workThread and updates the UI to show that it is running
def toggleWorkThread():
    global workThread
    global workThreadRunning
    if workThreadRunning == False:
        workThreadRunning = True
        workThread = threading.Thread(target=work, daemon=True)
        workThread.start()
        toggleWorker["text"] = "Work Thread: On"
    else:
        workThreadRunning = False
        if workThread.is_alive():
            print("waiting for workThread to join")
            workThread.join()
            print("workThread joined")
        else:
            print("workThread not running")
        toggleWorker["text"] = "Work Thread: Off"

# UI function, selects the previous available camera
def cycleLeft():
    global connections
    global iterator
    if len(connections) > 0:
        if iterator > 0:
            iterator -= 1
    elif len(connections) < 1:
        iterator = 0
    iteratorText["text"] = "Iterator: " + str(iterator)

# UI function, selects the next available camera
def cycleRight():
    global connections
    global iterator
    if len(connections) > 0:
        if iterator < len(connections) - 1:
            iterator += 1
    elif len(connections) < 1:
        iterator = 0
    iteratorText["text"] = "Iterator: " + str(iterator)

# UI function, updates the displayed image for the camera that is selected
def refreshImage():
    global connections
    global iterator
    if len(connections) > 0:
        connectionsLock.acquire()
        image = connections[iterator].image
        if type(image) != type(None):
            connections[iterator].PhotoImage = ImageTk.PhotoImage(master=canvas, image=Image.fromarray(image))
            connectionsLock.release()
            MACaddress["text"] = connections[iterator].MAC
            canvas.create_image(0, 0, image=connections[iterator].PhotoImage, anchor="nw")
        else:
            connectionsLock.release()

# UI function, updates the UI with the current number of connected ESP32-cams
def updateNumConnections():
    global connections
    numConnections["text"] = "Connections: " + str(len(connections))

# Reads from a list of instructions in each connection that instructs the floorPlan on the movement of people
def movePeople(plan):
    global connections
    connectionsLock.acquire()
    for connection in connections:
        for room in plan.rooms:
            if connection.MAC == plan.rooms[room].camera:
                while len(connection.humanTraffic) > 0:
                    traffic = connection.humanTraffic.pop(0)
                    if traffic[0] == "enter":
                        plan.rooms[room].movePerson(traffic[1], True)
                    elif traffic[0] == "exit":
                        plan.rooms[room].movePerson(traffic[1], False)
                break
    connectionsLock.release()

# UI function, updates the UI with the current amount of people in each room
def printPeopleCount(plan, roomPeopleCount):
    total = 0
    i = 0
    for room in plan.rooms:
        roomPeopleCount[i][1]["text"] = str(plan.rooms[room].peopleCount)
        i += 1
        total += plan.rooms[room].peopleCount
    totalPeopleCount["text"] = str(total)

# UI function, Cleans up everything when the "X" button is pressed
def quitProgram():
    global listeningThreadRunning
    global handoutThreadRunning
    global workThreadRunning
    global connections
    
    listeningThreadRunning = False
    handoutThreadRunning = False
    workThreadRunning = False
    
    if listeningThread.is_alive():
        print("waiting for listeningThread to join")
        listeningThread.join()
        print("listeningThread joined")
    
    if handoutThread.is_alive():
        print("waiting for handoutThread to join")
        handoutThread.join()
        print("handoutThread joined")
    
    if workThread.is_alive():
        print("waiting for workThread to join")
        workThread.join()
        print("workThread joined")
    
    print("Closing all connections")
    for connection in connections:
        if connection.connection != None:
            connection.connection[0].close()
    connections.clear()
    
    print("Program finished")
    
    global running
    running = False
    
    UI.destroy()

# UI function, tries to create a floorPlan from the file specified in the inputBox
def getFloorPlan():
    global plan
    global roomPeopleCount
    filePath = inputBox.get()
    if plan is None:
        plan = fp.createFloorPlanFromFile(filePath)
        
        if plan is not None:
            for room in plan.rooms:
                roomPeopleCount.append([tk.Label(statisticsFrame, text=plan.rooms[room].roomName + ": "), tk.Label(statisticsFrame, text="0")])
            
            roomRow = 1
            for room in roomPeopleCount:
                room[0].grid(row=roomRow, column=0, sticky="W")
                room[1].grid(row=roomRow, column=1, sticky="E")
                roomRow += 1
    else:
        print("floorPlan already created")
    







UI = tk.Tk()
UI.title("Human Tracker")
UI.protocol("WM_DELETE_WINDOW", quitProgram)

topFrame = tk.Frame(UI)
topFrame.grid(row=0, column=1, sticky="E")

enterFloorPlan = tk.Label(topFrame, text="Enter Floor Plan file path: ")
enterFloorPlan.grid(row=0, column=0)

inputBox = tk.Entry(topFrame, width=70)
inputBox.grid(row=0, column=1, sticky="W")

inputButton = tk.Button(topFrame, text="Select", command=getFloorPlan)
inputButton.grid(row=0, column=2, sticky="W")


leftFrame = tk.Frame(UI, width=120, height=480)
leftFrame.grid(row=1, column=0, sticky="N")
leftFrame.grid_propagate(0)

leftTopFrame = tk.Frame(leftFrame)
leftTopFrame.grid(row=0, column=0, sticky="NESW")

numConnections = tk.Label(leftTopFrame, text="Connections: " + str(len(connections)))
numConnections.grid(row=0, column=0, sticky="NESW")


leftMiddleFrame = tk.Frame(leftFrame)
leftMiddleFrame.grid(row=1, column=0, sticky="NESW")

toggleListener = tk.Button(leftMiddleFrame, text="Listening Thread: Off", command=toggleListeningThread)
toggleListener.grid(row=0, column=0, sticky="NESW")

toggleHandouter = tk.Button(leftMiddleFrame, text="Handout Thread: Off", command=toggleHandoutThread)
toggleHandouter.grid(row=1, column=0, sticky="NESW")

toggleWorker = tk.Button(leftMiddleFrame, text="Work Thread: Off", command=toggleWorkThread)
toggleWorker.grid(row=2, column=0, sticky="NESW")


leftBottomFrame = tk.Frame(UI)
leftBottomFrame.grid(row=2, column=0, sticky="S")

MACaddress = tk.Label(leftBottomFrame, text="")
MACaddress.grid(row=0, column=0, columnspan=2, sticky="NESW")

iteratorText = tk.Label(leftBottomFrame, text="Iterator: " + str(iterator))
iteratorText.grid(row=1, column=0, columnspan=2, sticky="NESW")

leftButton = tk.Button(leftBottomFrame, text=" < ", command=cycleLeft)
leftButton.grid(row=2, column=0, sticky="E")
        
rightButton = tk.Button(leftBottomFrame, text=" > ", command=cycleRight)
rightButton.grid(row=2, column=1, sticky="W")


rightFrame = tk.Frame(UI, width=640, height=480)
rightFrame.grid(row=1, column=1)

canvas = tk.Canvas(rightFrame, width=640, height=480)
canvas.grid(row=0, column=0)


statisticsFrame = tk.Frame(leftMiddleFrame)
statisticsFrame.grid(row=3, column=0)

totalPeople = tk.Label(statisticsFrame, text="Total people: ")
totalPeople.grid(row=0, column=0, sticky="W")

totalPeopleCount = tk.Label(statisticsFrame, text="0")
totalPeopleCount.grid(row=0, column=1, sticky="E")

running = True
while running:
    updateNumConnections()
    refreshImage()
    if plan is not None:
        movePeople(plan)
        printPeopleCount(plan, roomPeopleCount)
    UI.update()







