# importing libraries

import cv2
import time, requests
import numpy as np
import handtracker as htm
import math
import pyfirmata2
from time import strftime
from pyfirmata2 import Arduino, util, STRING_DATA

# defining window dimensions(the one that you see when the program runs)
wCam, hCam = 640, 480

# initalizes webcamera feed
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

# stores hand detector as an object
detector = htm.handDetector(detectionCon=0.7)

# creates an object to store the Arduino board information
board = pyfirmata2.Arduino('COM3')
# creates an object representing the LED pin on the board
ledPin = board.get_pin('d:6:p')

# creates an iterator that acts as a tick
it = util.Iterator(board)
it.start()

# allows analog pins 3 and 4 to be read by the python file
board.analog[3].enable_reporting()
board.analog[4].enable_reporting()

# function for printing messages to the LCD
def msg( text ):
    if text: # if the string contains text, print it to the LCD
        board.send_sysex( STRING_DATA, util.str_to_two_byte_iter( text ) )
    else: # if the string is empty, print nothing to the LCD
        board.send_sysex( STRING_DATA, util.str_to_two_byte_iter( ' ' ) )

# draws circles on the index fingertip, thumbtip, the line between them, and the center of that line
def drawAndCalculateBrightness(indX, indY, thumbX, thumbY):
    cx, cy = (indX + thumbX) // 2, (indY + thumbY) // 2 # calculting midpoint of the line

    # drawing circles and line
    cv2.circle(img, (indX, indY), 15, (255, 0, 255), cv2.FILLED) 
    cv2.circle(img, (thumbX, thumbY), 15, (255, 0, 255), cv2.FILLED)
    cv2.line(img, (indX, indY), (thumbX, thumbY), (255, 0, 255), 3)
    cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)

    # calculating the length of the distance between index fingertip and thumb tip
    length = math.hypot(indX - thumbX, indY - thumbY)

    # storing brightness by mapping the distance in pixels to a range 0-1, similar to map() in arduino
    brightness = np.interp(length, [20, 350], [0, 1])

    # handles if the fingers are close or touching(when the LED should be off)
    if length < 50:
        cv2.circle(img, (cx, cy), 15, (0, 255, 0), cv2.FILLED) # colors circle green to denote the light is off
        brightness = 0 

    # returns the brightness that the LED should be
    return brightness
        
# this will show the time and date when the program is first run(you will see how later)
x = False

# loops infinitely
while True:

    # reads the webcam video feed
    success, img = cap.read()

    # updates the camera image to contain the hand tracker
    img = detector.findHands(img)

    # creates a 2d array of coordinates for the positions of landmarks on the hands
    lmList = detector.findPosition(img, draw=False)

    # the python equivalent of delay() but in seconds instead of milliseconds
    time.sleep(0.1)
    
    # a match case structure works similar to an if/else statement but depends on the value of the variable being matched
    match x:
            # if x is True
            case True:

                # creates two strings to be displayed on the LCD, one for temperature and the other for Humidity
                msg1 = "Temp: " + str(np.interp(board.analog[3].read(), 0, 1.0, 20, 80)) + " C"
                msg2 = "Humidity: " + str(np.interp(board.analog[4].read(), 0, 1.0, 0, 50)) + "%"
                
                # displays the strings on the LCD
                msg(msg1)
                msg(msg2)
            
            # if x is False(this is what we set x to before the loop)
            case False:

                # get current time in hours, minutes, seconds, and am/pm
                ctime = strftime('   %I:%M:%S %p')
                # display the current time on the LCD screen
                msg(ctime)

                # get current date as a day of the week, month, day, and year 
                cdate = strftime(' %a %b %d %Y')
                # display the current date on the LCD screen
                msg(cdate)

    # this condition ensures that there are hands present and that the landmarks are being tracked
    if len(lmList) != 0:
        baseX, baseY = lmList[0][1], lmList[0][2] # x and y coords of the base of the hand
        knuckleX, knuckleY = lmList[5][1], lmList[5][2] # x and y coords of the index knuckle
        thumbX, thumbY = lmList[4][1], lmList[4][2] # x and y coords of the tip of the thumb
        indX, indY = lmList[8][1], lmList[8][2] # x and y coords for the tip of the index
        midX, midY = lmList[12][1], lmList[12][2] # x and y coords for the tip of the middle finger
        midknklX, midknklY = lmList[9][1], lmList[9][2] # x and y coords for the middle finger knuckle

        if indY < knuckleY and midY < midknklY and indX > midX: # if the index fingertip is higher than the knuckle(if the finger is pointing up),
                                                                # the middle fingertip is higher than the knuckle(pointing up),
                                                                # and the index finger is further right than the middle finger(the right hand is being used)
            
            cv2.putText(img, f'Display Control', (40, 50), cv2.FONT_HERSHEY_SIMPLEX,
                1, (177, 232, 0), 2) # prints on screen that the system is in display control mode
            
            if(indX > 500): # if the index and middle fingers move to the left, x becomes true
                x = True
                continue # starts the loop over from the beginning, updating the LCD with the new value of x

            elif(indX < 200): # if the index and middle fingers move to the right, x becomes false
                x = False
                continue # starts the loop over from the beginning, updating the LCD with the new value of x

        elif knuckleX > baseX and indY < thumbY and indX <= thumbX: # if the index knuckle is to the right of the base of the hand(the hand is facing upwards),
                                                                    # the index fingertip is above the thumbtip(the index and thumb are facing upright),
                                                                    # and the index finger is either to the left of the thumb or right above it(the right hand is used)
                                                                    # (if the right hand is in an L shape with the index and thumb)
            
            cv2.putText(img, f'LED Control', (40, 50), cv2.FONT_HERSHEY_SIMPLEX,
                1, (177, 232, 0), 2) # tells the user on screen that the system is in LED control mode
            
            brightness = drawAndCalculateBrightness(indX, indY, thumbX, thumbY) # stores the brightness of the LED based on the function above
                                                                                #(how far apart the index and thumb tips are)

            #print(brightness) for testing purposes
            ledPin.write(brightness) # writes the brightness to the LED pin, similar to analogWrite() in arduino
        
    
    cv2.imshow("Img", img) # displays the webcam feed with the hand tracking on it in a window on screen
    cv2.waitKey(1) # sets the key that breaks the loop

