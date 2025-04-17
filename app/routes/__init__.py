def nl2br(value):
    if not value:
        return ""
    return value.replace('\n', '<br>')