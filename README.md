# Python Object Persistence

This library provides a single `@dataobject` decorator for object persistence. `filter` and `exclude` methods are added as classmethods to query the existing objects.

## Example
```python
@dataobject
class MyClassA:
    name: str
    health: int = 100
    my_path: Path = None
    inventory: list['MyClassB'] = []
```
This creates an `__init__` with the default arguments of the class variables.

```python
@dataobject
class MyClassB:
    daddy: MyClassA
    other_items: list
    timestamp: datetime
    problems: random.randint(0, 99)
```
`MyClassA` and `MyClassB` now reference each other.
We create the objects like we would any other, just keep in mind to use all keyword arguments.

```
a1 = MyClassA(name="Benjamin") # Throws an error because 
a2 = MyClassA(name="Steve", inventory=["Stone Pickaxe"])

b1 = MyClassB(daddy=a1, 
              timestamp=datetime.now(), 
              other_items=['Some cheese', 'Bud light'])
b2 = MyClassB(daddy=b1, 
              timestamp=b1.timestamp, 
              other_items=[b1])

a1.inventory.append(b1)
a2.inventory.append(b2)

```

## How it works
Decorated classes will store its instances under `./data/<ClassName>` as a `.json` file.

## Properties
For each class variable that is annotated, a `property` will be provided with the same name. Class variables whos annotation is also a decorated object are stored as UUID and will be resolved when their `get` method is first called.

## Limitations
All objects are kept in memory

## Next steps
- Explicit archiving, adding items to a `.zip` archive.
- Optional explicit saving for better performance.
- Allow creaton/modification/deletion of objects from files using watchdog to monitor the data directory for changes.