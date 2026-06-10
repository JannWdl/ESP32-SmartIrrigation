import gc

# Früh Garbage Collector aktivieren. threshold wird nur gesetzt, wenn die Firmware es unterstützt.
gc.enable()
try:
    gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())
except Exception:
    pass
