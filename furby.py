#!/usr/bin/env python

# Import required modules
import time
import RPi.GPIO as GPIO

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
    GPIO.output(PWMA, GPIO.HIGH) # Set PWMA

    # Disable STBY (standby)
    GPIO.output(STDBY, GPIO.HIGH)
    print("Running")
    while True:
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

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Cleanup by keyboard interrupt")
        GPIO.cleanup()
    except:
        print("uncaught error")
    finally:
        print("Cleanup")
        GPIO.cleanup()

