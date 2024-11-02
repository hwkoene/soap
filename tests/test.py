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

from itertools import chain
from pathlib import Path
import unittest
from src.dataobject import dataobject
import random
import string
from datetime import datetime, timedelta
import calendar
import pytz

@dataobject
class TestObjectA:
    name: str
    value: int
    ref_b: 'TestObjectB' = None
    ref_c_list: list['TestObjectC'] = []
    true_or_false: bool = False
    what_happens: set = {1, 5, 6}

@dataobject
class TestObjectB:
    code: str
    timestamp: datetime = datetime.now()
    ref_a: TestObjectA = None
    ref_d_list: list['TestObjectD'] = []
    path_list: list[Path] = []

@dataobject
class TestObjectC:
    active: bool
    tags: list[str]
    ref_b_list: list[TestObjectB] = []
    ref_a: TestObjectA = None
    something: dict = {}

@dataobject
class TestObjectD:
    priority: int
    description: str
    ref_b: TestObjectB = None
    path: Path = Path(".")
    datetime_list: list[datetime] = []


class TestDataObjectSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create random instances
        for _ in range(20):
            TestObjectA(name=random.choice(string.ascii_uppercase), 
                        value=random.randint(1, 100))
        
        for _ in range(15):
            TestObjectB(code=''.join(random.choices(string.ascii_lowercase, k=5)),
                        timestamp=datetime.now() + timedelta(days=random.randint(-100, 100)))
        
        for _ in range(25):
            TestObjectC(active=random.choice([True, False]),
                        tags=random.sample(string.ascii_lowercase, random.randint(1, 5)),
                        # TODO: Encode sets
                        something={"abc": [1, 2, (True, False)]})
                        # something={''.join(random.choices(string.ascii_letters, k=20)): random.randint(0, 100)})
        
        for _ in range(10):
            TestObjectD(priority=random.randint(3, 10),
                        description=''.join(random.choices(string.ascii_letters, k=20)))
            
        print(f'Test size: DataObject.count()')
            
        # Assign random references
        for obj_a in TestObjectA.all():
            obj_a.ref_b = TestObjectB.all().sample(1)[0]
            obj_a.ref_c_list = TestObjectC.all().sample(random.randint(1, 5))
        
        for obj_b in TestObjectB.all():
            obj_b.ref_a = TestObjectA.all().sample(1)[0]
            obj_b.ref_d_list = TestObjectD.all().sample(random.randint(0, TestObjectD.count()))
            obj_b.path_list = [obj.PATH for obj in random.sample(list(chain(TestObjectA.all(), TestObjectC.all(), TestObjectD.all())), random.randint(0, 50))]        

        for obj_c in TestObjectC.all():
            obj_c.ref_a = TestObjectA.all().sample(1)[0]
            obj_c.ref_b_list = TestObjectB.all().sample(random.randint(0, TestObjectB.count()))
        

        def random_date():
            year = random.randint(1, 9999)  # Datetime supports years 1-9999
            month = random.randint(1, 12)
            
            # Get the last day of the selected month
            _, last_day = calendar.monthrange(year, month)
            
            day = random.randint(1, last_day)
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            microsecond = random.randint(0, 999999)
            
            return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=pytz.UTC)
        
        for obj_d in TestObjectD.all():
            obj_d.ref_b = TestObjectB.all().sample(1)[0]
            obj_d.datetime_list = [random_date()]*3
            
    # @classmethod
    # def tearDownClass(cls):
    #     for obj in list(TestObjectA.all()):
    #         obj.delete()
        
    #     for obj in list(TestObjectB.all()):
    #         obj.delete()
        
    #     for obj in list(TestObjectC.all()):
    #         obj.delete()
        
    #     for obj in list(TestObjectD.all()):
    #         obj.delete()

    def test_reference_integrity(self):
        for obj_a in TestObjectA.all():
            self.assertIsInstance(obj_a.ref_b, TestObjectB)
            self.assertTrue(all(isinstance(obj, TestObjectC) for obj in obj_a.ref_c_list))

    def test_filter_basic(self):
        # Test filtering TestObjectA by value
        filtered_a = TestObjectA.filter(value=lambda x: x > 50)
        self.assertTrue(all(obj.value > 50 for obj in filtered_a))

        # Test filtering TestObjectB by timestamp
        one_month_ago = datetime.now() - timedelta(days=30)
        filtered_b = TestObjectB.filter(timestamp=lambda t: t > one_month_ago)
        self.assertTrue(all(obj.timestamp > one_month_ago for obj in filtered_b))

    def test_filter_complex(self):
        # Test filtering TestObjectC by active status and tag count
        filtered_c = TestObjectC.filter(active=True, tags=lambda t: len(t) > 2)
        TestObjectB.filter(objects=list(filtered_c)[0].ref_b_list, timestamp=lambda ts: ts < datetime.now())
        obj_to_append = TestObjectB.all().sample(1)[0]
        list(filtered_c)[0].ref_b_list.append(obj_to_append)
        list(filtered_c)[0].ref_b_list.reverse()
        obj_to_remove = random.choice(list(filtered_c)[0].ref_b_list)
        list(filtered_c)[0].ref_b_list.remove(obj_to_remove)
        self.assertTrue(all(obj.active and len(obj.tags) > 2 for obj in filtered_c))

        # Test filtering TestObjectD by priority and reference to TestObjectB
        filtered_d = TestObjectD.filter(ref_b=lambda b: b.code.startswith('a'))
        # extra_filtered_d = filtered_d.exclude(priority=lambda x: x < 3).sort(key=lambda obj: obj.datetime_list[0])
        extra_filtered_d = sorted(filtered_d.exclude(priority=lambda x: x < 3), key=lambda obj: obj.datetime_list[0])
        
        self.assertTrue(all(obj.priority >= 3 and obj.ref_b.code.startswith('a') for obj in extra_filtered_d))

    def test_exclude_basic(self):
        # Test excluding TestObjectA by value
        excluded_a = TestObjectA.exclude(value=lambda x: x <= 50)
        self.assertTrue(all(obj.value > 50 for obj in excluded_a))

        # Test excluding TestObjectB by timestamp
        one_month_ago = datetime.now() - timedelta(days=30)
        excluded_b = TestObjectB.exclude(timestamp=lambda t: t <= one_month_ago)
        self.assertTrue(all(obj.timestamp > one_month_ago for obj in excluded_b))

    def test_exclude_complex(self):
        # Test excluding TestObjectC by active status and tag count
        excluded_c = TestObjectC.exclude(active=False, tags=lambda t: len(t) <= 2)
        self.assertTrue(all(obj.active or len(obj.tags) > 2 for obj in excluded_c))

        # Test excluding TestObjectD by priority and reference to TestObjectB
        excluded_d = TestObjectD.exclude(priority=lambda p: p <= 3, ref_b=lambda b: not b.code.startswith('a'))
        self.assertTrue(all(obj.priority > 3 or obj.ref_b.code.startswith('a') for obj in excluded_d))

    def test_chained_filtering(self):
        # Test chained filtering across multiple object types
        high_value_a = TestObjectA.filter(value=lambda x: x > 75)
        related_c = TestObjectC.filter(ref_a=lambda a: a in high_value_a)
        self.assertTrue(all(obj.ref_a.value > 75 for obj in related_c))

    def test_get_by_uuid(self):
        obj_a = TestObjectA.all().sample(1)[0]
        retrieved_obj = TestObjectA.get(obj_a.UUID)
        self.assertEqual(obj_a, retrieved_obj)

    def test_delete(self):
        obj_to_delete = TestObjectA.all().sample(1)[0]
        obj_with_ref_to_deleted = TestObjectB.all().sample(1)[0]
        obj_with_ref_to_deleted.ref_a = obj_to_delete
        obj_to_delete.delete()
        # NOTE: The refernce gets deleted with the first property get call to the attribute
        # self.assertIsNone(getattr(obj_with_ref_to_deleted, '__DataObject_fields')['ref_a'])
        self.assertIsNone(TestObjectA.get(obj_to_delete))
        self.assertIsNone(obj_with_ref_to_deleted.ref_a)
        
        obj_with_ref_list_to_deleted = TestObjectA.filter(ref_c_list=lambda x: len(x) > 1).sample(1)[0]
        obj_to_delete = random.sample(obj_with_ref_list_to_deleted.ref_c_list, 1)[0]
        obj_to_delete.delete()
        # NOTE: The refernce gets deleted with the first property get call to the attribute
        # self.assertNotIn(obj_to_delete, getattr(obj_with_ref_list_to_deleted, '__DataObject_fields')['ref_c_list'])
        self.assertNotIn(obj_to_delete, getattr(obj_with_ref_list_to_deleted, 'ref_c_list'))
        self.assertNotIn(obj_to_delete, obj_with_ref_list_to_deleted.ref_c_list)
        
    def test_custom_fields(self):
        # Path
        obj_with_path = TestObjectD.all().sample(1)[0]
        self.assertIsInstance(obj_with_path.path, Path)
        obj_with_path_list = TestObjectB.all().sample(1)[0]
        self.assertTrue(all(isinstance(path, Path) for path in obj_with_path_list.path_list))
        
        # datetime
        obj_with_datetime = TestObjectB.all().sample(1)[0]
        self.assertIsInstance(obj_with_datetime.timestamp, datetime)
        obj_with_datetime_list = TestObjectD.all().sample(1)[0]
        self.assertTrue(all(isinstance(timestamp, datetime) for timestamp in obj_with_datetime_list.datetime_list))


if __name__ == '__main__':
    unittest.main()
    
    