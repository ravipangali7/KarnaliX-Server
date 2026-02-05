"""
Live chat permission helpers.
Hierarchy: POWERHOUSE → SUPER → MASTER → USER
"""


def can_chat_with(user_a, user_b):
    """
    Check if user_a is allowed to have a live chat conversation with user_b.
    - USER: only with parent (master)
    - MASTER: with parent (super) or direct children (users)
    - SUPER: with direct children (masters)
    - POWERHOUSE: with direct children (supers)
    """
    if user_a is None or user_b is None:
        return False
    if not getattr(user_a, 'is_authenticated', True):
        return False
    if getattr(user_a, 'id', None) == getattr(user_b, 'id', None):
        return False

    role_a = getattr(user_a, 'role', None)
    role_b = getattr(user_b, 'role', None)
    if not role_a or not role_b:
        return False

    parent_a_id = getattr(user_a, 'parent_id', None) or (user_a.parent.id if getattr(user_a, 'parent', None) else None)
    parent_b_id = getattr(user_b, 'parent_id', None) or (user_b.parent.id if getattr(user_b, 'parent', None) else None)

    if role_a == 'USER':
        return user_b.id == parent_a_id

    if role_a == 'MASTER':
        if user_b.id == parent_a_id:
            return True
        return parent_b_id == user_a.id and role_b == 'USER'

    if role_a == 'SUPER':
        return parent_b_id == user_a.id and role_b == 'MASTER'

    if role_a == 'POWERHOUSE':
        return parent_b_id == user_a.id and role_b == 'SUPER'

    return False
