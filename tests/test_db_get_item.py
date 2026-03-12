
import os
import sys

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.local_db import LocalDBManager

def test_get_item():
    db_path = "test_local_data.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    manager = LocalDBManager(db_path)
    
    # 1. Add an item
    item_id = manager.add_item("test/path", "http://image.url", "Test Title", "Season 1", 0)
    print(f"Added item with ID: {item_id}")
    
    # 2. Retrieve the item
    item = manager.get_item(item_id)
    print(f"Retrieved item: {item}")
    
    # 3. Assertions
    assert item["id"] == item_id
    assert item["title"] == "Test Title"
    assert item["relative_path"] == "test/path"
    
    # 4. Non-existent item
    empty_item = manager.get_item(999)
    print(f"Retrieved non-existent item: {empty_item}")
    assert empty_item == {}
    
    print("Verification successful!")
    
    # Cleanup
    os.remove(db_path)

if __name__ == "__main__":
    try:
        test_get_item()
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)
