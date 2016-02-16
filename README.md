pyalfred
========

Installation
------------

```
python3 setup.py install
```

Usage
-----

You can find an easy example in `bin/pyalfred`.

```python
import pyalfred

ac = pyalfred.AlfredConnection()

# Send "Hello World" as id 64 (with the local mac as sender)
ac.send(64, "Hello World")

# Send "Wake up, Neo" as id 64 (with a custom mac as sender)
ac.send(64, "Wake up, Neo", mac="00:11:22:33:44:55")


# Receive all data with id 64 (returns a dict with mac keys)
data = ac.fetch(64)
```
