from datetime import timedelta

def daterange(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)