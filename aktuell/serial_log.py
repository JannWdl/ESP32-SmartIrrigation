DEBUG = True


def log(msg):
    if DEBUG:
        try:
            print("[IRR] " + str(msg))
        except Exception:
            pass
