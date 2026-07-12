import requests

# 1. Login to get token
r = requests.post("http://localhost:8000/api/auth/login/", json={
    "username": "alex",
    "password": "password"
})
print("Login:", r.status_code, r.text)

token = r.json().get("token")
if token:
    headers = {"Authorization": f"Token {token}"}
    
    # 2. Test send pitch
    p_r = requests.post("http://localhost:8000/api/campaigns/pitches/", json={
        "brand": 6,
        "campaign_name": "Test Pitch",
        "budget": 1000,
        "sent_date": "Today",
        "description": "Test",
        "deliverables": []
    }, headers=headers)
    print("Pitch:", p_r.status_code, p_r.text)
    
    # 3. Test save brand
    s_r = requests.post("http://localhost:8000/api/creators/save-brand/", json={
        "brand_id": 1
    }, headers=headers)
    print("Save Brand:", s_r.status_code, s_r.text)
