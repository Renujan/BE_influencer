import re

with open("user/serializers.py", "r") as f:
    content = f.read()

content = content.replace('"country", "province", "district", "district",', '"country", "province", "district",')

with open("user/serializers.py", "w") as f:
    f.write(content)
