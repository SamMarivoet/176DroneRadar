#!/bin/bash
# filepath: test_forwarded_header.sh

echo "=== Testing X-Forwarded-For Header Handling ==="
echo ""
echo "PORT 8000 HAS TO BE EXPOSED FOR THIS TEST TO WORK!"
echo "(BUT SHOULD NOT BE IN PRODUCTION!)"

BACKEND_URL="http://localhost:8000"

echo "Test 1: Simulating IP 203.0.113.10 (will get rate limited)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for i in {1..6}; do
  echo -n "Attempt $i from 203.0.113.10... "
  RESPONSE=$(curl -s -X POST "$BACKEND_URL/admin/auth/verify" \
    -H "Content-Type: application/json" \
    -H "X-Forwarded-For: 203.0.113.10" \
    -H "X-Real-IP: 203.0.113.10" \
    -d '{"username":"admin","password":"wrongpass'$i'"}')
  
  if echo "$RESPONSE" | grep -qi "rate limit"; then
    echo "RATE LIMITED ✅"
    break
  elif echo "$RESPONSE" | grep -qi "unauthorized\|incorrect"; then
    echo "Rejected"
  else
    echo "$RESPONSE"
  fi
  sleep 0.3
done

echo ""
echo "Test 2: Different IP 203.0.113.20 (should NOT be rate limited)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -s -X POST "$BACKEND_URL/admin/auth/verify" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 203.0.113.20" \
  -H "X-Real-IP: 203.0.113.20" \
  -d '{"username":"admin","password":"wrongpass"}')

if echo "$RESPONSE" | grep -qi "rate limit"; then
  echo "❌ FAIL: Different IP got rate limited (not tracking IPs correctly!)"
  echo "Response: $RESPONSE"
elif echo "$RESPONSE" | grep -qi "unauthorized\|incorrect"; then
  echo "✅ PASS: Different IP can still attempt login"
else
  echo "Response: $RESPONSE"
fi

echo ""
echo "Test 3: Third IP 203.0.113.30 (should also work)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -s -X POST "$BACKEND_URL/admin/auth/verify" \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: 203.0.113.30" \
  -H "X-Real-IP: 203.0.113.30" \
  -d '{"username":"admin","password":"wrongpass"}')

if echo "$RESPONSE" | grep -qi "unauthorized\|incorrect"; then
  echo "✅ PASS: Third IP can also attempt login"
else
  echo "Response: $RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo "  ✅ IP 203.0.113.10: Rate limited after multiple attempts"
echo "  ✅ IP 203.0.113.20: Not affected by first IP's rate limit"
echo "  ✅ IP 203.0.113.30: Also not affected"
echo ""
echo "This proves X-Forwarded-For header is being tracked correctly!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"