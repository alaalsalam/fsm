# Product business flow

The product exposes five canonical flows: After-Sales Setup, Preventive Maintenance, Corrective Service, Workshop/Repair and Contract Renewal. All begin with ERPNext master/commercial truth and converge on `Service Job` for operational execution. They then return evidence to ERPNext reporting, stock and billing references.

The operator starts at Operations Home, After-Sales Setup, Requests, Maintenance, Visits or Exceptions. Every non-terminal projection supplies a next action; details link back to the owning record rather than copying its state.
