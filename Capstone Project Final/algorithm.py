"""
Algorithms Module
Demonstrates Merge Sort (Price sorting), Binary Search (ID lookup),
and Linear Search (Case-insensitive Name search).
"""


def merge_sort_by_price(products, reverse=False):
    """
    Recursively divides and sorts a list of product dictionaries by price.
    
    Time Complexity:
        - Best, Average, Worst: O(n log n)
        - Divide phase splits list in halves: O(log n) levels of recursion.
        - Conquer/Merge phase merges subarrays: O(n) work per level.
    Space Complexity:
        - O(n) auxiliary memory for merged sublists.
        
    Parameters:
        products (list): List of product dicts with 'price' key.
        reverse (bool): If True, sorts descending; otherwise ascending.
    """
    if len(products) <= 1:
        return list(products)

    mid = len(products) // 2
    left_half = merge_sort_by_price(products[:mid], reverse=reverse)
    right_half = merge_sort_by_price(products[mid:], reverse=reverse)

    return _merge(left_half, right_half, reverse=reverse)


def _merge(left, right, reverse=False):
    """Helper function to merge two sorted lists into one sorted list."""
    sorted_list = []
    i = 0  # Pointer for left list
    j = 0  # Pointer for right list

    while i < len(left) and j < len(right):
        if not reverse:
            # Ascending
            condition = left[i]['price'] <= right[j]['price']
        else:
            # Descending
            condition = left[i]['price'] >= right[j]['price']

        if condition:
            sorted_list.append(left[i])
            i += 1
        else:
            sorted_list.append(right[j])
            j += 1

    sorted_list.extend(left[i:])
    sorted_list.extend(right[j:])
    return sorted_list


def binary_search_by_id(sorted_products, target_id):
    """
    Performs binary search on a list of products pre-sorted by 'id'.
    
    Time Complexity:
        - Best: O(1) when target is at exact midpoint.
        - Average / Worst: O(log n) halving search space on each iteration.
    Space Complexity:
        - O(1) auxiliary iterative space.
        
    Academic Note / Viva Defense:
        SQLite already indexes PRIMARY KEY 'product_id' using a B-Tree,
        enabling the DBMS engine to locate any product in O(log n) time.
        We provide this Python binary search implementation to demonstrate
        algorithmic divide-and-conquer on in-memory structured arrays.
        Prerequisite: The input array must strictly be sorted by 'id'.
    """
    low = 0
    high = len(sorted_products) - 1

    while low <= high:
        mid = (low + high) // 2
        mid_id = sorted_products[mid]['id']

        if mid_id == target_id:
            return sorted_products[mid]
        elif mid_id < target_id:
            low = mid + 1
        else:
            high = mid - 1

    return None


def linear_search_by_name(products, query):
    """
    Performs case-insensitive substring linear search on product names.
    
    Time Complexity:
        - Best: O(1) match on first element.
        - Worst / Average: O(n * m) where n is catalog size and m is average name length.
    Space Complexity:
        - O(k) where k is the number of matching results returned.
        
    Academic Note / Viva Defense:
        While SQL 'SELECT * FROM Products WHERE LOWER(name) LIKE ?' achieves
        similar results using database query planning, linear search in Python
        demonstrates algorithmic sequential scanning for unindexed arbitrary
        substring matches over in-memory collections.
    """
    if not query:
        return list(products)

    cleaned_query = query.strip().lower()
    matches = []
    for product in products:
        if cleaned_query in product['name'].lower():
            matches.append(product)
    return matches


if __name__ == "__main__":
    test_catalog = [
        {"id": 5, "name": "Gaming Monitor", "price": 18500.0, "stock": 8},
        {"id": 2, "name": "Wireless Mouse", "price": 1200.0, "stock": 25},
        {"id": 1, "name": "Mechanical Keyboard", "price": 3500.0, "stock": 15},
        {"id": 4, "name": "USB-C Hub", "price": 1800.0, "stock": 30},
        {"id": 3, "name": "Headphones", "price": 6500.0, "stock": 10}
    ]

    print("--- 1. Testing Merge Sort (Ascending) ---")
    for item in merge_sort_by_price(test_catalog, reverse=False):
        print(f"Rs {item['price']:<8.2f} -> {item['name']}")

    print("\n--- 2. Testing Merge Sort (Descending) ---")
    for item in merge_sort_by_price(test_catalog, reverse=True):
        print(f"Rs {item['price']:<8.2f} -> {item['name']}")

    print("\n--- 3. Testing Binary Search (Find Product by ID) ---")
    sorted_by_id = sorted(test_catalog, key=lambda x: x['id'])
    target = 4
    result = binary_search_by_id(sorted_by_id, target)
    print(f"Found ID {target}: {result['name'] if result else 'Not found'}")

    print("\n--- 4. Testing Linear Search by Name ---")
    name_query = "mo"
    matches = linear_search_by_name(test_catalog, name_query)
    print(f"Matches for '{name_query}': {[m['name'] for m in matches]}")