import RPi.GPIO as GPIO
import time

pins = [14,15,26,23,24,25,5,6,13]


try:
    for i in pins:
        print(i)
        GPIO.setmode(GPIO.BCM) 
        GPIO.setup(i, GPIO.OUT) 
        GPIO.output(i, GPIO.HIGH) 
        print("LED ON")
        time.sleep(1) 

        GPIO.output(i, GPIO.LOW) 
        print("LED OFF")
        time.sleep(1) 

except KeyboardInterrupt:
    GPIO.cleanup()

except Exception as e:
    print(f"An error occurred: {e}")
    GPIO.cleanup()

finally:
    GPIO.cleanup()
