# Python source extraction

Nested tuple/list unpacking and starred targets now produce module-level global symbols. Attribute and subscription stores are not misidentified as new globals. Source spans and existing chained assignments are preserved.

Relative imports now resolve against their actual package, including `from . import module`, aliases, parent-package imports and package initializers. Imports beyond the known repository package hierarchy remain unresolved rather than inventing a target.

CLI baseline token comparisons reuse already-decoded parser snapshots instead of rereading files as UTF-8. This removes redundant file I/O and keeps coding-cookie/BOM inputs consistent through analysis.
