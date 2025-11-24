#!/bin/bash

echo "=== Testing Backend Security ==="
echo ""

echo "1. Testing direct backend access (should FAIL)..."
if curl -s -f -m 2 http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ SECURITY ISSUE: Backend is directly accessible!"
else
    echo "✅ Good: Backend is not directly accessible"
fi
echo ""

echo "2. Testing proxy access to backend (should WORK)..."
if curl -s -f http://localhost:8080/api/planes > /dev/null 2>&1; then
    echo "✅ Good: Can access backend via proxy"
else
    echo "❌ Problem: Cannot access backend via proxy"
fi
echo ""

echo "3. Testing authentication via proxy..."
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"pass"}')

if echo "$AUTH_RESPONSE" | grep -q "ok"; then
    echo "✅ Good: Authentication works via proxy"
else
    echo "❌ Problem: Authentication failed"
    echo "(Restart container to reset rate limiting)"
    echo "Response: $AUTH_RESPONSE"
fi
echo ""

echo "4. Testing rate limiting (5 failed attempts)..."
for i in {1..6}; do
  RESPONSE=$(curl -s -X POST http://localhost:8080/api/auth \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"wrongpass"}' 2>&1)
  
  if echo "$RESPONSE" | grep -q "Rate limit"; then
    echo "✅ Good: Rate limit triggered on attempt $i"
    break
  elif [ $i -eq 6 ]; then
    echo "⚠️  Warning: Rate limit not triggered after 6 attempts"
  fi
done
echo ""

echo "=== Security Test Complete ==="


