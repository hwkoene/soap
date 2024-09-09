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

from datetime import datetime
from pathlib import Path
import random
from src.dataobject import dataobject

@dataobject
class MyClassA:
    name: str
    health: int = 100
    my_path: Path = None
    inventory: list['MyClassB'] = []
    
@dataobject
class MyClassB:
    daddy: MyClassA
    other_items: list
    timestamp: datetime
    problems: int = random.randint(0, 99)
    
a1 = MyClassA(name="Benjamin Franklin")
a2 = MyClassA(name="Steve Jobs")

b1 = MyClassB(daddy=a1, 
              timestamp=datetime.now(), 
              other_items=['Some cheese', 'Bud light'])
b2 = MyClassB(daddy=a2, 
              timestamp=b1.timestamp, 
              other_items=[b1])

a1.inventory.append(b1)
a1.inventory = [b1, b1, b1]
# a1.save()
a2.inventory.append(b2)
# a2.save()

ben_is_my_daddy = MyClassB.filter(daddy=lambda x: x.name.startswith('Ben'))
steve_is_my_daddy = MyClassB.exclude(daddy=lambda x: not x.name.startswith('Steve'))

# print(ben_is_my_daddy is steve_is_my_daddy)