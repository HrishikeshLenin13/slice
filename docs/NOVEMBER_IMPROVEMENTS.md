# Python source extraction

Nested tuple/list unpacking and starred targets now produce module-level global symbols. Attribute and subscription stores are not misidentified as new globals. Source spans and existing chained assignments are preserved.
