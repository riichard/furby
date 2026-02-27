HOST      = furby
REMOTE    = ~/furby
PYTHON    = python3

# Files/dirs to sync (excludes secrets, cache, git, and Pi-local memory)
RSYNC_OPTS = --archive --verbose --exclude='.git' --exclude='__pycache__' \
             --exclude='*.pyc' --exclude='.env' --exclude='*.pdf' \
             --exclude='memory/'

.PHONY: deploy run calibrate ssh log summarize

## Sync code to Pi (excludes .env — manage that separately on the Pi)
deploy:
	rsync $(RSYNC_OPTS) . $(HOST):$(REMOTE)/

## Deploy then start main loop
deploy-run: deploy run

## Run the main always-listening loop on the Pi
run:
	ssh $(HOST) "cd $(REMOTE) && $(PYTHON) main.py"

## Run the expression calibration tool on the Pi
calibrate:
	ssh $(HOST) "cd $(REMOTE) && $(PYTHON) calibrate_expressions.py"

## Run AI chat test on the Pi
test-ai:
	ssh $(HOST) "cd $(REMOTE) && $(PYTHON) ai.py"

## Run voice test on the Pi
test-voice:
	ssh -t $(HOST) "cd $(REMOTE) && $(PYTHON) -u voice.py 2>/dev/null"

## Open SSH shell on the Pi
ssh:
	ssh $(HOST)

## Tail the last run's output (if you background it)
log:
	ssh $(HOST) "tail -f $(REMOTE)/furby.log"

## Run the memory summarizer on the Pi (also run nightly via cron)
summarize:
	ssh $(HOST) "cd $(REMOTE) && $(PYTHON) summarize.py"
