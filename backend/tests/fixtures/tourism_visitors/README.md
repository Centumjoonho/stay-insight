# TEST / DEVELOPMENT ONLY

Real official locgoRegnVisitrDDList responses captured 2026-09-30 using private tooling.
No application seed, production fallback or sync input. HTTP 200 for every capture.
JSON formatting normalized; response fields and values preserved. No request URLs,
keys or headers saved. daily.json contains one day (2026-08-01), all 807 returned
records requested with pageNo=1 and numOfRows=1000, including 48 Busan records.
empty.json requests 2026-09-01; invalid.json supplies invalid for both dates.
boundary.json requests one row for 2026-08-31. missing_parameter.txt is the actual
JSON error response with startYmd omitted, not the normal response envelope.

These snapshots do not establish newest complete data, maximum page size,
continuous historical coverage, or guaranteed null/error behavior. Synthetic
negative mutations exist only in the test module and are not live observations.
