"""
The DataObject package provides a single-decorator way to persist Python objects.
It acts like a filesystem variant of an ORM.
Copyright (C) 2024 Hans Koene

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations
from datetime import datetime
from functools import wraps
from itertools import chain
import json
from pathlib import Path
from pprint import pformat
from uuid import UUID, uuid4
import inspect
from inspect import signature, Parameter

# --- 
from src.properties import make_property


class DataObject:
    """
    TODO:
        Meta
        1. Add testing (stress/functionality)
        2. Error handling
        3. Use cases:
            a. Check if network persistence is possible (blocked by Functionality #3)
            
        Functionality
        1. Return list[DataObject] fields as DataObjectList to allow querying
        2. Make DataObjectList operations update the object
        3. Add watchdog functionality
        4. Add archiving functionality
        5. Integrate with NiceGUI
        6. (Custom) encoders/decoders for more types
        
        Bugs:
        1. Attributes annotated with DataObject subclasses get stored as strings, but not restored.
        
    Notes:
        Class variables with no type hint don't get picked up because they are not in __class__.__annotations__.
        A reference to a DataObject annotated with a string will get resolved when queried.
        
    """
    __types: dict[str, __qualname__] = {}
    __directory: Path = Path.cwd() / 'data'
        
    class DataObjectList(list):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            
        def filter(self, func=__builtins__['all'], **kwargs) -> DataObjectList:
            return DataObject.filter(func=func, objects=self, **kwargs)
            
        def exclude(self, func=__builtins__['all'], **kwargs) -> DataObjectList:
            return DataObject.exclude(func=func, objects=self, **kwargs)
        
        def sort(self, key, reverse=False) -> DataObjectList:
            return sorted(self, key=key, reverse=reverse)
        
    @classmethod
    def get(cls, uuid: UUID): 
        for subcls in DataObject.__types.values():
            try:
                return subcls.get(uuid)
            except StopIteration:
                print(f"No {subcls.__name__} object found with UUID: {uuid}")
                
    @classmethod
    def filter(cls, func=all, **kwargs) -> DataObjectList:
        matches = DataObjectList()
        for subcls in DataObject.__types.values():
            if all(hasattr(subcls, k) for k in kwargs.keys()):
                matches += subcls.filter(func=func, **kwargs)
        return matches
    
    @classmethod
    def exclude(cls, func=all, **kwargs) -> DataObjectList:
        matches = DataObjectList()
        for subcls in DataObject.__types.values():
            if all(hasattr(subcls, k) for k in kwargs.keys()):
                matches += subcls.exclude(func=func, **kwargs)
        return matches
    
    @classmethod
    def all() -> DataObjectList:
        instances = DataObjectList()
        for subcls in DataObject.__types.values():
            instances += subcls.all()
        return instances
        
    @classmethod
    def count(cls) -> int:
        counter = 0
        for subcls in DataObject.__types.values():
            counter += subcls.count()
        return counter
    
class DataObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, DataObject):
            return obj.UUID
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.timestamp()
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, set):
            return tuple(obj)

        return super().default(obj)

def dataobject(cls):
    class DataObjectList(list):
        def __init__(self, *args, **kwargs):
            self.__container__ = None
            super().__init__(*args, **kwargs)
        
        def filter(self, func=__builtins__['all'], **kwargs) -> DataObjectList:
            return cls.filter(func=func, objects=self, **kwargs)
            
        def exclude(self, func=__builtins__['all'], **kwargs) -> DataObjectList:
            return cls.exclude(func=func, objects=self, **kwargs)
        
        def save_after(func):
            
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                if self.__container__:
                    self.__container__.save(check=False)
                return res
            return wrapper
        
        @save_after
        def append(self, *args, **kwargs):
            return super().append(*args, **kwargs)
        
        @save_after
        def extend(self, *args, **kwargs):
            return super().extend(*args, **kwargs)
        
        @save_after
        def insert(self, *args, **kwargs):
            return super().insert(*args, **kwargs)
        
        @save_after
        def remove(self, *args, **kwargs):
            return super().remove(*args, **kwargs)
        
        @save_after
        def pop(self, *args, **kwargs):
            return super().pop(*args, **kwargs)
        
        @save_after
        def clear(self, *args, **kwargs):
            return super().clear(*args, **kwargs)

    # Keep track of class instances
    setattr(cls, '__DataObject_instances', DataObjectList())
    setattr(cls, '__DataObject_directory', DataObject._DataObject__directory / cls.__name__)
   
    # Set object methods 
    def date_created(self):
        return datetime.fromtimestamp(self.PATH.stat().st_ctime)
    setattr(cls, 'date_created', date_created)
    
    def delete(self):
        setattr(self, '__DataObject_deleted', True)
        setattr(self, '__DataObject_uuid', None)
        self.__class__.__DataObject_instances.remove(self)
        self.PATH.unlink()
    setattr(cls, 'delete', delete)
        
    # Save the object
    def save(self, check=True):
        if check:
            for field_name in self.__DataObject_fields.keys():
                getattr(self, field_name)
            
        with self.__DataObject_path.open('w', encoding='utf-8') as file:
            json.dump(self.__DataObject_fields, file, indent='\t', cls=DataObjectEncoder)
            
    setattr(cls, 'save', save)
        
    # Generate __init__ function for the class based on class_annotations
    original_init = cls.__init__
    class_annotations = inspect.get_annotations(cls)
    def __init__(self, **kwargs):
        # Set standard attributes and create file if necessary
        getattr(cls, '__DataObject_instances').append(self)
        setattr(self, '__DataObject_fields', {})
        setattr(self, '__DataObject_uuid', kwargs.get('uuid', uuid4()))
        setattr(self, '__DataObject_deleted', False)
        kwargs.pop('uuid', None)
        setattr(self, '__DataObject_path', getattr(self, '__DataObject_directory') / str(getattr(self, '__DataObject_uuid')))
        getattr(self, '__DataObject_path').touch(exist_ok=True)
        setattr(cls, '__str__', lambda x: pformat(getattr(self, '__DataObject_fields')))
        setattr(self, 'UUID', getattr(self, '__DataObject_uuid'))
        setattr(self, 'PATH', getattr(self, '__DataObject_path'))
        
        # Read class variable annotations and defautls to determine arguments
        defaults = {k:v.default for (k, v) in signature(self.__class__.__init__).parameters.items() if k not in kwargs.keys() and v.default is not Parameter.empty}
        kwargs.update(defaults)
        missing_args = set(class_annotations.keys()) - set(kwargs.keys())
        extra_args = set(kwargs.keys()) - set(class_annotations.keys())
        
        if missing_args:
            raise TypeError(f"{cls.__name__}.__init__() missing arguments {missing_args}")
        elif extra_args:
            raise TypeError(f"{cls.__name__}.__init__() got unexpected keyword arguments {extra_args}")
        else:
            setattr(self, '__DataObject_fields', kwargs)

        self.save()
        
        original_init(self)
    
    @wraps(original_init)
    def new_init(self, **kwargs):
        __init__(self, **kwargs)
    
    cls.__init__ = new_init
    
    sig = signature(__init__)
    params = [Parameter('self', Parameter.POSITIONAL_OR_KEYWORD, annotation=cls)]
    params += [Parameter(name=name, 
                        kind=Parameter.POSITIONAL_OR_KEYWORD,
                        default=getattr(cls, name) if hasattr(cls, name) else Parameter.empty,
                        annotation=annotation) 
                for name, annotation in class_annotations.items()]
    sig = sig.replace(parameters=params, return_annotation=cls)
    __init__.__signature__ = sig
    setattr(cls, '__init__', __init__)
    
    # Make the class a DataObject type    
    cls = type(cls.__name__, (DataObject, cls), {})
    DataObject._DataObject__types[cls.__name__] = cls
    
    for field_name, field_type in class_annotations.items():
        setattr(cls, field_name, make_property(cls, field_name, field_type, DataObjectList))
    
    # Define classmethods
    def check(obj, func, invert, values, callables):        
        if func(chain(((getattr(obj, k) == v) for k, v in values.items()), 
                      (v(getattr(obj, k)) for k, v in callables.items()))):
            return not invert
        else:
            return invert
    
    @classmethod
    def get(cls, uuid: UUID) -> DataObject:
        return next((obj for obj in cls.__DataObject_instances if obj.UUID == (UUID(uuid) if type(uuid) is str else uuid)), None)
    setattr(cls, 'get', get)
        
    @classmethod
    def filter(cls, func=__builtins__['all'], objects=cls.__DataObject_instances, **kwargs) -> DataObjectList:
        values = {k: v for k, v in kwargs.items() if not callable(v)}
        callables = {k: v for k, v in kwargs.items() if callable(v)}
        return DataObjectList([obj for obj in objects if check(obj, func, invert=False, values=values, callables=callables)])
    setattr(cls, 'filter', filter)
    
    @classmethod
    def exclude(cls, func=__builtins__['all'], objects=cls.__DataObject_instances, **kwargs) -> DataObjectList:
        values = {k: v for k, v in kwargs.items() if not callable(v)}
        callables = {k: v for k, v in kwargs.items() if callable(v)}
        return DataObjectList([obj for obj in objects if check(obj, func, invert=True, values=values, callables=callables)])
    setattr(cls, 'exclude', exclude)
    
    @classmethod
    def all(cls) -> DataObjectList:
        return DataObjectList(cls.__DataObject_instances)
    setattr(cls, 'all', all)
    
    @classmethod
    def count(cls) -> int:
        return len(cls.__DataObject_instances)
    setattr(cls, 'count', count)
    
    # Create a folder to store data objects of this type and load instances
    if cls.__DataObject_directory.exists():
        for file in cls.__DataObject_directory.iterdir():
            with file.open('r', encoding='utf-8') as fp:
                data = json.load(fp)
                if isinstance(data, dict):
                    cls(**data, uuid=UUID(file.stem))
    else:
        cls.__DataObject_directory.mkdir()
        
    return cls