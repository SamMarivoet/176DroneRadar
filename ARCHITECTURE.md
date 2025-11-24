# System Architecture Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER                                        │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                    ▼                                 ▼
        ┌──────────────────────┐        ┌──────────────────────┐
        │   Map GUI            │        │   Admin Dashboard    │
        │   (index.html)       │        │   (admin-stats.html) │
        │                      │        │                      │
        │ - Display map        │        │ - Real-time stats    │
        │ - Show planes/drones │        │ - 4 tab views        │
        │ - Login button       │        │ - Auto-refresh 30s   │
        │ - Admin button       │        │ - Professional UI    │
        └────────┬─────────────┘        └──────────┬───────────┘
                 │ [Login]                         │ [Requires Auth]
                 │                                 │
                 └─────────────────┬────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼ HTTP Basic Auth             │
        ┌──────────────────────────┐             │
        │   FastAPI Backend        │             │
        │   (:8000)                │             │
        │                          │             │
        │ /admin/auth/verify       │             │
        │ /statistics/overview     │             │
        │ /statistics/recent...    │◄────────────┘ API Calls
        │ /statistics/top-...      │
        │ /statistics/health       │
        │                          │
        │ + CORS Middleware        │
        │ + Rate Limiting          │
        │ + Admin Auth Required    │
        └────────────┬─────────────┘
                     │
                     │ MongoDB Queries
                     │
                     ▼
        ┌──────────────────────────┐
        │   MongoDB Database       │
        │                          │
        │ Collections:             │
        │ - planes (active)        │
        │ - archive (aged-out)     │
        │ - users (auth)           │
        └──────────────────────────┘
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. User opens Map GUI (index.html)                      │
└──────────────────────────┬────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────┐
│ 2. User clicks "Login" button                          │
└──────────────────────────┬────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────┐
│ 3. Login modal appears                                │
│    Username: ___________  Password: ___________       │
└──────────────────────────┬────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────┐
│ 4. User submits credentials                           │
│    POST /admin/auth/verify                            │
    │    Body: {"username": "admin", "password": "pass"} │
└──────────────────────────┬────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
          ┌─────────▼──────┐  ┌───▼──────────┐
          │ VALID          │  │ INVALID      │
          │ ✓ Credentials  │  │ ✗ Error msg  │
          │   verified     │  │   displayed  │
          └─────────┬──────┘  └──────────────┘
                    │
        ┌───────────▼──────────┐
        │ 5. Token stored      │
        │    localStorage      │
        │    "admin:pass"   │
        └───────────┬──────────┘
                    │
        ┌───────────▼──────────┐
        │ 6. UI updated        │
        │    - Login hidden    │
        │    - Admin visible   │
        │    - Logout visible  │
        └───────────┬──────────┘
                    │
        ┌───────────▼──────────┐
        │ 7. User clicks       │
        │    "Admin Stats"     │
        └───────────┬──────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ 8. Navigate to admin-stats.html  │
        │    Token sent with each request  │
        │    Authorization: Basic xxx      │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────┐
        │ 9. Dashboard loads   │
        │    Statistics fetch  │
        │    API Calls         │
        └──────────────────────┘
```

## Data Flow

```
┌─────────────────────────┐
│ Admin Dashboard         │
│ (admin-stats.html)      │
└────────────┬────────────┘
             │ fetch()
             │ Auth: "Basic xxx"
             │
┌────────────▼──────────────────────────┐
│ FastAPI Backend                       │
│ (main.py, statistics.py)              │
│                                       │
│ verify_admin() → Check credentials    │
│                                       │
│ GET /statistics/overview              │
│   → Query MongoDB (planes, archive)   │
│   → Count by source                   │
│   → Count by drone_type               │
│   → Count by altitude                 │
│   → Return JSON                       │
│                                       │
│ GET /statistics/recent-activity       │
│   → Query last 24 hours               │
│   → Aggregate statistics              │
│   → Get latest updates                │
│   → Return JSON                       │
│                                       │
│ GET /statistics/top-countries         │
│   → Group by country                  │
│   → Sort by count                     │
│   → Limit to N                        │
│   → Return JSON                       │
│                                       │
│ GET /statistics/database-health       │
│   → collStats commands                │
│   → Calculate sizes                   │
│   → Return MongoDB metrics            │
└────────────┬──────────────────────────┘
             │ MongoDB queries
             │
