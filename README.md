# Python Object Persistence

This library provides a single `@dataobject` decorator for object persistence.
Decorated classes will store their instances under `./data/<ClassName>` in `json` format with their UUID as filename.
`filter()` and `exclude()` methods are added as classmethods to query the existing objects.

For each class variable that is annotated, a `property` will be provided with the same name.

Class variables whose annotation is also a decorated object or list thereof are stored as a string of their UUID and will be resolved when their `get()` method is first called.

## Example
```python
@dataobject
class MyClassA:
    name: str
    health: int = 100
    my_path: Path = None
    inventory: set['MyClassB'] = set() # One-to-many
```
This creates an `__init__`-function with the default arguments of the class variables.

```python
@dataobject
class MyClassB:
    daddy: MyClassA # One-to-one relation
    other_items: list
    timestamp: datetime
    problems: random.randint(0, 99)
```
`MyClassA` and `MyClassB` now reference each other.
We create the objects like we would any other, just keep in mind to use all keyword arguments.

```python
a1 = MyClassA(name="Benjamin")
a2 = MyClassA(name="Steve")

b1 = MyClassB(daddy=a1, 
              timestamp=datetime.now(), 
              other_items=['Some cheese', 'Bud light'])
b2 = MyClassB(daddy=a2, 
              timestamp=b1.timestamp, 
              other_items=[b1])
```

Because `MyClassA.inventory` is annotated with `set['MyClassB']`[^1], the `getattr` function returns a `DataObjectList` type.
This is basically a `list` with `filter()` and `exlude()` methods to perform queries.
Additionally, operations like `append` and `remove` are wrapped to save the object afterwards.

[^1]: Behaviour is similar with annotations like `MyClassX`, `'MyClassX'`, `set[MyClassX]`, `list[MyClassX]`, `list['MyClassX']`.

```python
a1.inventory.append(b1)
a2.inventory.append(b2)

steve_not_my_daddy = MyClassB.exclude(daddy=lambda x: x.name.startswith('Steve'))
cheese_i_have = a1.inventory.filter(other_items=lambda x: "Some cheese" in x)

print(steve_not_my_daddy)   # [b1]
print(cheese_i_have)        # [b1]

print(type(steve_not_my_daddy)) # <class 'src.dataobject.dataobject.<locals>.DataObjectList'>
print(type(a1.inventory))       # <class 'src.dataobject.dataobject.<locals>.DataObjectList'>
```

## Limitations
1. All objects are kept in memory.
2. Currently, only `datetime` and `Path` objects are transcoded besides the builtins.

## Next steps
- Explicit archiving, adding items to a `.zip` archive (to partially address limitation #1);
- Option to disable implicit saving;
    - Combine with a `rollback` function to facilitate transactions;
- Custom transcoders (to address limitation #2);
- Typechecking for getters and setters;
- Derive date created from file metadata;
- Custom assignment of data folder;
- Allow creaton/modification/deletion of objects from files using watchdog to monitor the data directory for changes;
    - This may allow this framework to function as a synchronized database when combined with something like `portalocker`;
- CSV file writing of all objects;
- Optional integrations:
    - NiceGUI to have some kind of admin page;
- Saving asynchronously;