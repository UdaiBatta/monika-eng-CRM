import re


def _key(value):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", str(value))


def company_group(company_id):
    return f"company.{_key(company_id)}"


def user_group(user_id):
    return f"user.{_key(user_id)}"


def entity_group(entity_type, entity_id):
    return f"entity.{_key(entity_type)}.{_key(entity_id)}"