┌────────────▼──────────────────────────┐
│ MongoDB Database                       │
│                                        │
│ planes collection:                     │
│   {icao, flight, lat, lon, alt, ...}  │
│   {source: "opensky"/"ogn"/"report"} │
│   {drone_type: "consumer"/...}        │
│   {altitude: "0-50m"/...}             │
│                                        │
│ archive collection:                    │
│   {drone_description, ...}            │
│   {archived_at: timestamp}            │
│                                        │
│ users collection:                      │
│   {username, password_hash, role}     │
└────────────────────────────────────────┘
```

## Component Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│ Frontend Layer (Map_GUI/frontend/)                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│ ┌──────────────────┐         ┌──────────────────┐               │
│ │  index.html      │         │ admin-stats.html │               │
│ │  (Map GUI)       │◄────────│ (Dashboard)      │               │
│ │                  │ navigate │                  │               │
│ │ - Map display    │          │ - Tab views      │               │
│ │ - Sidebar        │          │ - Statistics     │               │
│ │ - Login modal    │          │ - Auto-refresh   │               │
│ └────────┬─────────┘          └────────┬─────────┘               │
│          │                             │                         │
│ ┌────────▼─────────────────────────────▼────────────┐            │
│ │ app.js                                           │            │
│ │                                                   │            │
│ │ - Authentication handling                         │            │
│ │ - Token management (localStorage)                 │            │
│ │ - Event listeners                                │            │
│ │ - API calls                                      │            │
│ └───────────────────┬────────────────────┬─────────┘            │
│                     │                    │                      │
└─────────────────────┼────────────────────┼──────────────────────┘
                      │ HTTP requests      │
                      │ (CORS enabled)     │
┌─────────────────────┼────────────────────┼──────────────────────┐
│ Backend Layer (DroneRadarBackend/backend/app/)                   │
├─────────────────────┼────────────────────┼──────────────────────┤
│                     │                    │                      │
│ ┌──────────────────▼┴────────┐  ┌───────▼──────────────────┐   │
│ │ main.py                   │  │ routers/statistics.py    │   │
│ │                           │  │                          │   │
│ │ - FastAPI app init        │  │ @router.get("/overview")  │   │
│ │ - CORS middleware         │  │ @router.get("/activity")  │   │
│ │ - Router registration     │  │ @router.get("/countries") │   │
│ │ - Error handlers          │  │ @router.get("/health")    │   │
│ └───────────┬────────────────┘  └───────┬──────────────────┘   │
│             │                           │                      │
│ ┌───────────▼──────────────────┐  ┌───▼──────────────────┐    │
│ │ auth.py                      │  │ routers/admin.py     │    │
│ │                              │  │                      │    │
│ │ - verify_admin()             │  │ @router.post("/auth/ │    │
│ │ - verify_password()          │  │  verify")            │    │
│ │ - Rate limiting              │  │ - Credential check   │    │
│ │ - IP-based lockout           │  │ - Return status      │    │
│ └─────────────────────────────┘  └─────────────────────┘    │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐   │
│ │ database.py, crud.py                                  │   │
│ │                                                        │   │
│ │ - MongoDB connection                                   │   │
│ │ - Query helpers                                        │   │
│ │ - User lookups                                         │   │
│ └───────────────────────┬────────────────────────────────┘   │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │ MongoDB driver
                          │
┌─────────────────────────▼────────────────────────────────────┐
│ MongoDB Database Layer                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Database: planesdb                                          │
│                                                              │
│ ┌────────────────────┐  ┌────────────────────┐             │
│ │ planes collection  │  │ archive collection │             │
│ │                    │  │                    │             │
│ │ Indexes:           │  │ Indexes:           │             │
│ │ - icao (unique)    │  │ - last_seen        │             │
│ │ - position (geo)   │  │ - archived_at      │             │
│ │ - last_seen        │  │ - position (geo)   │             │
│ │                    │  │                    │             │
│ │ Fields:            │  │ Fields:            │             │
│ │ - source           │  │ - drone_desc       │             │
│ │ - drone_type       │  │ - timestamp        │             │
│ │ - altitude         │  │ - original_last... │             │
│ │ - country          │  │                    │             │
│ └────────────────────┘  └────────────────────┘             │
│                                                              │
│ ┌────────────────────────────────────────────────┐          │
│ │ users collection                              │          │
│ │ {username, password_hash, role, ...}         │          │
│ └────────────────────────────────────────────────┘          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## API Endpoint Flow

```
┌─────────────────┐
│ Admin Dashboard │
└────────┬────────┘
         │
         ├─→ POST /admin/auth/verify
         │   ├─ Username
         │   └─ Password
         │   Response: {status, username, role}
         │
         ├─→ GET /statistics/overview
         │   └─ Response: {total, by_source, drone_types, altitudes}
         │
         ├─→ GET /statistics/recent-activity?hours=24
         │   └─ Response: {recent_planes, recent_drones, latest_updates}
         │
         ├─→ GET /statistics/top-countries?limit=10
         │   └─ Response: {top_countries: {country: count}}
         │
         └─→ GET /statistics/database-health
             └─ Response: {collections: {planes, archive, users}, total_size}
