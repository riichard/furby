
i created this project a while ago, it was a poc script to program a furby but i want to upgrade it now using AI and make it really expressive with a TTS and Speech to text interface. And make its face match the expression on the sentence.
We should connect it to whisper API. 
We should add a wakeword detection, but can add this later, and first start with an always listening mode.




This is a description on the hardware.

it was a script that runs on the furby and activates the motor, with this motor it can make all kinds of expressions on the furby's face, it can move its mouth, ears, eyes, and effectively talk. This is the first generation furby from the 90's.
With this, it has a stepper motor sensor based on an IR light and a light sensor that detects a high/low based on a disk in front of it that allow light to pass trough. This allows us to count when light goes trough, so that we can control the motor speed and guess the position.
With that there's also a hardware sensor, this gets triggered at the full cycle and makes us know for certain where the position is.

i have yet to define what position relates to what expression.
But for instance, this part

      print("testing talk mode")
        raw_input("Press Enter to continue...")
        for x in range(6):
            f.moveTo(80)
            f.moveTo(90)
            f.moveTo(10)
            f.moveTo(90)


It uses the moveTo function to be able to define an absolute position, which tries to position based on it's known calibration reference point. 

We should create a configuration file in which we can write all expressions and what they mean on the rotary index. 
We can then set a sequence of expressions, in which we can play an animation along a text based on the text sent by the AI voice model.
The expressions that come back have to match what we can physically execute, expressions have to be near each other on the expression dial, and we can't move too fast. We have to move back and forth between and around expressions a bit to look alive. 

I wonder if voice assistant API's allow to get text back, and to match it with expressions and a lip sync way, as limited as the furby can be.

please share more info on the voice assistant API opportunities and how we can structure the project the best. I think this system doesn't have to hold, we can discard most of the code, and rearrange the logic on how the dial works and the calibration. you can see the rising/falling edge definitions and the way that the clock works with the calibration hardware switch. There's some debouncing code in there, and a bit of tuning on delays, which we'll have to optimize next too. 

I can add credits, i don't think this'll consume much credits so i'm not worried about this

