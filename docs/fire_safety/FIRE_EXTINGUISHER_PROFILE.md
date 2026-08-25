# Fire Extinguisher specialization

Date: 2026-08-25. Domain owner: **FSM Fire Safety**, implemented as a specialization of the generic Installed Equipment and Inspection domains.

## Ownership

- ERPNext Item/Brand remains the product catalogue and generic manufacturer/model source.
- Installed Equipment stores the physical unit's nameplate/service facts: extinguisher type, capacity/UOM, agent,
  nameplate manufacturer/model, manufacture/expiry dates, pressure rating and hydro interval.
- Last refill/result, last hydro test and calculated hydro due are service history on the installed unit, not stock
  consumption or an Item master override.
- Other categories (Fire Alarm, Fire Pump, Hose Reel, Sprinkler, Emergency Light and Fire Door) are enumerated for
  future specializations; no extinguisher logic is imposed on them.

Hydro due is recalculated from the latest hydro test, otherwise manufacturing date, plus the configured interval.
Service history writes require an authorized canonical Job containing the equipment and emit an append-only event.
No Stock Entry, Material Request, Invoice or accounting document is created in this phase.
