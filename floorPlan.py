# -*- coding: utf-8 -*-
"""
Defines the floorPlan and room objects

when saved to a file, the format is as follows:
    id roomName "name of room"
    id leftRoom "name of left room"
    id middleRoom "name of middle room"
    id rightRoom "name of right room"
    id camera "name of camera"
    id direction "N or E or S or W"
    
id is just a number that is determined by the order that the rooms are added to the file,
each room has a unique id.
if any saved variables do not exist then they will simple be marked as "none".

@author: Zac
"""

# room object stores information about this room and points to connected rooms
# a room can have up to 3 doors, "Left", "Middle", and "Right"
# camera will be mounted on the wall opposite of middle door, the camera is also facing the middle door
# direction is the direction the camera is facing
class room:
    # creates a room, the only required argument is the roomName, the rest can be filled in later
    def __init__(self, roomName, leftRoom=None, middleRoom=None, rightRoom=None, camera=None, direction="N"):
        self.roomName = roomName
        self.leftRoom = leftRoom
        self.middleRoom = middleRoom
        self.rightRoom = rightRoom
        self.camera = camera
        if direction == "N" or direction == "S" or direction == "E" or direction == "W":
            self.direction = direction
        else:
            self.direction = "N"
            print("direction must be \"N\" or \"E\" or \"S\" or \"W\", defaulting to \"N\"")
        self.peopleCount = 0
    
    # increases the number of people in the room
    def add(self, num):
        self.peopleCount += num
    
    # decreases the number of people in the room
    # prevents the peopleCount from going below 0
    def sub(self, num):
        self.peopleCount -= num
        if self.peopleCount < 0:
            self.peopleCount = 0
    
    # returns a list of connected rooms
    def getConnections(self):
        c = []
        if self.leftRoom is not None:
            c.append(self.leftRoom)
        if self.middleRoom is not None:
            c.append(self.middleRoom)
        if self.rightRoom is not None:
            c.append(self.rightRoom)
        return c
    
    # adjusts the peopleCount in this room and the specified room depending on direction of traffic
    # direction = "Left", "Middle" or "Right", this refers to the rooms the person coming from/going to
    # enter = True or False, True means the person entered this room, False means they exited this room
    def movePerson(self, direction, enter):
        if direction == "Left":
            if enter == True:
                self.add(1)
                if self.leftRoom is not None:
                    self.leftRoom.sub(1)
            else:
                self.sub(1)
                if self.leftRoom is not None:
                    self.leftRoom.add(1)
            return True
        elif direction == "Right":
            if enter == True:
                self.add(1)
                if self.rightRoom is not None:
                    self.rightRoom.sub(1)
            else:
                self.sub(1)
                if self.rightRoom is not None:
                    self.rightRoom.add(1)
            return True
        elif direction == "Middle":
            if enter == True:
                self.add(1)
                if self.middleRoom is not None:
                    self.middleRoom.sub(1)
            else:
                self.sub(1)
                if self.middleRoom is not None:
                    self.middleRoom.add(1)
            return True
        else:
            print("invalid direction")
            return False

# stores a dictionary of rooms and has a few functions for accessing data
class floorPlan:
    # creates a floorPlan, the firstRoom can optionally be created here
    # if the firstRoom is not created then the floorPlan can either be filled in through the createFloorPlanFromFile function
    # or a firstRoom may be created with the firstRoom function
    def __init__(self, roomName=None, camera=None, direction="N"):
        self.firstRoom = roomName
        self.rooms = {}
        if roomName is None:
            return
        r = room(roomName, camera=camera, direction=direction)
        self.rooms[roomName] = r
    
    # single use function that allows an initial room to be added if one was not created by the constructor
    def firstRoom(self, roomName, leftRoom=None, middleRoom=None, rightRoom=None, camera=None, direction="N"):
        if len(self.rooms) > 0:
            print("this function may only be used for adding the first room")
            return False
        else:
            self.firstRoom = roomName
            r = room(roomName, leftRoom=leftRoom, middleRoom=middleRoom, rightRoom=rightRoom, camera=camera, direction=direction)
            self.rooms[roomName] = r
    
    # adds a room to this floorPlan and makes the room connections two way
    # roomName = "name of the new room"
    # roomToConnect = "room the new room will connect to"
    # roomSide = "Left", "Middle", or "Right, the side of the new room that connects to roomToConnect
    # roomToConnectSide = "Left", "Middle", or "Right, the side of roomToConnect that the new room will connect to
    def addRoom(self, roomName, roomSide, roomToConnect, roomToConnectSide):
        if roomToConnect in self.rooms:
            if roomName in self.rooms:
                print(roomName, " already exists")
                return False
            r = room(roomName)
            if roomSide == "Left":
                r.leftRoom = self.rooms[roomToConnect]
            elif roomSide == "Middle":
                r.middleRoom = self.rooms[roomToConnect]
            elif roomSide == "Right":
                r.rightRoom = self.rooms[roomToConnect]
            else:
                print("invalid roomSide")
                return False
            
            self.rooms[roomName] = r
            
            if roomToConnectSide == "Left":
                if self.rooms[roomToConnect].leftRoom is None:
                    self.rooms[roomToConnect].leftRoom = self.rooms[roomName]
                else:
                    print (roomToConnect, " leftRoom already filled")
                    self.rooms.pop(roomName)
                    return False
            elif roomToConnectSide == "Middle":
                if self.rooms[roomToConnect].middleRoom is None:
                    self.rooms[roomToConnect].middleRoom = self.rooms[roomName]
                else:
                    print (roomToConnect, " middleRoom already filled")
                    self.rooms.pop(roomName)
                    return False
            elif roomToConnectSide == "Right":
                if self.rooms[roomToConnect].rightRoom is None:
                    self.rooms[roomToConnect].rightRoom = self.rooms[roomName]
                else:
                    print (roomToConnect, " rightRoom already filled")
                    self.rooms.pop(roomName)
                    return False
            else:
                print("invalid roomToConnectSide")
                self.rooms.pop(roomName)
                return False
            
            return True
        else:
            print(roomToConnect, " not in this floorplan")
            return False
    
    # prints out a tree that displays each room and its position
    def printRooms(self, r=None, num=0, pr=None):
        if r is None:
            if self.firstRoom is not None:
                r = self.rooms[self.firstRoom]
            else:
                print("no rooms available")
                return
        text = ""
        for x in range(num):
            text += "-"
        print(text, r.roomName)
        for i in r.getConnections():
            if i is not pr:
                self.printRooms(i, num+1, r)

