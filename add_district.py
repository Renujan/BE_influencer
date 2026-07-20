with open("user/models.py", "r") as f:
    content = f.read()

target = '    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")\n'
replacement = '    province = models.ForeignKey(Province, on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")\n    district = models.ForeignKey("District", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")\n'

if target in content and 'district = models.ForeignKey("District"' not in content[content.find(target):]:
    content = content.replace(target, replacement)
    with open("user/models.py", "w") as f:
        f.write(content)
    print("Success")
else:
    print("Failed or already added")

