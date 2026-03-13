from services.local_db import LocalDBManager

db = LocalDBManager('test_local.db')
db_id = db.add_item("movies/test", "http://test.com", "Test Title", "S01E01")
print(f"Added item with ID {db_id}")

items = db.get_all_items()
print("Items:", items)

success = db.delete_item(db_id)
print("Deleted?", success)

print("Items after delete:", db.get_all_items())
import os
os.remove('test_local.db')
