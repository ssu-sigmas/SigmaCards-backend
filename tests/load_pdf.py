import requests

url = "http://localhost:9000/card-images"

# Данные из upload_fields
form_data = {
    "Content-Type": "application/pdf",
    "Cache-Control": "public, max-age=31536000, immutable",
    "key": "source-pdfs/2c0c2c73-3498-44f7-adc9-89d2a773445d.pdf",
    "x-amz-algorithm": "AWS4-HMAC-SHA256",
    "x-amz-credential": "ADJKLSJDALKJSLJLAK1312321/20260414/us-east-1/s3/aws4_request",
    "x-amz-date": "20260414T131855Z",
    "policy": "eyJleHBpcmF0aW9uIjogIjIwMjYtMDQtMTRUMTM6Mjg6NTVaIiwgImNvbmRpdGlvbnMiOiBbeyJDb250ZW50LVR5cGUiOiAiYXBwbGljYXRpb24vcGRmIn0sIHsiQ2FjaGUtQ29udHJvbCI6ICJwdWJsaWMsIG1heC1hZ2U9MzE1MzYwMDAsIGltbXV0YWJsZSJ9LCBbImNvbnRlbnQtbGVuZ3RoLXJhbmdlIiwgMSwgNTI0Mjg4MDBdLCB7ImJ1Y2tldCI6ICJjYXJkLWltYWdlcyJ9LCB7ImtleSI6ICJzb3VyY2UtcGRmcy8yYzBjMmM3My0zNDk4LTQ0ZjctYWRjOS04OWQyYTc3MzQ0NWQucGRmIn0sIHsieC1hbXotYWxnb3JpdGhtIjogIkFXUzQtSE1BQy1TSEEyNTYifSwgeyJ4LWFtei1jcmVkZW50aWFsIjogIkFESktMU0pEQUxLSlNMSkxBSzEzMTIzMjEvMjAyNjA0MTQvdXMtZWFzdC0xL3MzL2F3czRfcmVxdWVzdCJ9LCB7IngtYW16LWRhdGUiOiAiMjAyNjA0MTRUMTMxODU1WiJ9XX0=",
    "x-amz-signature": "4504a3018a629d1190d03266e1911ec44bcbd9f08cd0674ca8c960679c3ee656"
}

# Открываем файл
with open("hybrid_test.pdf", "rb") as f:
    files = {"file": ("hybrid_test.pdf", f, "application/pdf")}
    
    response = requests.post(url, data=form_data, files=files)

print(response.status_code)
print(response.text)