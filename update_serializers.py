with open("user/serializers.py", "r") as f:
    content = f.read()

b_repl = """    province = ProvinceSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)"""
content = content.replace('    province = ProvinceSerializer(read_only=True)', b_repl, 2)

c_repl = '        fields = ["id", "user", "phone", "location", "country", "province", "district", '
content = content.replace('        fields = ["id", "user", "phone", "location", "country", "province", ', c_repl)

c2_repl = '        fields = ["id", "user", "company_name", "location", "country", "province", "district", '
content = content.replace('        fields = ["id", "user", "company_name", "location", "country", "province", ', c2_repl)

with open("user/serializers.py", "w") as f:
    f.write(content)
