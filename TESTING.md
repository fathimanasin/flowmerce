## TESTING CHECKLIST — Flask Backend

Follow these steps in order. Use **Postman** or `curl` to test.

---

## Step 1: Verify Server is Running

```bash
curl http://localhost:5000/health
```

Expected response:
```json
{"status": "ok", "database": "connected"}
```

If you get a connection error, your server isn't running. Do:
```bash
python app.py
```

---

## Step 2: Signup (Create Tenant + First User)

**Endpoint:** `POST http://localhost:5000/auth/signup`

**In Postman:**
1. New → Request
2. Method: POST
3. URL: `http://localhost:5000/auth/signup`
4. Body → Raw → JSON:
```json
{
  "email": "seller@myshop.com",
  "password": "password123",
  "business_name": "My Clothing Store"
}
```
5. Send

**Expected response (201):**
```json
{
  "message": "Signup successful",
  "tenant_id": "abc-123-def",
  "user_id": "user-456",
  "token": "eyJhbGc..."
}
```

**Save the `token` value** — you'll use it for all future requests.

---

## Step 3: Login (Get Token for Existing User)

**Endpoint:** `POST http://localhost:5000/auth/login`

**Request:**
```json
{
  "email": "seller@myshop.com",
  "password": "password123"
}
```

**Expected response (200):**
```json
{
  "message": "Login successful",
  "tenant_id": "abc-123-def",
  "user_id": "user-456",
  "token": "eyJhbGc..."
}
```

---

## Step 4: Create a Customer

**Endpoint:** `POST http://localhost:5000/customers`

**Headers:**
```
Authorization: Bearer <token from signup>
Content-Type: application/json
```

**Body:**
```json
{
  "name": "Raj Kumar",
  "phone": "9876543210",
  "email": "raj@example.com"
}
```

**Expected response (201):**
```json
{
  "message": "Customer created",
  "customer_id": "cust-789"
}
```

**Save the `customer_id`** — you'll need it for orders.

---

## Step 5: Create a Conversation (Simulate WhatsApp Message)

**Endpoint:** `POST http://localhost:5000/conversations`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "customer_name": "Raj Kumar",
  "customer_phone": "9876543210",
  "channel": "whatsapp",
  "message_text": "Hi! Do you have the red shirt in size M?",
  "direction": "inbound"
}
```

**Expected response (201):**
```json
{
  "message": "Conversation created",
  "conversation_id": "conv-100"
}
```

**Save the `conversation_id`** — you'll need it for orders.

---

## Step 6: List All Conversations

**Endpoint:** `GET http://localhost:5000/conversations`

**Headers:**
```
Authorization: Bearer <token>
```

**No body needed.**

**Expected response (200):**
```json
{
  "conversations": [
    {
      "id": "conv-100",
      "customer_name": "Raj Kumar",
      "customer_phone": "9876543210",
      "channel": "whatsapp",
      "message_text": "Hi! Do you have the red shirt in size M?",
      "status": "open",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

---

## Step 7: Create an Order

**Endpoint:** `POST http://localhost:5000/orders`

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Body:**
```json
{
  "customer_id": "cust-789",
  "conversation_id": "conv-100",
  "items": [
    {
      "product": "Red Shirt Size M",
      "qty": 1,
      "price": 500
    }
  ],
  "total_amount": 500,
  "notes": "Customer prefers cash on delivery"
}
```

**Expected response (201):**
```json
{
  "message": "Order created",
  "order_id": "ord-200",
  "order_number": "ORD-ABC12345"
}
```

---

## Step 8: List All Orders

**Endpoint:** `GET http://localhost:5000/orders`

**Headers:**
```
Authorization: Bearer <token>
```

**Expected response (200):**
```json
{
  "orders": [
    {
      "id": "ord-200",
      "order_number": "ORD-ABC12345",
      "customer_id": "cust-789",
      "status": "enquiry",
      "total_amount": 500,
      "payment_status": "pending",
      "created_at": "2024-01-15T10:35:00"
    }
  ]
}
```

---

## Step 9: Get Single Order Details

**Endpoint:** `GET http://localhost:5000/orders/<order_id>`

Replace `<order_id>` with `ord-200` from step 7.

**Headers:**
```
Authorization: Bearer <token>
```

**Expected response (200):**
```json
{
  "order": {
    "id": "ord-200",
    "order_number": "ORD-ABC12345",
    "customer_id": "cust-789",
    "status": "enquiry",
    "items": [
      {
        "product": "Red Shirt Size M",
        "qty": 1,
        "price": 500
      }
    ],
    "total_amount": 500,
    "payment_status": "pending",
    "created_at": "2024-01-15T10:35:00"
  }
}
```

---

## What to Check ✓

- [ ] Health check returns 200
- [ ] Signup creates tenant and returns token
- [ ] Login returns token for same tenant
- [ ] Customer can be created with token
- [ ] Conversation can be created and retrieved
- [ ] Order can be created from conversation
- [ ] All requests with invalid token return 401
- [ ] All requests from one tenant cannot see another tenant's data (test with 2 different signup tokens)

---

## Common Issues

| Error | Fix |
|-------|-----|
| `400 Missing required fields` | Check JSON body has all fields |
| `401 Token is missing` | Add `Authorization: Bearer <token>` header |
| `401 Token is invalid or expired` | Use a fresh token from signup/login |
| `404 Endpoint not found` | Check URL path and method (GET vs POST) |
| `500 Internal server error` | Check Flask logs in terminal for traceback |
| `Connection refused` | Flask not running — do `python app.py` |

---

## Notes for Next Phase

Once all tests pass:
1. **Deploy to Railway** using the README instructions
2. **Get your production HTTPS URL** from Railway dashboard
3. **Update `.env` with production JWT secret**
4. **Test production endpoints** with the same curl/Postman requests
5. **Start building React frontend** — it will use these exact same endpoints
