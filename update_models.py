with open("user/models.py", "r") as f:
    content = f.read()

business_repl = """    province = models.ForeignKey("Province", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")
    district = models.ForeignKey("District", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")"""
content = content.replace('    province = models.ForeignKey("Province", on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses")', business_repl)

creator_repl = """    province = models.ForeignKey("Province", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")
    district = models.ForeignKey("District", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")"""
content = content.replace('    province = models.ForeignKey("Province", on_delete=models.SET_NULL, null=True, blank=True, related_name="creators")', creator_repl)

with open("user/models.py", "w") as f:
    f.write(content)
