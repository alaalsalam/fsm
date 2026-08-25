# Mobile Field Application

The Ionic/Vue Capacitor application is the technician surface for assigned work. It consumes the same typed Installed Base, Inspection, Materials and Reporting contracts as the web surfaces.

## Field flow

- My Jobs/My Day with duty state, urgent/current work, cached jobs and team/van context.
- Job customer, location, visit lifecycle and linked equipment/QR lookup.
- Typed inspection capture with server-calculated outcome.
- ERPNext-backed van availability and material consumption.
- Camera evidence and customer report signature capture.
- Equipment history and service-document visibility.

All state-changing online operations call guarded commands. The mobile client never writes a DocType status directly.
