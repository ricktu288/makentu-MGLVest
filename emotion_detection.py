import argparse
from scipy.misc import imsave
import cognitive_face as CF
import cv2
from sys import platform
import timeit
import requests
import serial
import serial.tools.list_ports

# disable warning
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor", "Anger", "Contempt", "Disgust", 
    "Fear", "Happiness", "Neutral", "Sadness", "Surprise"]

OBJ_MAX = 30
OBJ_MAX_DIST = 1000
OBJ_LIFE = 2

MOTOR_N = 10

WIDTH=400
WIDTH_DETECT=300

CONF_TRIG = 0.2
CONF_MIN = 0.1

SERIAL = len(list(serial.tools.list_ports.comports())) > 0
if (SERIAL):
	device = list(serial.tools.list_ports.comports())[0].device
	print(device)
	ser = serial.Serial(device, baudrate=115200)  # open serial port
	print(ser.name)         # check which port was really used


class Obj:
	def __init__(self, start, end, idx):
		self.update(start, end)
		self.idx = idx
	def lifeTick(self):
		self.life = self.life - 1
		return self.life > 0
	def distanceTo(self, start, end):
		return (start[0]-self.start[0])**2 + (start[1]-self.start[1])**2 + (end[0]-self.end[0])**2 + (end[1]-self.end[1])**2
	def update(self, start, end):
		self.start = start;
		self.end = end;
		self.center = (start[0] + end[0]) / 2
		self.strength = end[0] - start[0]
		self.life = OBJ_LIFE
		
class Objs:
	def __init__(self):
		self.objs = [None] * OBJ_MAX
	def lifeTick(self):
		#print('tick')
		for i, obj in enumerate(self.objs):
			if (not (obj is None)):
				if (not obj.lifeTick()):
					#print('delete', i)
					if (SERIAL):
						ser.write(b'd,%d\n'%i)
					self.objs[i] = None
	def testDetection(self, start, end, idx, conf):
		for i, obj in enumerate(self.objs):
			if (not (obj is None)):
				if (obj.distanceTo(start, end) < OBJ_MAX_DIST and self.objs[i].idx == idx and conf > CONF_MIN and self.objs[i].life < OBJ_LIFE):
					self.objs[i].update(start, end)
					#print('update', i, self.objs[i].center, self.objs[i].strength)
					if (SERIAL):
						ser.write(b'u,%d,%d,%d\n'%(i, self.objs[i].center, self.objs[i].strength))
					return
		if (conf > CONF_TRIG):
			for i, obj in enumerate(self.objs):
				if obj is None:
					self.objs[i] = Obj(start, end, idx)
					#print('a,%d,%d,%d,%d\n'%(i, self.objs[i].center, self.objs[i].strength, idx))
					if (SERIAL):
						ser.write(b'a,%d,%d,%d,%d\n'%(i, self.objs[i].center, self.objs[i].strength, idx))
					return
	def toVibe(self):
		strs = ['_'] * MOTOR_N
		for i, obj in enumerate(self.objs):
			if (not (obj is None)):
				motorid = int(obj.center * MOTOR_N / WIDTH / 2)
				
				strs[motorid] = CLASSES[obj.idx][0]
				
		str = ''
		for c in strs:
			str += c
		print(str)
				

				

objs = Objs()

def recognize(key):

  CF.Key.set(key) # set API key
  CF.BaseUrl.set('https://southeastasia.api.cognitive.microsoft.com/face/v1.0')

  while True:
    objs.lifeTick()
    start = timeit.default_timer()
    cap = cv2.VideoCapture(1)
    ret, frame = cap.read()
    if platform.startswith('win'): # for windows we don't display video due to camera issues
      cap.release()
    imsave('tmp.png', frame)

    result = CF.face.detect('tmp.png', attributes='age,gender,emotion,smile')
    stop = timeit.default_timer()
    print(stop - start)
    try:
      for face in result:
        # faceID = face['faceId']
        gender = face['faceAttributes']['gender']
        age = face['faceAttributes']['age']
        emotion_happy = face['faceAttributes']['smile']
        rect = face['faceRectangle']
        top = rect['top']
        left = rect['left']
        fattr = face['faceAttributes']
        disp = {'gender': fattr['gender'],
                     'age': fattr['age']}
        disp.update(fattr['emotion'])
        # print(disp)
		
        print(gender, age, emotion_happy, top, left, disp)
        #print(fattr['emotion'])
        # if platform == 'darwin': # for mac we display the video, face bounding box, age & gender
        
        confidence = 0
        idx = -1
        for i, (k, conf) in enumerate(fattr['emotion'].items()):
            #print(i, k, conf)
            if conf > confidence:
                confidence = conf
                idx = i + 21
        
        print(CLASSES[idx])
        
        width = rect['width']

        height = rect['height']
        # cv2.rectangle(frame, (left, top), (left + width, top + height),
        #                 (0, 255, 0), 2)
        # cv2.putText(frame, '{},{}'.format(gender, int(age)), (left, top),
        #               cv2.FONT_HERSHEY_SIMPLEX, 2, 255)
        # cv2.imshow('Demo', frame)
        objs.testDetection((left, top),(left + width, top + height), idx, confidence)
      objs.toVibe()
    except not result:
      continue

    except KeyboardInterrupt:
      cap.release()
      cv2.destroyAllWindows()
    

parser = argparse.ArgumentParser()
parser.add_argument('-k','--key', required=True, type=str, help='key for face api')
args = parser.parse_args()
recognize(args.key)