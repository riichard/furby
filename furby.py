#!/usr/bin/env python

# Import required modules
# from abc import update_abstractmethods
import time
import RPi.GPIO as GPIO
import random
import math
GPIO.cleanup()

# Declare the GPIO settings
GPIO.setmode(GPIO.BOARD)

## equivalent to BCM pin 25
sensor = 22

GPIO.setmode(GPIO.BOARD)
# GPIO.setup(sensor, GPIO.IN)


# Set the filename and path for the sound card in use (See: https://howchoo.com/g/mmnhmti2zjz/how-to-detect-that-audio-is-currently-being-output-in-linux-and-use-it-to-call-a-program#create-an-audio-output-monitor-script)
soundcard_status_file = '/proc/asound/card2/pcm0p/sub0/status'

# Turn off GPIO warnings caused by us declaring our pins outside of the start_furby and stop_furby functions
GPIO.setwarnings(True)

clockwise = False

AIN1 = 29 # PIN 5
AIN2 = 31 # PIN 6
PWMA = 7 # PIN 4
STDBY = 13 # PIN 27
IR = 18 # 24
CAL = 36 # 16
PWMA_TEST = 32 # PWM0 BCM12
TONGUE = 33

ir_ticks = 0
def ir_callback(channel):
    print("IR Tick")

cal_ticks = 0
def cal_callback(channel):
    # cal_ticks+=1
    print("CAL Tick: " + str(channel))

def tongue_callback(channel):
    print("TONGUE PRESSED")
    pwm.ChangeDutyCycle(0)

def start_furby():
    if clockwise:
        # Drive the motor clockwise
        GPIO.output(AIN1, GPIO.HIGH) # Set AIN1
        GPIO.output(AIN2, GPIO.LOW) # Set AIN2
    else:
        GPIO.output(AIN1, GPIO.LOW) # Set AIN1
        GPIO.output(AIN2, GPIO.HIGH) # Set AIN2
    # GPIO.output(29, GPIO.HIGH) # Set pin 5 to test functionality

    # Set the motor speed
    #GPIO.output(PWMA, GPIO.HIGH) # Set PWMA
    # pwm.ChangeDutyCycle(50)
    pwm.start(40)
    #GPIO.output(PWMA_TEST, GPIO.HIGH) # Set AIN2

    GPIO.add_event_detect(CAL,GPIO.RISING,callback=cal_callback, bouncetime=200) 
    GPIO.add_event_detect(TONGUE,GPIO.RISING,callback=tongue_callback, bouncetime=200) 
    GPIO.add_event_detect(IR,GPIO.RISING,callback=ir_callback, bouncetime=20) 

    # Disable STBY (standby)
    GPIO.output(STDBY, GPIO.HIGH)
    print("Running")
    time.sleep(1000)


def stop_furby():
    # Reset all the GPIO pins by setting them to LOW
    GPIO.output(AIN1, GPIO.LOW) # Set AIN1
    GPIO.output(AIN2, GPIO.LOW) # Set AIN2
    GPIO.output(PWMA, GPIO.LOW) # Set PWMA
    GPIO.output(STDBY, GPIO.LOW) # Set STBY


def main():
    print "starting"
    # Set up GPIO pins
    GPIO.setup(PWMA, GPIO.OUT) # Connected to PWMA 
    GPIO.setup(AIN2, GPIO.OUT) # Connected to AIN2
    GPIO.setup(AIN1, GPIO.OUT) # Connected to AIN1
    GPIO.setup(STDBY, GPIO.OUT) # Connected to STBY

    ## AIN2 / AIN1 seem broken. Testing if other IO works.
    # GPIO.setup(29, GPIO.OUT) # Connected to AIN2 possibly, testing 

    count = 0
    start_furby()


def foo():
    if GPIO.input(sensor):
        print "object detected"
        while GPIO.input(sensor) is True:
            time.sleep(0.001)
        print "end of ir gap"
        count+=1
        print count
        stop_furby()
        time.sleep(0.01)
    else:
        print "no object detected"
    time.sleep(0.0005)
    stop_furby()
    time.sleep(0.03)

    if count > 3:
        time.sleep(3)
        clockwise != clockwise
        count = 0

    stop_furby()

    return
    # Open file and check contents
    with open(soundcard_status_file, 'r') as fh:
        value = fh.read()
        if value == 'RUNNING':
            start_furby()
        else:
            stop_furby()

