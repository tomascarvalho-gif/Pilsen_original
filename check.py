with open("visualizer.py", "r") as f:
    text = f.read()

lines = text.split("\n")
stack = []
for i, line in enumerate(lines):
    # Skip string contents to avoid false positives
    in_string = False
    string_char = None
    for j, char in enumerate(line):
        if char in ["'", '"']:
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
            continue
            
        if in_string: continue
        
        if char in "([{":
            stack.append((char, i+1))
        elif char in ")]}":
            if not stack:
                print(f"Error: closing {char} at line {i+1} with no opening bracket")
                exit(1)
            
            last_char, last_line = stack.pop()
            pairs = {"(": ")", "[": "]", "{": "}"}
            if char != pairs[last_char]:
                print(f"Syntax Error! Line {i+1} character '{char}' is trying to close '{last_char}' from line {last_line}")
                for ln in range(last_line-2, i+2):
                    if 0 <= ln < len(lines):
                        print(f"{ln+1}: {lines[ln]}")
                exit(1)

print("All matched!")
