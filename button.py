#Libraries
import RPi.GPIO as GPIO
from time import sleep
#Set warnings off (optional)
GPIO.setwarnings(True)
GPIO.setmode(GPIO.BOARD)
#Set Button and LED pins
# Button = 36 # 16
Button = 33 # 13
#Setup Button and LED
GPIO.setup(Button,GPIO.IN,pull_up_down=GPIO.PUD_UP)
#flag = 0

def button_callback(channel):
        print("Button was pushed!")

GPIO.add_event_detect(Button,GPIO.RISING,callback=button_callback) # Setup event on pin 10 rising edge

message = input("Press enter to quit\n\n") # Run until someone presses enter
GPIO.cleanup() # Clean up

# based on https://raspberrypihq.com/use-a-push-button-with-raspberry-pi-gpio/
