import face_recognition
import cv2
import os
import numpy as np
import time
import pymysql
import socket


# open server -------------------------------------
HOST = '0.0.0.0'
PORT = 8003


# MySQL Connection -----------------------------------------------------
db_flag = True#False

if db_flag:
    dbconn = pymysql.connect(host='59.26.77.236', user='root', password='0000', db='iotDB', charset='utf8', )
    curs = dbconn.cursor(pymysql.cursors.DictCursor)


# Input Video---------------------------------------------------------------
#cap = cv2.VideoCapture("test_input/test7.mp4")      # kimYoonSeok3
#cap = cv2.VideoCapture("http://192.168.0.5:8090/?action=stream")   # real-time 
cap = cv2.VideoCapture("http://59.26.77.236:8090/?action=stream")   

# Adjust permittion process --------------------------
cnt_permit = 0
cnt_notpermit = 0
    
class FaceRecog():
    def __init__(self):
        print('--- Program_Start ---')
        
    def recog_Person(self, grayframe):
        ## Choice CascadeClassifier - Body
        body_cascade = cv2.CascadeClassifier()
        body_cascade.load('data/haarcascade_fullbody.xml')
        
        ## Detect Body
        body = body_cascade.detectMultiScale(grayframe, 1.1, 3, 0, (30, 30))
        
        return body
        
    def recog_Face(self, grayframe):
        ## Choice Cascade Classifier - Face
        face_cascade = cv2.CascadeClassifier()
        face_cascade.load('data/haarcascade_frontalface_default.xml')    # Front Face
        
        ### Detect_Face
        faces = face_cascade.detectMultiScale(grayframe, 1.1, 3, 0, (30, 30))

        return faces
        
    def check_Permission(self, permitFlag):
        ## Variable About Face
        permit_face_encodings = []
        permit_face_names = []
        input_face_locations = []
        input_face_encodings = []
        process_this_frame = True
        
        global cnt_permit
        global cnt_notpermit
        
        # Read Permitted Person
        dirname = 'permission'
        files = os.listdir(dirname)
        for filename in files:
            name, ext = os.path.splitext(filename)
            if ext == '.jpg':
                permit_face_names.append(name)
                pathname = os.path.join(dirname, filename)
                img = face_recognition.load_image_file(pathname)
                face_encoding = face_recognition.face_encodings(img)[0]
                permit_face_encodings.append(face_encoding)
        
        # Resize Frame
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        
        # Convert BGR->RGB
        rgb_small_frame = small_frame[:, :, ::-1]

        # Detect Permitted Person
        if process_this_frame:
            input_face_locations = face_recognition.face_locations(rgb_small_frame)
            input_face_encodings = face_recognition.face_encodings(rgb_small_frame, input_face_locations)
            
            for face_encoding in input_face_encodings:        
                distances = face_recognition.face_distance(permit_face_encodings, face_encoding)
                min_value = min(distances)

                ## Current Time
                now = time.localtime()
                nowTime = "%04d/%02d/%02d %02d:%02d:%02d" % (now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min, now.tm_sec)

                ## Permitted or Not
                if min_value < 0.4:  #0.5
                    permitFlag = True

                    print("cnt-permit: " + str(cnt_permit))
                    if cnt_permit == 3:
                        print(nowTime + ' -- Permitted')
                        
                        ## insert data - permit
                        if db_flag:
                            sql = """insert into access(time,permit)
                                     values (%s, %s)"""
                            curs.execute(sql, (nowTime, 'Permitted'))
                            dbconn.commit()
                        
                        cnt_permit = 0
                    else:
                        cnt_permit += 1 
                else:
                    print("cnt-notpermit: " + str(cnt_notpermit))
                    if cnt_notpermit == 5:
                        print(nowTime + ' -- Not-permitted!')
                        
                        ## insert data - not permit
                        if db_flag:
                            sql = """insert into access(time,permit)
                                     values (%s, %s)"""
                            curs.execute(sql, (nowTime, 'Not-permitted'))
                            dbconn.commit()
                        
                        cnt_notpermit = 0
                    else:
                        cnt_notpermit += 1
                                    
        process_this_frame = not process_this_frame
        
        return permitFlag, input_face_locations


face_recog = FaceRecog()

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    s.bind((HOST, PORT))
    s.listen(1)
    
    conn, addr = s.accept()    
    with conn:        
        while True:
            permitFlag = False

            ## Read Frame
            ret,frame = cap.read()

            ## Convert Grayscale
            grayframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            grayframe = cv2.equalizeHist(grayframe)             # more clear

            # Recognize Person -------------------------------------------------------
            #body = face_recog.recog_Person(grayframe)
            body = None
            
            ## Recognize Face --------------------------------------------------------
            faces = face_recog.recog_Face(grayframe)
            
            ## Check Permission ------------------------------------------------------
            permitFlag, input_face_locations = face_recog.check_Permission(permitFlag)

            a=()
            ## Draw onframe
            if faces is not a:   
                if permitFlag:
                    ### open door
                    conn.send('1'.encode())
                    
                    ### Draw around Face - Permission
                    for (top, right, bottom, left) in input_face_locations:
                        top *= 4
                        right *= 4
                        bottom *= 4
                        left *= 4
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        cv2.putText(frame, "Permitted", (left+6, bottom-6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), 1)
                else:
                    ### Not open door
                    conn.send('0'.encode())
                    
                    ### Draw around Face - No-Permission
                    for (x,y,w,h) in faces:
                        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,0,255),3, 4, 0)
                        cv2.putText(frame, "Unknown(F)", (x+6, y+h-6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), 1)
            else:  
                print('no person')
                conn.send('0'.encode())
                #faces = face_recog.recog_Face(grayframe)
                continue
                ### Draw around Body
                #for (x,y,w,h) in body:
                #    cv2.rectangle(frame,(x,y),(x+w,y+h),(0,0,255),3, 4, 0)
                #    cv2.putText(frame, "Unknown(B)", (x+6, y+h-6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255,255,255), 1)
             
            ## Show_Result
            #cv2.imshow("Frame", frame)
            
            ## Wait Key input
            key = cv2.waitKey(1) & 0xFF
            
            ## input 'q' then exit
            if key == ord("q"):  break
            
        print('--- Program_Finished ---')
        cv2.destroyAllWindows()
        
    s.close()
    
