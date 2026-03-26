import os, base64
B = "/c/Users/Zacha/OneDrive/Desktop/Projects/builder"
def w(p, c):
    fp = os.path.join(B, p)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w").write(c)
    print("  " + p)