# accepts a floorPlan object and saves it to a .floorplan file
# will not save an empty floorPlan
def saveFloorPlanToFile(floorPlan, fileName):
    if fileName[-10:] != ".floorplan":
        fileName += ".floorplan"
    if len(floorPlan.rooms) == 0:
        print("can't save empty floorplan")
        return
    try:
        f = open(fileName, "w")
        x = 0
        for i in floorPlan.rooms:
            head = str(x) + " "
            text = head + "roomName " + floorPlan.rooms[i].roomName + "\n"
            text += head + "leftRoom "
            if floorPlan.rooms[i].leftRoom is not None:
                text += floorPlan.rooms[i].leftRoom.roomName + "\n"
            else:
                text += "none\n"
            text += head + "middleRoom "
            if floorPlan.rooms[i].middleRoom is not None:
                text += floorPlan.rooms[i].middleRoom.roomName + "\n"
            else:
                text += "none\n"
            text += head + "rightRoom "
            if floorPlan.rooms[i].rightRoom is not None:
                text += floorPlan.rooms[i].rightRoom.roomName + "\n"
            else:
                text += "none\n"
            text += head + "camera "
            if floorPlan.rooms[i].camera is not None:
                text += floorPlan.rooms[i].camera + "\n"
            else:
                text += "none\n"
            text += head + "direction " + floorPlan.rooms[i].direction + "\n"
            f.write(text)
            x += 1
        f.close()
    except:
        print("Failed to save to file")
        f.close()

# reads a .floorplan file and builds a floorPlan object from that data
# returns a floorPlan object if successful or None if it fails
def createFloorPlanFromFile(fileName):
    if fileName[-10:] != ".floorplan":
        print("file type must be .floorplan")
        return None
    try:
        data = []
        f = open(fileName, "r")
        EOF = False
        while EOF == False:
            text = f.readline()
            if text == "":
                EOF = True
                break
            splitText = text.split()
            if len(splitText) > 3:
                splitText = [splitText[0], splitText[1], " ".join(splitText[2:])]
            data.append(splitText)
        f.close()
        
        dataRooms = []
        for i in range(int(len(data) / 6)):
            dataRooms.append(data[i * 6:i * 6 + 6])
        
        fp = floorPlan()
        fp.firstRoom = dataRooms[0][0][2]
        for i in dataRooms:
            r = room(roomName=i[0][2], camera=i[4][2], direction=i[5][2])
            fp.rooms[i[0][2]] = r
        
        for i in range(len(fp.rooms)):
            if dataRooms[i][1][2] != "none":
                fp.rooms[dataRooms[i][0][2]].leftRoom = fp.rooms[dataRooms[i][1][2]]
            else:
                fp.rooms[dataRooms[i][0][2]].leftRoom = None
            if dataRooms[i][2][2] != "none":
                fp.rooms[dataRooms[i][0][2]].middleRoom = fp.rooms[dataRooms[i][2][2]]
            else:
                fp.rooms[dataRooms[i][0][2]].middleRoom = None
            if dataRooms[i][3][2] != "none":
                fp.rooms[dataRooms[i][0][2]].rightRoom = fp.rooms[dataRooms[i][3][2]]
            else:
                fp.rooms[dataRooms[i][0][2]].rightRoom = None
        
        return fp
    except:
        print("failed to create floorPlan from file")
        try:
            f.close()
        except:
            print("file does not exist")
        return None
    

# example on how to use everything
"""
plan = floorPlan("one")

plan.addRoom("two", "Right", "one", "Left")
plan.addRoom("three", "Left", "one", "Right")

plan.addRoom("two-1", "Right", "two", "Left")
plan.addRoom("two-2", "Right", "two", "Middle")

plan.addRoom("three-1", "Right", "three", "Right")
plan.addRoom("three-2", "Right", "three", "Middle")

plan.addRoom("two-1-1", "Right", "two-1", "Left")
plan.addRoom("two-1-2", "Right", "two-1", "Middle")

plan.addRoom("three", "Middle", "one", "Middle")

plan.addRoom("three-1", "Left", "three", "Left")

plan.printRooms()


saveFloorPlanToFile(plan, "test_floorPlan")


test = createFloorPlanFromFile("test_floorPlan.floorplan")
"""