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

# --- Built-in ---
from __future__ import annotations
from datetime import datetime
from functools import wraps
from itertools import chain
import json
import logging
from pathlib import Path
from pprint import pformat
import random
from uuid import UUID, uuid4
import inspect
from inspect import signature, Parameter

# --- Internal ---
from properties import make_property


class DataObject:
    __types: dict[str, __qualname__] = {}
    __directory: Path = Path.cwd() / "data"
    __directory.mkdir(exist_ok=True)

    class DataObjectList(list):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def filter(self, func=__builtins__["all"], **kwargs) -> DataObjectList:
            return DataObject.filter(func=func, objects=self, **kwargs)

        def exclude(self, func=__builtins__["all"], **kwargs) -> DataObjectList:
            return DataObject.exclude(func=func, objects=self, **kwargs)

        def sort(self, key, reverse=False) -> DataObjectList:
            return sorted(self, key=key, reverse=reverse)

    class DataObjectSet(set):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def filter(self, func=__builtins__["all"], **kwargs) -> DataObjectSet:
            return DataObject.filter(func=func, objects=self, **kwargs)

        def exclude(self, func=__builtins__["all"], **kwargs) -> DataObjectSet:
            return DataObject.exclude(func=func, objects=self, **kwargs)

    @classmethod
    def get(cls, uuid: UUID):
        for subcls in DataObject.__types.values():
            try:
                return subcls.get(uuid)
            except StopIteration:
                print(f"No {subcls.__name__} object found with UUID: {uuid}")

    @classmethod
    def filter(cls, func=all, **kwargs) -> DataObjectSet:
        matches = DataObjectSet()
        for subcls in DataObject.__types.values():
            if all(hasattr(subcls, k) for k in kwargs.keys()):
                matches += subcls.filter(func=func, **kwargs)
        return matches

    @classmethod
    def exclude(cls, func=all, **kwargs) -> DataObjectSet:
        matches = DataObjectSet()
        for subcls in DataObject.__types.values():
            if all(hasattr(subcls, k) for k in kwargs.keys()):
                matches += subcls.exclude(func=func, **kwargs)
        return matches

    @classmethod
    def all() -> DataObjectSet:
        instances = DataObjectSet()
        for subcls in DataObject.__types.values():
            instances += subcls.all()
        return instances

    @classmethod
    def count(cls) -> int:
        counter = 0
        for subcls in DataObject.__types.values():
            counter += subcls.count()
        return counter

    @classmethod
    def export() -> None:
        raise NotImplementedError(
            "This function should export all dataobjects to their own tab in a .csv file."
        )


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

        def filter(self, func=__builtins__["all"], **kwargs) -> DataObjectList:
            return cls.filter(func=func, objects=self, **kwargs)

        def exclude(self, func=__builtins__["all"], **kwargs) -> DataObjectList:
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

    class DataObjectSet(set):
        def __init__(self, *args, **kwargs):
            self.__container__ = None
            super().__init__(*args, **kwargs)

        def filter(self, func=__builtins__["all"], **kwargs) -> DataObjectSet:
            return cls.filter(func=func, objects=self, **kwargs)

        def exclude(self, func=__builtins__["all"], **kwargs) -> DataObjectSet:
            return cls.exclude(func=func, objects=self, **kwargs)

        def sample(self, k) -> DataObjectList:
            return DataObjectList(random.sample(list(self), k))

        def save_after(func):
            # Save after editing a DataObjectSet or DataObjectList
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                res = func(self, *args, **kwargs)
                if self.__container__:
                    self.__container__.save(check=False)
                return res

            return wrapper

        @save_after
        def add(self, *args, **kwargs):
            return super().add(*args, **kwargs)

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
    setattr(cls, "__DataObject_instances", DataObjectSet())
    setattr(
        cls, "__DataObject_directory", DataObject._DataObject__directory / cls.__name__
    )

    # Set object methods
    def date_created(self):
        return datetime.fromtimestamp(self.PATH.stat().st_ctime)

    setattr(cls, "date_created", date_created)

    def delete(self):
        setattr(self, "__DataObject_deleted", True)
        setattr(self, "__DataObject_uuid", None)
        self.__class__.__DataObject_instances.remove(self)
        self.PATH.unlink()

    setattr(cls, "delete", delete)

    # Save the object
    def save(self, check=True):
        if not getattr(self, "__DataObject_saving"):
            logging.warning("Saving is disabled for this object!")
            return

        # Update all references to other objects to remove invalid ones.
        if check:
            for field_name in self.__DataObject_fields.keys():
                getattr(self, field_name)

        with self.__DataObject_path.open("w", encoding="utf-8") as file:
            json.dump(
                self.__DataObject_fields, file, indent="\t", cls=DataObjectEncoder
            )

    setattr(cls, "save", save)

    # Generate __init__ function for the class based on class_annotations
    original_init = cls.__init__
    class_annotations = inspect.get_annotations(cls)

    def __init__(self, **kwargs):
        # Set standard attributes and create file if necessary
        getattr(cls, "__DataObject_instances").add(self)
        setattr(self, "__DataObject_saving", True)
        setattr(self, "__DataObject_fields", {})
        setattr(self, "__DataObject_uuid", kwargs.get("uuid", uuid4()))
        setattr(self, "__DataObject_deleted", False)
        kwargs.pop("uuid", None)
        setattr(
            self,
            "__DataObject_path",
            getattr(self, "__DataObject_directory")
            / str(getattr(self, "__DataObject_uuid")),
        )
        getattr(self, "__DataObject_path").touch(exist_ok=True)
        setattr(cls, "__str__", lambda x: pformat(getattr(self, "__DataObject_fields")))
        # TODO: UUID and PATH should be properties without a settter
        setattr(self, "UUID", getattr(self, "__DataObject_uuid"))
        setattr(self, "PATH", getattr(self, "__DataObject_path"))

        # Read class variable annotations and defautls to determine arguments
        defaults = {
            k: v.default
            for (k, v) in signature(self.__class__.__init__).parameters.items()
            if k not in kwargs.keys() and v.default is not Parameter.empty
        }
        kwargs.update(defaults)
        missing_args = set(class_annotations.keys()) - set(kwargs.keys())
        extra_args = set(kwargs.keys()) - set(class_annotations.keys())

        if missing_args:
            raise TypeError(
                f"{cls.__name__}.__init__() missing arguments {missing_args}"
            )
        elif extra_args:
            raise TypeError(
                f"{cls.__name__}.__init__() got unexpected keyword arguments {extra_args}"
            )
        else:
            setattr(self, "__DataObject_fields", kwargs)

        self.save()

        original_init(self)

    @wraps(original_init)
    def new_init(self, **kwargs):
        __init__(self, **kwargs)

    cls.__init__ = new_init

    sig = signature(__init__)
    params = [Parameter("self", Parameter.POSITIONAL_OR_KEYWORD, annotation=cls)]
    params += [
        Parameter(
            name=name,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=getattr(cls, name) if hasattr(cls, name) else Parameter.empty,
            annotation=annotation,
        )
        for name, annotation in class_annotations.items()
    ]
    sig = sig.replace(parameters=params, return_annotation=cls)
    __init__.__signature__ = sig
    setattr(cls, "__init__", __init__)

    # Make the class a DataObject type
    cls = type(cls.__name__, (DataObject, cls), {})
    DataObject._DataObject__types[cls.__name__] = cls

    # Create getters and setters for each field
    for field_name, field_type in class_annotations.items():
        setattr(
            cls,
            field_name,
            make_property(cls, field_name, field_type, DataObjectList, DataObjectSet),
        )

    def _check(obj, func, invert, values, callables):
        """
        Check if an object satisfies the query values and lambdas in 'filter' or 'exclude'.
        """
        if func(
            chain(
                ((getattr(obj, k) == v) for k, v in values.items()),
                (v(getattr(obj, k)) for k, v in callables.items()),
            )
        ):
            return not invert
        else:
            return invert

    @classmethod
    def get(cls, uuid: UUID) -> DataObject:
        return next(
            (
                obj
                for obj in cls.__DataObject_instances
                if obj.UUID == (UUID(uuid) if type(uuid) is str else uuid)
            ),
            None,
        )

    setattr(cls, "get", get)

    @classmethod
    def filter(
        cls, func=__builtins__["all"], objects=cls.__DataObject_instances, **kwargs
    ) -> DataObjectSet:
        values = {k: v for k, v in kwargs.items() if not callable(v)}
        callables = {k: v for k, v in kwargs.items() if callable(v)}
        return DataObjectSet(
            {
                obj
                for obj in objects
                if _check(obj, func, invert=False, values=values, callables=callables)
            }
        )

    setattr(cls, "filter", filter)

    @classmethod
    def exclude(
        cls, func=__builtins__["all"], objects=cls.__DataObject_instances, **kwargs
    ) -> DataObjectSet:
        values = {k: v for k, v in kwargs.items() if not callable(v)}
        callables = {k: v for k, v in kwargs.items() if callable(v)}
        return DataObjectSet(
            {
                obj
                for obj in objects
                if _check(obj, func, invert=True, values=values, callables=callables)
            }
        )

    setattr(cls, "exclude", exclude)

    @classmethod
    def all(cls) -> DataObjectSet:
        # return DataObjectSet(cls.__DataObject_instances)
        return cls.__DataObject_instances

    setattr(cls, "all", all)

    @classmethod
    def count(cls) -> int:
        return len(cls.__DataObject_instances)

    setattr(cls, "count", count)

    # Create a folder to store data objects of this type and load instances
    if cls.__DataObject_directory.exists():
        for file in cls.__DataObject_directory.iterdir():
            with file.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
                if isinstance(data, dict):
                    cls(**data, uuid=UUID(file.stem))
    else:
        cls.__DataObject_directory.mkdir()

    return cls
