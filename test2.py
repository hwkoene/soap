from datetime import datetime
from pathlib import Path
import random
from dataobject import dataobject

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
a1.save()
a2.inventory.append(b2)
a2.save()

ben_is_my_daddy = MyClassB.filter(daddy=lambda x: x.name.startswith('Ben'))
steve_is_my_daddy = MyClassB.exclude(daddy=lambda x: not x.name.startswith('Steve'))

print(ben_is_my_daddy is steve_is_my_daddy)