"""
Unit Tests for Data Structures and Algorithms Module
Verifies:
    - CreateStack (LIFO, push, pop, peek, get_total_price, clear)
    - DispatchQueue (FIFO, O(1) operations, removal)
    - OrderTracker (Linked list traversal, next stage)
    - Merge Sort (Ascending and Descending)
    - Binary Search (Existing, non-existent, boundary IDs)
    - Linear Search (Case-insensitive substring search)
"""

import pytest
from data_structures import CreateStack, DispatchQueue, OrderTracker
from algorithm import merge_sort_by_price, binary_search_by_id, linear_search_by_name


def test_stack_lifo_and_total_price():
    cart = CreateStack()
    assert cart.is_empty() is True

    cart.push({"id": 1, "name": "Laptop", "price": 1000.0, "quantity": 1})
    cart.push({"id": 2, "name": "Mouse", "price": 50.0, "quantity": 2})

    assert cart.is_empty() is False
    assert cart.peek()["name"] == "Mouse"
    assert cart.get_total_price() == 1100.0

    popped = cart.pop()
    assert popped["name"] == "Mouse"
    assert cart.get_total_price() == 1000.0
    assert cart.peek()["name"] == "Laptop"

    cart.clear()
    assert cart.is_empty() is True
    assert cart.pop() is None


def test_dispatch_queue_fifo_and_removal():
    queue = DispatchQueue()
    assert queue.is_empty() is True

    queue.enqueue(101)
    queue.enqueue(102)
    queue.enqueue(103)

    assert queue.size() == 3
    assert queue.peek() == 101

    # Remove non-head element
    removed = queue.remove(102)
    assert removed is True
    assert queue.size() == 2

    # FIFO ordering holds
    assert queue.dequeue() == 101
    assert queue.dequeue() == 103
    assert queue.is_empty() is True
    assert queue.dequeue() is None


def test_order_tracker_linked_list_traversal():
    tracker = OrderTracker()
    stages = tracker.get_all_stages()
    assert stages == ["Placed", "Order Confirmed", "Packed", "Dispatched", "Delivered"]

    assert tracker.get_next_stage("Placed") == "Order Confirmed"
    assert tracker.get_next_stage("Order Confirmed") == "Packed"
    assert tracker.get_next_stage("Packed") == "Dispatched"
    assert tracker.get_next_stage("Dispatched") == "Delivered"
    assert tracker.get_next_stage("Delivered") is None
    assert tracker.get_next_stage("Unknown") is None


def test_merge_sort_ascending_and_descending():
    items = [
        {"id": 1, "name": "Monitor", "price": 150.0},
        {"id": 2, "name": "Mouse", "price": 20.0},
        {"id": 3, "name": "Laptop", "price": 1200.0},
        {"id": 4, "name": "Keyboard", "price": 75.0}
    ]

    asc = merge_sort_by_price(items, reverse=False)
    assert [p["price"] for p in asc] == [20.0, 75.0, 150.0, 1200.0]

    desc = merge_sort_by_price(items, reverse=True)
    assert [p["price"] for p in desc] == [1200.0, 150.0, 75.0, 20.0]


def test_binary_search_by_id():
    sorted_items = [
        {"id": 1, "name": "A"},
        {"id": 3, "name": "B"},
        {"id": 5, "name": "C"},
        {"id": 7, "name": "D"},
        {"id": 9, "name": "E"}
    ]

    assert binary_search_by_id(sorted_items, 1)["name"] == "A"
    assert binary_search_by_id(sorted_items, 5)["name"] == "C"
    assert binary_search_by_id(sorted_items, 9)["name"] == "E"
    assert binary_search_by_id(sorted_items, 4) is None
    assert binary_search_by_id(sorted_items, 10) is None


def test_linear_search_by_name():
    catalog = [
        {"id": 1, "name": "Mechanical Gaming Keyboard"},
        {"id": 2, "name": "Wireless Optical Mouse"},
        {"id": 3, "name": "Gaming Laptop Pro"},
        {"id": 4, "name": "USB-C to HDMI Adapter"}
    ]

    res1 = linear_search_by_name(catalog, "gaming")
    assert len(res1) == 2
    assert {p["id"] for p in res1} == {1, 3}

    res2 = linear_search_by_name(catalog, "ADAPTER")
    assert len(res2) == 1
    assert res2[0]["id"] == 4

    res3 = linear_search_by_name(catalog, "nonexistent")
    assert len(res3) == 0
