# Event Model

An event is the business source object that triggers a run. It contains the operating objective, schedule, offer, target, channel intent, and source references.

Events live under `events/{event-id}/`. Generated pipeline outputs should not be written back into the event folder.
