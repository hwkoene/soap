"""
The SOAP package provides a single-decorator solution to persist Python objects.
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

from datetime import datetime
from pathlib import Path
from typing import get_args, get_origin
from uuid import UUID


def make_property(
    cls,
    field_name: str,
    field_type: str | type,
    entity_list_class: type,
    entity_set_class: type,
):
    """Use the annotations to get the value of the field.

    Args:
        field_name (str): Name of the field to make the property for.
        field_type (str | type): Type hint for the field.

    Returns:
        Property: A property object to get and set the field value.


    """

    def default_setter(self, value):
        self.__Entity_fields[field_name] = value
        self.save()

    def default_getter(self):
        return self.__Entity_fields[field_name]

    def list_setter(self, value):
        self.__Entity_fields[field_name] = entity_list_class(value)
        setattr(self.__Entity_fields[field_name], "__container__", self)
        self.save()

    def list_getter(self):
        # Determine if the list contains referces to other entities (list[Entity] or list['Entity'])
        value_type = get_args(field_type)[0]
        if value_type in self._Entity__types.keys():
            obj_get = cls._Entity__types[value_type].get
        elif value_type in self._Entity__types.values():
            obj_get = value_type.get
        else:
            obj_get = None

        if obj_get:
            if __builtins__["all"](
                isinstance(obj, (str, UUID))
                for obj in self.__Entity_fields[field_name]
            ):
                self.__Entity_fields[field_name] = entity_list_class(
                    [obj_get(item) for item in self.__Entity_fields[field_name]]
                )
                setattr(self.__Entity_fields[field_name], "__container__", self)

            outdated = False
            for item in self.__Entity_fields[field_name]:
                if item is None or getattr(item, "__Entity_deleted"):
                    outdated = True
                    self.__Entity_fields[field_name].remove(item)

            if outdated:
                self.save(check=False)

        return self.__Entity_fields[field_name]

    def set_setter(self, value):
        self.__Entity_fields[field_name] = entity_set_class(value)
        setattr(self.__Entity_fields[field_name], "__container__", self)
        self.save()

    # TODO: Generalise and allow for custom types
    def set_getter(self):
        # Determine if the list contains referces to other entities (list[Entity] or list['Entity'])
        value_type = get_args(field_type)[0]
        if value_type in self._Entity__types.keys():
            obj_get = cls._Entity__types[value_type].get
        elif value_type in self._Entity__types.values():
            obj_get = value_type.get
        else:
            obj_get = None

        if obj_get:
            if __builtins__["all"](
                isinstance(obj, (str, UUID))
                for obj in self.__Entity_fields[field_name]
            ):
                self.__Entity_fields[field_name] = entity_set_class(
                    {obj_get(item) for item in self.__Entity_fields[field_name]}
                )
                setattr(self.__Entity_fields[field_name], "__container__", self)

            outdated = False
            for item in self.__Entity_fields[field_name]:
                if item is None or getattr(item, "__Entity_deleted"):
                    outdated = True
                    self.__Entity_fields[field_name].remove(item)

            if outdated:
                self.save(check=False)

        return self.__Entity_fields[field_name]

    # TODO: Generalise and allow for custom types
    def datetime_getter(self):
        value_type = type(self.__Entity_fields[field_name])
        if value_type is float:
            self.__Entity_fields[field_name] = datetime.fromtimestamp(
                self.__Entity_fields[field_name]
            )
        return self.__Entity_fields[field_name]

    def path_getter(self):
        value_type = type(self.__Entity_fields[field_name])
        if value_type is str:
            self.__Entity_fields[field_name] = Path(
                self.__Entity_fields[field_name]
            )
        return self.__Entity_fields[field_name]

    def entities_getter(self):
        if isinstance(self.__Entity_fields[field_name], (str, UUID)):
            self.__Entity_fields[field_name] = field_type.get(
                self.__Entity_fields[field_name]
            )

        if (
            self.__Entity_fields[field_name] is not None
            and self.__Entity_fields[field_name].__Entity_deleted
        ):
            self.__Entity_fields[field_name] = None
            self.save(check=False)
            return None

        return self.__Entity_fields[field_name]

    def str_getter(self):
        field_value = self.__Entity_fields[field_name]
        if field_type in self._Entity__types.keys():
            if isinstance(field_value, (str, UUID)):
                field_value = cls._Entity__types[field_type].get(field_value)

            # if field_value is not None and field_value.__Entity_deleted:
            if field_value is not None and field_value.__Entity_deleted:
                self.__Entity_fields[field_name] = None
                self.save(check=False)
                return None

        return field_value

    if isinstance(field_type, type):
        # Custom fields
        if field_type is datetime:
            return property(fget=datetime_getter, fset=default_setter)

        elif field_type is Path:
            return property(fget=path_getter, fset=default_setter)

        # Generic alias iterable fields
        elif get_origin(field_type) is list:
            return property(fget=list_getter, fset=list_setter)

        # Generic alias iterable fields
        elif get_origin(field_type) is set:
            return property(fget=set_getter, fset=set_setter)

        # Entity
        elif field_type.__name__ in cls._Entity__types.keys():
            return property(fget=entities_getter, fset=default_setter)

        # Resolve regular fields
        else:
            return property(fget=default_getter, fset=default_setter)

    # Generic alias iterable fields (Python 3.12)
    elif get_origin(field_type) is list:
        return property(fget=list_getter, fset=list_setter)

    # Generic alias iterable fields (Python 3.12)
    elif get_origin(field_type) is set:
        return property(fget=set_getter, fset=set_setter)

    # 'Entity'
    elif isinstance(field_type, str):
        return property(fget=str_getter, fset=default_setter)

    else:
        return property(fget=default_getter, fset=default_setter)
