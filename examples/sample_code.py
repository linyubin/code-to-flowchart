def select_records(records, config):
    min_score = config.get("min_score", 50)
    max_items = config.get("max_items", 0)
    valid = select_valid(records, min_score)
    if not valid:
        return []
    if max_items > 0:
        valid = valid[:max_items]
    return valid


def select_valid(records, min_score):
    if not records:
        return []
    return [item for item in records if item.score >= min_score]