class Furby:
    def __init__(self):
        self.pos = 1
        self.maxPos = 0
        self.maxError = 30
        self.speed = 70
        self.clockwise = True
        self.calibrated = False
        self.des = 0
        self.desPerc = 0

        # GPIO.setup(IR, GPIO.IN)
        GPIO.setup(IR,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.setup(CAL,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        GPIO.setup(TONGUE,GPIO.IN,pull_up_down=GPIO.PUD_UP)

        GPIO.setup(PWMA_TEST, GPIO.OUT)
        self.pwm = GPIO.PWM(PWMA_TEST, 300)

        GPIO.setup(PWMA, GPIO.OUT) # Connected to PWMA 
        GPIO.setup(AIN2, GPIO.OUT) # Connected to AIN2
        GPIO.setup(AIN1, GPIO.OUT) # Connected to AIN1
        GPIO.setup(STDBY, GPIO.OUT) # Connected to STBY

        GPIO.add_event_detect(CAL,GPIO.RISING,callback=self.calCallback, bouncetime=200) 
        GPIO.add_event_detect(TONGUE,GPIO.RISING,callback=self.tongueCallback, bouncetime=200) 
        GPIO.add_event_detect(IR,GPIO.RISING,callback=self.irCallback) 

        self.setDirection(True)

    def start(self):
        print("starting")
        GPIO.output(STDBY, GPIO.HIGH)
        self.pwm.start(self.speed)

    def stop(self):
        print("stopping at ", self.pos)
        print("reached des ", self.des, self.desPerc, " by error of ", self.des - self.pos)
        self.pwm.stop()
        GPIO.output(STDBY, GPIO.LOW)
        print("maxpos", self.maxPos)

    def setDirection(self, clockwise):
        if clockwise:
            print("Setting direction clockwise")
            GPIO.output(AIN1, GPIO.HIGH) # Set AIN1
            GPIO.output(AIN2, GPIO.LOW) # Set AIN2
        else:
            print("Setting direction counter clockwise")
            GPIO.output(AIN1, GPIO.LOW) # Set AIN1
            GPIO.output(AIN2, GPIO.HIGH) # Set AIN2
        self.clockwise = clockwise
    
    def setSpeed(self, speed): # 0 < speed < 100
        self.speed = speed
        self.pwm.ChangeDutyCycle(speed)

    def calCallback(self, pin):
        print("cal callback " + str(self.pos))
        self.calibrated = True
        self.pos = 0
        print("-----POSITION-RESET----")

    def irCallback(self, pin):
        print("ir callback " + str(self.pos))
        if self.maxPos < self.pos:
            self.maxPos = self.pos

        if self.clockwise:
            self.pos += 1
            """
            if self.pos >= self.des:
                print("reached destination of "+str(self.des))
                self.stop()
            """
        else:
            self.pos -= 1
            """
            if self.pos <= self.des:
                print("reached destination of "+str(self.des))
                self.stop()
            """


    def tongueCallback(self, pin):
        print("tongue callback")

    def moveDown(self, des):
        print("moving down, "+str(des))
        self.setDirection(False)

        self.des = des
        self.start()
        while self.pos > des:
            time.sleep(0.0001)
        self.stop()

    def moveUp(self, des):
        print("moving up, "+str(des))
        self.setDirection(True)
        print("moving up")

        self.des = des
        self.start()
        
        while self.pos < des:
            time.sleep(0.0001)
        self.stop()
        print("destination reached")

    def moveTo(self, angle):
        des = min(math.floor((self.maxPos/100)*angle), (self.maxPos - self.maxError)) # TODO set maxError smarter based on better maxPos averaging
        print('moveto', angle, self.pos, des)
        deltaWithoutCal = self.pos - des
        deltaWithCal = min(
            ((des + self.maxPos) - self.pos), # angle80 -> angle10 = (100 + 10) - 80 = 30
            ((self.maxPos + self.pos) - des) # angle10 -> angle80 = (100 + 10) - 80 = 30
        );
        print('delta with cal', deltaWithCal)
        print('delta without cal', deltaWithoutCal)
        self.desPerc = angle

        if deltaWithoutCal < deltaWithCal:
            print("moving without cal")
            if des > self.pos:
                self.moveUp(des)
            else:
                self.moveDown(des)
        else:
            print("moving with cal, ")
            if des < self.pos:
                # make current pos negative based on maxpos
                self.pos = self.pos - self.maxPos
                # pos will reset to 0
                # move up instead of down
                self.moveUp(des)
                print('finished moving up', self.pos)
            else:
                # make des negative based on maxpos
                nDes = des - self.maxPos
                # pos will reset to 0
                # move down instead of up
                self.moveDown(nDes)
                print('finished moving down', self.pos)
        print('finished move to angle ', angle)
                


    def calibrate(self):
        print("calibrating")
        # self.pos = 0
        self.des = 0
        self.setDirection(True)
        self.start()
        time.sleep(2)
        self.stop()
        time.sleep(1)
        print("has max pos", self.maxPos)
        self.moveTo(10)
        self.moveTo(1)
        print("==========CALIBRATED===========")
        """
        self.setDirection(False)
        self.calibrated = False
        time.sleep(0.01)
        self.start()
        while self.calibrated == False:
            print("calibrating..")
            time.sleep(0.01)
        print("cal reached")
        self.stop()
        self.calibrated = False
        """

if __name__ == '__main__':
    try:
        f = Furby()

        #f.start()
        #time.sleep(10)
        #f.stop()
        f.calibrate()
        print("calibrate command finished")
        print("wait..")
        #time.sleep(10)


        print(f.pos, f.maxPos, f.des)
        """
        f.moveTo(30)
        f.moveTo(1)
        f.moveTo(60)
        time.sleep(1)
        """
        
        print('---------------------------------------ready')
        f.moveTo(90)
        f.moveTo(10)
        """
        
        
        f.moveTo(1)
        #time.sleep(1)
        f.moveTo(60)
        #time.sleep(1)
        f.moveTo(90)
        f.setSpeed(100)
        for i in range(3):
            f.moveTo(70)
            f.moveTo(75)
        f.moveTo(90)
        f.setSpeed(30)
        for i in range(3):
            f.moveTo(20)
            f.moveTo(15)
        f.moveTo(100)

        """


        """
        #r = random.randint(0,f.maxPos)
        f.moveTo(r)
        time.sleep(1)
        f.calibrate()
        f.moveTo(0)
        time.sleep(1)
        f.moveTo(100)
        time.sleep(1)
        f.moveTo(200)
        """


        #time.sleep(1)
        #f.moveTo(10)
        #time.sleep(1)
        #f.moveTo(60)
        # f.moveTo(30)
        # f.moveTo(60)

        

    except KeyboardInterrupt:
        print("Cleanup by keyboard interrupt")
        GPIO.cleanup()
    except Exception as e:
        print("uncaught error")
        print(e)
    finally:
        print("Cleanup")
        GPIO.cleanup()