```

## Security Flow

```
Request
   │
   ▼
┌─────────────────────────────┐
│ Frontend Auth Check         │
│ - Check localStorage token  │
│ - If missing → redirect     │
└──────────────┬──────────────┘
               │ Token present
               ▼
┌─────────────────────────────┐
│ Add Auth Header             │
│ Authorization: Basic <xxx>  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ CORS Middleware             │
│ - Check origin              │
│ - Allow if in whitelist     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Rate Limiting Check         │
│ - Check IP                  │
│ - Check attempt count       │
│ - Check lockout status      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ verify_admin()              │
│ - Extract credentials       │
│ - Check password hash       │
│ - Check admin role          │
└──────────────┬──────────────┘
               │ Valid
               ▼
┌─────────────────────────────┐
│ Execute Endpoint            │
│ - Query database            │
│ - Prepare response          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ Return Response             │
│ {data: ...}                 │
└─────────────────────────────┘
```

## Deployment Architecture

```
Development
├── Frontend
│   └── http://localhost:3000
│       ├── index.html (Map)
│       └── admin-stats.html (Dashboard)
├── Backend
│   └── http://localhost:8000
│       └── FastAPI server
└── Database
    └── localhost:27017
        └── MongoDB

Production (Example)
├── Frontend
│   └── https://radar.example.com
│       ├── index.html
│       └── admin-stats.html
├── Backend
│   └── https://api.radar.example.com
│       └── FastAPI server (with HTTPS)
└── Database
    └── mongodb.example.com:27017
        └── MongoDB (with auth)

Configuration
- Update CORS origins in main.py
- Update backend URL in admin-stats.html
- Use HTTPS certificates
- Update credentials
```

## Request/Response Example

```
┌─────────────────────────────────────────┐
│ REQUEST (from admin-stats.html)         │
├─────────────────────────────────────────┤
│ GET /statistics/overview                │
│ Host: localhost:8000                    │
│ Authorization: Basic YWRtaW46ZXhhbXBsZQ== │
│ Content-Type: application/json          │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ PROCESSING (statistics.py)              │
├─────────────────────────────────────────┤
│ 1. Verify admin credentials             │
│ 2. Query planes collection              │
│ 3. Count by source                      │
│ 4. Count by drone type                  │
│ 5. Count by altitude                    │
│ 6. Prepare response JSON                │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ RESPONSE (to admin-stats.html)          │
├─────────────────────────────────────────┤
│ HTTP 200 OK                             │
│ Content-Type: application/json          │
│                                         │
│ {                                       │
│   "total_planes": 127,                  │
│   "active_planes": 95,                  │
│   "active_drones": 15,                  │
│   "archived_reports": 342,              │
│   "by_source": {                        │
│     "opensky": 95,                      │
│     "dronereport": 15,                  │
│     "ogn": 17                           │
│   },                                    │
│   "drone_types": {...},                 │
│   "drone_altitudes": {...},             │
│   "timestamp": "2024-11-24T10:30:45"   │
│ }                                       │
└─────────────────────────────────────────┘
```

This architecture provides a secure, scalable, and maintainable system for admin statistics monitoring.
