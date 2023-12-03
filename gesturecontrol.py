import cv2
import time, requests
import numpy as np
import handtracker as htm
import math
import pyfirmata2
from time import strftime
from pyfirmata2 import Arduino, util, STRING_DATA

################################
wCam, hCam = 640, 480
################################

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0
detector = htm.handDetector(detectionCon=0.7)

board = pyfirmata2.Arduino('COM3')
ledPin = board.get_pin('d:6:p')

it = util.Iterator(board)
it.start()

board.analog[3].enable_reporting()
board.analog[4].enable_reporting()

def msg( text ):
    if text:
        board.send_sysex( STRING_DATA, util.str_to_two_byte_iter( text ) )
    else:
        board.send_sysex( STRING_DATA, util.str_to_two_byte_iter( ' ' ) )

def map_range(x, in_min, in_max, out_min, out_max): 
  return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

def drawAndCalculateBrightness(indX, indY, thumbX, thumbY):
    cx, cy = (indX + thumbX) // 2, (indY + thumbY) // 2
    cv2.circle(img, (indX, indY), 15, (255, 0, 255), cv2.FILLED)
    cv2.circle(img, (thumbX, thumbY), 15, (255, 0, 255), cv2.FILLED)
    cv2.line(img, (indX, indY), (thumbX, thumbY), (255, 0, 255), 3)
    cv2.circle(img, (cx, cy), 15, (255, 0, 255), cv2.FILLED)
    length = math.hypot(indX - thumbX, indY - thumbY)

    brightness = np.interp(length, [20, 350], [0, 1])

    if length < 50:
        cv2.circle(img, (cx, cy), 15, (0, 255, 0), cv2.FILLED)
        brightness = 0

    return brightness
        

x = False
while True:
    success, img = cap.read()
    img = detector.findHands(img)
    lmList = detector.findPosition(img, draw=False)
    time.sleep(0.1)
    match x:
            case True:
                msg1 = "Temp: " + str(map_range(board.analog[3].read(), 0, 1.0, 20, 80)) + " C"
                msg2 = "Humidity: " + str(map_range(board.analog[4].read(), 0, 1.0, 0, 50)) + "%"

                msg(msg1)
                msg(msg2)

            case False:
                ctime = strftime('   %I:%M:%S %p')
                msg(ctime)
                cdate = strftime(' %a %b %d %Y')
                msg(cdate)

    if len(lmList) != 0:
        baseX, baseY = lmList[0][1], lmList[0][2]
        knuckleX, knuckleY = lmList[5][1], lmList[5][2]
        thumbX, thumbY = lmList[4][1], lmList[4][2]
        indX, indY = lmList[8][1], lmList[8][2]
        midX, midY = lmList[12][1], lmList[12][2]
        ringX, ringY = lmList[16][1], lmList[16][2]
        midknklX, midknklY = lmList[9][1], lmList[9][2]
        ringknklX, ringknklY = lmList[13][1], lmList[13][2]
        if indY < knuckleY and midY < midknklY and indX > midX:
            cv2.putText(img, f'Display Control', (40, 50), cv2.FONT_HERSHEY_SIMPLEX,
                1, (177, 232, 0), 2)
            if(indX > 500):
                x = True
                continue
            elif(indX < 200):
                x = False
                continue
        elif knuckleX > baseX and indY < thumbY and indX <= thumbX:
            cv2.putText(img, f'LED Control', (40, 50), cv2.FONT_HERSHEY_SIMPLEX,
                1, (177, 232, 0), 2)
            
            brightness = drawAndCalculateBrightness(indX, indY, thumbX, thumbY)

            print(brightness)
            ledPin.write(brightness)
        
    
    cv2.imshow("Img", img)
    cv2.waitKey(1)

