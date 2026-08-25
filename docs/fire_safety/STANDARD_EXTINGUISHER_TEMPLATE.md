# Standard Fire Extinguisher inspection template

The guarded installer creates one active, editable company template and is idempotent. It contains 19 typed items:
cylinder/body, corrosion, pressure, hose, nozzle, valve, pin, seal, label, mounting, accessibility, signage, weight,
manufacturing date, expiry, last refill, hydro test, photos and notes.

The template uses the generic Inspection Engine. Critical defects and configured actions can produce Fail, Needs
Refill, Needs Repair or Needs Replacement without hard-coding the whole application to extinguishers. Companies may
revise the generated template through the versioned Template command.
