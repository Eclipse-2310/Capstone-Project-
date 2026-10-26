"""
Data Structures Module
Demonstrates Stack, Queue, and Singly Linked List implementations
for E-Commerce Cart, Warehouse Dispatch, and Milestone Tracking.
"""

from collections import deque


class CreateStack:
    """
    LIFO (Last-In, First-Out) Stack for Shopping Cart management and item undo.
    Time Complexity:
        - push: O(1)
        - pop: O(1)
        - peek: O(1)
        - is_empty: O(1)
        - get_total_price: O(k) where k is number of items in cart
    """

    def __init__(self):
        self.item = []

    def push(self, product):
        """Pushes a product dictionary onto the cart stack."""
        self.item.append(product)

    def pop(self):
        """Pops and returns the most recently added product from the stack."""
        if not self.is_empty():
            return self.item.pop()
        return None

    def peek(self):
        """Returns the top item without removing it."""
        if not self.is_empty():
            return self.item[-1]
        return None

    def is_empty(self):
        """Checks if the stack has zero elements."""
        return len(self.item) == 0

    def get_total_price(self):
        """Calculates cumulative price for all items in the stack."""
        return round(sum(item['price'] * item['quantity'] for item in self.item), 2)

    def clear(self):
        """Clears all items from the stack."""
        self.item = []

    def get_items(self):
        """Returns a copy of all items in insertion order."""
        return list(self.item)


class DispatchQueue:
    """
    FIFO (First-In, First-Out) Queue for warehouse dispatch order processing.
    Implemented using collections.deque for true O(1) enqueue and dequeue.
    
    Academic Note / Viva Defense:
        Python list.pop(0) is O(n) because shifting all remaining elements
        in contiguous memory takes linear time. collections.deque provides a
        doubly linked list of fixed-size blocks guaranteeing O(1) append and
        O(1) popleft, strictly matching the formal theoretical definition of a Queue.
    """

    def __init__(self):
        self.queue = deque()

    def enqueue(self, order_id):
        """Enqueues an order_id at the rear of the queue in O(1) time."""
        self.queue.append(order_id)

    def dequeue(self):
        """Dequeues and returns the front order_id in O(1) time."""
        if not self.is_empty():
            return self.queue.popleft()
        return None

    def peek(self):
        """Returns the front order_id without removing it in O(1) time."""
        if not self.is_empty():
            return self.queue[0]
        return None

    def is_empty(self):
        """Checks if the queue is empty in O(1) time."""
        return len(self.queue) == 0

    def size(self):
        """Returns count of orders in the queue in O(1) time."""
        return len(self.queue)

    def to_list(self):
        """Returns orders as a standard Python list from front to rear."""
        return list(self.queue)

    def remove(self, order_id):
        """
        Removes a specific cancelled order from anywhere in the queue.
        Time Complexity: O(n) scan.
        """
        try:
            self.queue.remove(order_id)
            return True
        except ValueError:
            return False


class StatusNode:
    """Singly Linked List node representing an order processing milestone."""

    def __init__(self, stage_name):
        self.stage_name = stage_name
        self.next = None


class OrderTracker:
    """
    Singly Linked List tracking linear milestones in an order lifecycle.
    Milestones: Placed -> Order Confirmed -> Packed -> Dispatched -> Delivered
    
    Academic Note / Viva Defense:
        A singly linked list models fixed sequential state machines where transitions
        are strictly unidirectional. Pointer traversal moves forward to retrieve the
        immediate successor stage in O(k) steps without arbitrary random index jumps.
    """

    def __init__(self):
        milestones = [
            "Placed",
            "Order Confirmed",
            "Packed",
            "Dispatched",
            "Delivered"
        ]
        self.head = StatusNode(milestones[0])
        current = self.head
        for stage in milestones[1:]:
            current.next = StatusNode(stage)
            current = current.next

    def get_next_stage(self, current_stage):
        """Traverses linked list from head to locate next sequential milestone."""
        temp = self.head
        while temp is not None and temp.stage_name != current_stage:
            temp = temp.next

        if temp is not None and temp.next is not None:
            return temp.next.stage_name
        return None

    def get_all_stages(self):
        """Traverses the linked list from head to tail and returns all stages in order."""
        stages = []
        temp = self.head
        while temp is not None:
            stages.append(temp.stage_name)
            temp = temp.next
        return stages


if __name__ == "__main__":
    print("--- 1. Testing Stack (Cart Undo) ---")
    cart = CreateStack()
    cart.push({"id": 1, "name": "Mechanical Keyboard", "price": 3500.0, "quantity": 1})
    cart.push({"id": 2, "name": "Wireless Mouse", "price": 1200.0, "quantity": 2})
    print(f"Cart total: Rs {cart.get_total_price():.2f}")

    popped = cart.pop()
    print(f"Undid item: {popped['name']}")
    print(f"New cart total: Rs {cart.get_total_price():.2f}\n")

    print("--- 2. Testing Queue (Dispatch FIFO with O(1) Deque) ---")
    dispatch = DispatchQueue()
    dispatch.enqueue(101)
    dispatch.enqueue(102)
    print(f"Queue size: {dispatch.size()}")
    print(f"Next to dispatch: {dispatch.dequeue()}")  # 101
    print(f"Next to dispatch: {dispatch.dequeue()}\n")  # 102

    print("--- 3. Testing Linked List (Milestone Tracker) ---")
    tracker = OrderTracker()
    print("All stages:", " -> ".join(tracker.get_all_stages()))
    stage = "Placed"
    print(f"Initial status: {stage}")
    while stage:
        next_stage = tracker.get_next_stage(stage)
        if next_stage:
            print(f"Advancing -> {next_stage}")
        stage = next_stage