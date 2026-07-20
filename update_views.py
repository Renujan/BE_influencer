with open("user/views.py", "r") as f:
    content = f.read()

district_logic = """            # District
            district_data = request.data.get("district")
            if district_data:
                try:
                    profile.district = District.objects.get(id=district_data)
                except (ValueError, District.DoesNotExist):
                    profile.district = District.objects.filter(name__iexact=str(district_data).strip()).first()
            else:
                profile.district = None
"""

# For BusinessProfile
biz_prov_end = """            else:
                profile.province = None"""
idx = content.find(biz_prov_end)
if idx != -1:
    content = content[:idx + len(biz_prov_end)] + "\n" + district_logic + content[idx + len(biz_prov_end):]

# For CreatorProfile (the second occurrence of province_data check, since we just added one for business)
idx2 = content.find(biz_prov_end, idx + len(biz_prov_end) + 10)
if idx2 != -1:
    content = content[:idx2 + len(biz_prov_end)] + "\n" + district_logic + content[idx2 + len(biz_prov_end):]

with open("user/views.py", "w") as f:
    f.write(content)
