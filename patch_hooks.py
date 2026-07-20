import re

with open("user/wagtail_hooks.py", "r") as f:
    content = f.read()

# Remove MediumViewSet
old_medium_vs = """# 6. Medium Admin Viewset
class MediumViewSet(ModelViewSet):
    model = Medium
    menu_label = "Mediums"
    icon = "tag"
    menu_icon = "tag"
    menu_item_name = "mediums"
    add_to_admin_menu = False
    list_display = ("name",)
    search_fields = ("name",)"""
content = content.replace(old_medium_vs, "")

old_group = """"business_types", "countries", "mediums","""
new_group = """"business_types", "countries","""
content = content.replace(old_group, new_group)

with open("user/wagtail_hooks.py", "w") as f:
    f.write(content)
