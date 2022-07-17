# Notes 2022-07-17
- Checked in moveTo commands to move to a percentile
- Tried installing notebooks to better debug. But everything still runs python 2.7. A reinstall of OS is probably easier
- Physical components and movement look ok
- Seems to move a whole clock forward instead of the shortest path
- Can run interactively with the classic python interactive shell
- ```
python
import furby
f = furby.Furby()
f.calibrate()
f.moveTo(10)
f.moveTo(90)
```
- When doing a moveTo(10) after each other, it moves back/forth on the same position
- When doing a moveTo(90) and moveTo(10) it doest'n move to the desired 10% beyond calClick



# Notes 2021-12-07
- created git repo
- IR LED should be connected.
	-checked LED voltage, seems to outpult 5v on multimeter, but is actually auto adjusting to LED voltage
	- should connect wires and hot-glue them solid

- changed button pins to different layout. 
	see button.py
	when button is pressed, callback can be looped when gpio loops to ground
- motor pwm controller works, orange/yellow wires should be soldered
- zipties are amazing to keep the wires together
- should solder speaker wires

- pin on bottom pokes at pizero
	- move pizero
	- or remove poke sticko
	- can be latched with tie-wrap

- cannot keep furby steady. fix red stick on bottom with a aluminium rod
	- furby remains steady enough
	- can be latched with tie-wrap

- putting fur over furby
	- face does not seal tight
	- does wrap around bottom
	- cables nearly fit, should probably cut them trough the skin
	- board moves when pushing cables, glue/tape does not hold. See if it can be wrapped with tiewrap
		yes can be done. Solder wires first for speaker
