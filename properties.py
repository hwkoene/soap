# Create properties for each field      
from datetime import datetime
from pathlib import Path
from typing import get_args, get_origin
from uuid import UUID


def make_property(cls, field_name: str, field_type: str | type):
    """Use the annotations to get the value of the field.

    Args:
        field_name (str): Name of the field to make the property for.
        field_type (str | type): Type hint for the field.

    Returns:
        Property: A property object to get and set the field value.
        
        
    """
            
    def setter(self, value):
        self.__DataObject_fields[field_name] = value
        self.save()
        
    def default_getter(self):
        return self.__DataObject_fields[field_name]

    def list_getter(self):
        # Determine if the list contains referces to other dataobjects (list[DataObject] or list['DataObject'])
        value_type = get_args(field_type)[0]
        if value_type in self._DataObject__types.keys():
            obj_get = cls._DataObject__types[value_type].get
        elif value_type in self._DataObject__types.values():
            obj_get = value_type.get
        else:
            obj_get = None
        
        if obj_get:
            if __builtins__['all'](isinstance(obj, (str, UUID)) for obj in self.__DataObject_fields[field_name]):
                self.__DataObject_fields[field_name] = [obj_get(item) for item in self.__DataObject_fields[field_name]]
                   
            outdated = False       
            for item in self.__DataObject_fields[field_name]:
                if item is None or getattr(item, '__DataObject_deleted'):
                    outdated = True
                    self.__DataObject_fields[field_name].remove(item)
            
            if outdated:
                self.save(check=False)
            
        return self.__DataObject_fields[field_name]
    
    def datetime_getter(self):
        value_type = type(self.__DataObject_fields[field_name])
        if value_type is float:
            self.__DataObject_fields[field_name] = datetime.fromtimestamp(self.__DataObject_fields[field_name])
        return self.__DataObject_fields[field_name]
    
    def path_getter(self):
        value_type = type(self.__DataObject_fields[field_name])
        if value_type is str:
            self.__DataObject_fields[field_name] = Path(self.__DataObject_fields[field_name])
        return self.__DataObject_fields[field_name]
        
    def dataobject_getter(self):
        if isinstance(self.__DataObject_fields[field_name], (str, UUID)):
            self.__DataObject_fields[field_name] = field_type.get(self.__DataObject_fields[field_name])
    
        if self.__DataObject_fields[field_name] is not None and self.__DataObject_fields[field_name].__DataObject_deleted:
            self.__DataObject_fields[field_name] = None
            self.save(check=False)
            return None
                
        return self.__DataObject_fields[field_name]
    
    def str_getter(self):
        field_value = self.__DataObject_fields[field_name]
        if field_type in self._DataObject__types.keys():
            if isinstance(field_value, (str, UUID)) :
                field_value = cls._DataObject__types[field_type].get(field_value)
            
            # if field_value is not None and field_value.__DataObject_deleted:
            if field_value is not None and field_value.__DataObject_deleted:
                self.__DataObject_fields[field_name] = None
                self.save(check=False)
                return None
        
        return field_value
    
    if isinstance(field_type, type):
        # Custom fields
        if field_type is datetime:
            return property(fget=datetime_getter, fset=setter)
            
        elif field_type is Path:
            return property(fget=path_getter, fset=setter)
        
        # Generic alias iterable fields
        elif get_origin(field_type) is list:
            return property(fget=list_getter, fset=setter)
            
        # DataObject
        elif field_type.__name__ in cls._DataObject__types.keys():
            return property(fget=dataobject_getter, fset=setter)
            
        # Resolve regular fields
        else:
            return property(fget=default_getter, fset=setter)
            
    # Generic alias iterable fields (Python 3.12)
    elif get_origin(field_type) is list:
        return property(fget=list_getter, fset=setter)
    
    # 'DataObject'
    elif isinstance(field_type, str):
        return property(fget=str_getter, fset=setter)

    else:
        return property(fget=default_getter, fset=setter)