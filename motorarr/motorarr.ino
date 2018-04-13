#define nMotor 10
#define objListLen 30

#define sleepMs (tickMs/nCycle/nLevel)
#define nCycle 10
#define nLevel 10
#define tickMs 100 //0.1sec

#define maxPos 800

///pattern definitions///

const int patNone[] = {
  0, -1
};
const int patPerson[] = {
  7, 8, 9, 10, 10, 10, 9, 8, 7, 7, 
  6, 6, 5, 5, -1
};
const int patCar[] = {
  10, 8, 2, -1 //saw
};
const int patMBike[] = {
  10, 8, 2, -1 //saw
};
const int patBike[] = {
  8, 8, 8, 8, 8, 3, 3, 3, 3, 3, -1
};
const int patAni[]{
  8, 5, 3, 2, 2, 1, 1, -1 //70rpm beat rate
};
const int patCommon[] = {
  5, 8, 5, 0, 0, 0, 0, 0, 0, 0, -1 //pulse every 1sec
};
const int patternAnger[] = {
  10, 1, 5, 8, 0, 7, 9, 3, 2, -1
};
const int patternContempt[] = {
  10, 6, 4, 3, 2, -1
};
const int patternDisgust[] = {
  5, 7, 9, 10, 9, 7, 5, 3, 3, 3, 3, -1
};
const int patternFear[] = {
  8, 4, 4, -1
};
const int patternHappiness[] = {
  5, 8, 10, 8, 6, 4, 3, -1
};
const int patternNeutral[] = {
  7, 8, 9, 10, 10, 10, 9, 8, 7, 7, 
  6, 6, 5, 5, -1
};
const int patternSadness[] = {
  8, 7, 5, 5, 6  -1
};
const int patternSurprise[] = {
  10, 2, 8, 2, 8, 2, 3, 8, 3, 2,
  3, 3, 3, -1
};

const int patternPrio[] = {
  0, 0, 4, 0, 0, 0, 0, 4, 2, 1, 0, 1, 2, 0, 4, 3, 0, 0, 1, 0, 1, 3, 3, 3, 3, 3, 3, 3, 3
};
const int *patternPtr[] = {
  patNone, //background, 0
  patNone, //aeroplane
  patBike, //bicycle
  patNone, //bird
  patNone, //boat
  patNone, //bottle, 5
  patNone, //bus
  patCar, //car
  patAni, //cat
  patCommon, //chair
  patNone, //cow, 10
  patCommon, //diningtable
  patAni, //dog
  patNone, //horse
  patMBike, //motorbike
  patPerson, //person, 15
  patNone, //pottedplant
  patNone, //sheep
  patCommon, //sofa
  patNone, //train
  patCommon, //twmonitor, 20
  patternAnger,
  patternContempt,
  patternDisgust,
  patternFear,
  patternHappiness, //25
  patternNeutral,
  patternSadness,
  patternSurprise
};

typedef struct object_s {
  int pos;
  int strength;
  int type = -1;
  int phase;
} object;
object objList[objListLen];

int motorPin[nMotor] = {3, 4, 5, 6, 7, 8, 9, 10, 11, 12};
int motorLevel[nMotor];
int motorPrio[nMotor]; //"Z-buffer like" array

/////code/////

void setup() {
  Serial.begin(115200);
  for(int i = 0; i < 10; i++){
    pinMode(motorPin[i], OUTPUT);
  }
}

void loop() {
  int tick = 0;
  while(1){ //tick loop

    ///update object list if available///
    
    //format:
    //a,id,pos(0~400),size,type
    //u,...,size
    //d,id
    while(Serial.available()){
      char action = Serial.read();
      Serial.read();//skip comma
      int id = Serial.parseInt();
      Serial.read();//skip comma
        if(action == 'd'){
          objList[id].type = -1;
          continue;
        }
      objList[id].pos = Serial.parseInt();
      Serial.read();//comma
      objList[id].strength = Serial.parseInt();
      Serial.read();//comma
        if(action == 'u'){
          continue;
        }
      objList[id].type = Serial.parseInt();
      Serial.read();//skip newline
        if(action == 'a'){
          objList[id].phase = 0;
        }
    }
    
    ///calculate level per motor///

    for(int i = 0; i < nMotor; i++){
      motorPrio[i] = 0;
      motorLevel[i] = 0;
    }
    for(int i = 0; i < objListLen; i++){
      if(objList[i].type < 0){//no obj
        continue;
      }
      /*
       * smoothing algorithm insanly fucking hard to implement
       * 
      int leftMotor = ((2*nMotor*objList[i])/maxPos - 1)/2;
      temp
      int rightPerc = 100*(objList[i]+maxPos/2/nMotor)%(maxPos/nMotor)/(maxPos/nMotor);
      int rightMotor = leftMotor + 1;
      if(leftMotor < 0){ //wrapping
        leftMotor = 0;
      }
      if(rightMotor >= nMotor){
        rightMotor = nMotor - 1;
      }
      int leftMo
      */
      int n = nMotor * objList[i].pos / maxPos;
      if(patternPrio[objList[i].type] < motorPrio[n]){
        continue;
      }
      int strength = objList[i].strength > 100 ? 100 : objList[i].strength;
      motorLevel[n] = objList[i].strength * *(patternPtr[objList[i].type]+objList[i].phase) / 100;
      
      objList[i].phase++;
      if(*(patternPtr[objList[i].type]+objList[i].phase) < 0){
        objList[i].phase = 0;
      }
    }
    /*
    for(int n = 0; n < nMotor; n++){
      Serial.print(motorLevel[n]);
      Serial.print(',');
    }
    Serial.println();
    */
    ///do fast switching (pwm)///
    for(int i = 0; i < nCycle; i++){//cycle loop
      for(int l = 0; l < nLevel; l++){//duty loop
        for(int n = 0; n < nMotor; n++){
          if(motorLevel[n] > l){
            //high
            digitalWrite(motorPin[n], HIGH);
          }else{
            //low
            digitalWrite(motorPin[n], LOW);
          }
        }
        delay(sleepMs);
      }
    }
    tick++;
  }
}
