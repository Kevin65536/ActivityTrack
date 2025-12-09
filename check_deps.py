
try:
    import numpy
    import scipy.ndimage
    print("Imports successful")
except ImportError as e:
    print(f"Import failed: {e}")
