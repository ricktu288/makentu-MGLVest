# USAGE
# python real_time_object_detection.py --prototxt MobileNetSSD_deploy.prototxt.txt --model MobileNetSSD_deploy.caffemodel

# import the necessary packages
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import imutils
import time
import cv2
import serial
import serial.tools.list_ports
import time
import _thread

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", default='MobileNetSSD_deploy.prototxt.txt',
	help="path to Caffe 'deploy' prototxt file")
ap.add_argument("-m", "--model", default='MobileNetSSD_deploy.caffemodel',
	help="path to Caffe pre-trained model")
ap.add_argument("-c", "--confidence", type=float, default=0,
	help="minimum probability to filter weak detections")
args = vars(ap.parse_args())

# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]

COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
	
OBJ_MAX = 30
OBJ_MAX_DIST = 1000
OBJ_LIFE = 3

MOTOR_N = 10

WIDTH=400
WIDTH_DETECT=300

CONF_TRIG = 0.7
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
					#print('add', i, self.objs[i].center, self.objs[i].strength, CLASSES[idx])
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
				

				
				
# load our serialized model from disk
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

# initialize the video stream, allow the cammera sensor to warmup,
# and initialize the FPS counter
print("[INFO] starting video stream...")
vs = VideoStream(src=1).start()
VS2 = 1
if VS2:
	vs2 = VideoStream(src=2).start()


time.sleep(2.0)
fps = FPS().start()
objs = Objs()



def run_motor():
	while True:
		objs.toVibe()
		time.sleep(0.05)
		
_thread.start_new_thread(run_motor, ())

# loop over the frames from the video stream
while True:
	
	objs.lifeTick()
	
	# grab the frame from the threaded video stream and resize it
	# to have a maximum width of 400 pixels
	frame = vs.read()
	#overlay = vs.read()
	frame = imutils.resize(frame, width=WIDTH)
	#overlay = imutils.resize(overlay, width=400)
	# grab the frame dimensions and convert it to a blob
	(h, w) = frame.shape[:2]
	blob = cv2.dnn.blobFromImage(cv2.resize(frame, (WIDTH_DETECT, WIDTH_DETECT)),
		0.007843, (WIDTH_DETECT, WIDTH_DETECT), 127.5)

	# pass the blob through the network and obtain the detections and
	# predictions
	net.setInput(blob)
	detections = net.forward()

	
	
	# loop over the detections
	for i in np.arange(0, detections.shape[2]):
		# extract the confidence (i.e., probability) associated with
		# the prediction
		confidence = detections[0, 0, i, 2]
		if (confidence == 0):
			continue
		
		# filter out weak detections by ensuring the `confidence` is
		# greater than the minimum confidence
		#if confidence > args["confidence"]:
		# extract the index of the class label from the
		# `detections`, then compute the (x, y)-coordinates of
		# the bounding box for the object
		idx = int(detections[0, 0, i, 1])
		box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
		(startX, startY, endX, endY) = box.astype("int")

		# draw the prediction on the frame
		label = "{}: {:.2f}%".format(CLASSES[idx],
			confidence * 100)
		cv2.rectangle(frame, (startX, startY), (endX, endY),
			COLORS[idx], 2)
		y = startY - 15 if startY - 15 > 15 else startY + 15
		cv2.putText(frame, label, (startX, y),
			cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)
		
		objs.testDetection((startX, startY),(endX, endY), idx, confidence)
	
	cv2.imshow("Frame", frame)
	
	if VS2:
		# grab the frame from the threaded video stream and resize it
		# to have a maximum width of 400 pixels
		frame2 = vs2.read()
		#overlay = vs.read()
		frame2 = imutils.resize(frame2, width=WIDTH)
		#overlay = imutils.resize(overlay, width=400)
		# grab the frame dimensions and convert it to a blob
		(h, w) = frame2.shape[:2]
		blob = cv2.dnn.blobFromImage(cv2.resize(frame2, (WIDTH_DETECT, WIDTH_DETECT)),
			0.007843, (WIDTH_DETECT, WIDTH_DETECT), 127.5)

		# pass the blob through the network and obtain the detections and
		# predictions
		net.setInput(blob)
		detections = net.forward()

		
		
		# loop over the detections
		for i in np.arange(0, detections.shape[2]):
			# extract the confidence (i.e., probability) associated with
			# the prediction
			confidence = detections[0, 0, i, 2]
			if (confidence == 0):
				continue
			
			# filter out weak detections by ensuring the `confidence` is
			# greater than the minimum confidence
			#if confidence > args["confidence"]:
			# extract the index of the class label from the
			# `detections`, then compute the (x, y)-coordinates of
			# the bounding box for the object
			idx = int(detections[0, 0, i, 1])
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")

			# draw the prediction on the frame
			label = "{}: {:.2f}%".format(CLASSES[idx],
				confidence * 100)
			cv2.rectangle(frame2, (startX, startY), (endX, endY),
				COLORS[idx], 2)
			y = startY - 15 if startY - 15 > 15 else startY + 15
			cv2.putText(frame2, label, (startX, y),
				cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)
			
			objs.testDetection((startX + WIDTH, startY),(endX + WIDTH, endY), idx, confidence)
		cv2.imshow("Frame2", frame2)
	
	
	#cv2.addWeighted(overlay, confidence, frame, 1 - confidence,	0, frame)
	# show the output frame
	
	key = cv2.waitKey(1) & 0xFF
	
	
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break

	# update the FPS counter
	fps.update()

# stop the timer and display FPS information
fps.stop()
print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()

if (SERIAL):
	ser.close()             # close port
