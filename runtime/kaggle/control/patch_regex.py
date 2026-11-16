"""One-off repair: the two v3c2 regexes in template.py lost their backslash escapes. Rebuilds them with explicit backslash characters."""
import pathlib

BS = chr(92)
p = pathlib.Path("runtime/kaggle/control/template.py")
L = p.read_text(encoding="utf-8").split("\n")
fixed = 0
for i, l in enumerate(L):
    if l.startswith("IDRE = re.compile("):
        L[i] = 'IDRE = re.compile(r"(?<!@)' + BS + "b[BD]" + BS + "d{1,2}" + BS + 'b")'
        fixed += 1
    elif l.startswith("        body = re.sub(r") and "(?<!@)" in l:
        L[i] = ('        body = re.sub(r"' + BS + "s*[" + BS + "(" + BS + "[]?(?<!@)" + BS + "b[BD]" + BS + "d{1,2}" + BS + "b[" + BS + ")" + BS + "]]?[:,]?\", \"\", body).strip()")
        fixed += 1
p.write_text("\n".join(L), encoding="utf-8", newline="\n")
print("fixed lines:", fixed)
