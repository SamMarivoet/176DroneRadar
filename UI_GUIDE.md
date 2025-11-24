# Admin Statistics Dashboard - UI Guide

## Overview

The Admin Statistics Dashboard provides a comprehensive view of the drone radar system with real-time statistics, activity monitoring, and database health metrics.

## Layout

### Header Section
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Admin Statistics Dashboard     [🔄 Refresh] [← Back] [Logout] │
│  Last update: 10:30:45                                      │
└─────────────────────────────────────────────────────────────┘
```

### Metric Cards Row
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Total Active │ Active Planes│ Active Drones│   Archived   │
│   Objects    │   (ADS-B)    │   (Reports)  │   Reports    │
│     127      │      95      │      15      │     342      │
│          Planes & Drones Combined        │ Older than 1h│
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### Tab Navigation
```
┌─────────────────────────────────────────────────────┐
│ Overview  │ Activity  │ Details  │ Health  │       │
└─────────────────────────────────────────────────────┘
```

## Tab Views

### 1. Overview Tab

#### Distribution by Source
```
┌─────────────────────────────────────────────────────┐
│ Distribution by Source                              │
├─────────────┬─────────┬─────────────────────────────┤
│ Source      │ Count   │ Percentage                  │
├─────────────┼─────────┼─────────────────────────────┤
│ opensky     │ 95      │ [████████████████████] 74%  │
│ dronereport │ 15      │ [████] 12%                  │
│ ogn         │ 17      │ [█████] 13%                 │
└─────────────┴─────────┴─────────────────────────────┘
```

#### Drone Type Distribution
```
┌─────────────────────────────────────────────────────┐
│ Drone Type Distribution                             │
├─────────────────────────┬──────────────────────────┤
│ consumer                │ 8                        │
│ commercial              │ 4                        │
│ military                │ 3                        │
│ racing                  │ 1                        │
└─────────────────────────┴──────────────────────────┘
```

#### Drone Altitude Distribution
```
┌─────────────────────────────────────────────────────┐
│ Drone Altitude Distribution                         │
├─────────────────────────────┬──────────────────────┤
│ 0-50m (low)                 │ 5                    │
│ 50-150m (medium)            │ 6                    │
│ 150-400m (high)             │ 4                    │
│ +400m (very high)           │ 2                    │
└─────────────────────────────┴──────────────────────┘
```

#### Top Countries
```
Top Countries panel is omitted in the admin UI for Belgium-only deployments.
```

### 2. Recent Activity Tab

#### 24-Hour Stats Cards
```
┌──────────────┬──────────────┬──────────────┐
│ Active Planes│ Drone Reports│  Archived    │
│   (24h)      │    (24h)     │   (24h)      │
│     45       │      8       │     23       │
└──────────────┴──────────────┴──────────────┘
```

#### Latest Updates
```
┌─────────────────────────────────────────────────────┐
│ Latest Updates                                      │
├─────────────────────────────┬──────────────────────┤
│ Flight BAW901               │ opensky  10:30:12   │
│ Drone Report - Backyard     │ report   10:25:45   │
│ Flight EZY123               │ opensky  10:20:33   │
└─────────────────────────────┴──────────────────────┘
```

#### Recently Archived
```
┌─────────────────────────────────────────────────────┐
│ Recently Archived                                   │
├─────────────────────────────┬──────────────────────┤
│ Drone sighting - Airport    │ Archived 10:45:20  │
│ Delivery drone - City       │ Archived 10:40:15  │
│ Unknown UAV - Rural area    │ Archived 10:35:00  │
└─────────────────────────────┴──────────────────────┘
```

### 3. Detailed Statistics Tab

Comprehensive metric breakdown displayed in table format.

### 4. Database Health Tab

#### Collection Statistics
```
┌─────────────────────────────────────────────────────┐
│ Database Health Status                              │
├──────────────┬──────────┬──────────┬──────────────┤
│ planes       │ 127 docs │ 2.45 MB  │ Avg 19.4 KB │
│ archive      │ 342 docs │ 5.12 MB  │ Avg 15.0 KB │
│ users        │ 3 docs   │ 0.03 MB  │              │
├──────────────┴──────────┴──────────┴──────────────┤
│ Total Database Size: 7.60 MB                      │
└─────────────────────────────────────────────────────┘
```

## Color Scheme

### Card Colors
- **Primary Cards**: Blue border (Main metrics)
- **Drone Cards**: Pink/Magenta border (Drone data)
- **Archive Cards**: Light Blue border (Archive data)
- **Health Cards**: Green border (Database health)

### Status Badges
- **[blue]** INFO - Data source indicator
- **[green]** SUCCESS - Active/healthy status
- **[orange]** WARNING - Caution status
- **[red]** ERROR - Problem indicator

## Interactive Elements

### Buttons
```
[🔄 Refresh]  - Force immediate data update
[← Back]      - Return to map GUI
[Logout]      - Clear session and logout
```

### Tabs
```
[Overview]    [Activity]    [Details]    [Health]
```
Click to switch between views. Active tab highlighted in blue.

## Responsive Design

### Desktop (1200px+)
- Full layout with multiple columns
- Detailed tables
- Side-by-side cards

### Tablet (768px - 1199px)
- Adaptive grid layout
- Single column when needed
- Stacked cards

### Mobile (<768px)
- Single column layout
- Full-width elements
- Simplified tables
- Collapsible sections

## Visual Indicators

### Progress Bars
Used to show percentage distribution:
```
Distribution:
[████████████████████] 74%
[████] 12%
[█████] 13%
```

### Data Presentation
- **Numbers**: Large, bold, easy to read
- **Descriptions**: Small gray text below numbers
- **Time**: Displayed in local timezone
- **Units**: Clearly labeled (MB, count, %)

## User Interactions

### Viewing Data
1. Page loads with overview tab active
2. Statistics auto-refresh every 30 seconds
3. Click tabs to switch views
4. Click "Refresh" for immediate update

### Authentication
- Login credentials stored in browser session
- Token persists across page reloads
- "Logout" button clears session
- Session expires with browser close (localStorage)

### Error Handling
- Error messages displayed in red banner
- Auto-dismissal after 5 seconds
- User-friendly error descriptions

## Performance Indicators

### Page Load
- API calls show loading state
- "Loading..." message during data fetch
- Partial data display (cards load first)

### Auto-Refresh
- Timestamp updated on each refresh
- Smooth data transitions
- No page reload needed

### Database Health
- Size in MB clearly shown
- Count of documents per collection
- Average document size
- Performance insights

## Navigation Flow

```
Map GUI
    ↓ [Login]
    ↓ (enter credentials)
    ↓ [Sign In]
    ↓ [Admin Stats Button appears]
    ↓ [Click Admin Stats]
    ↓
Admin Dashboard
    ├─ Overview Tab (default)
    ├─ Activity Tab
    ├─ Details Tab
    └─ Health Tab
    
    Buttons:
    ├─ [Refresh] - Force update
    ├─ [← Back] - Return to map
    └─ [Logout] - Exit dashboard
```

## Data Freshness

- **Auto-Refresh**: Every 30 seconds
- **Manual Refresh**: Via button click
- **Last Update**: Timestamp shown in header
- **Format**: HH:MM:SS local time

## Accessibility

- **Color Contrast**: WCAG compliant
- **Font Sizes**: Readable on all devices
- **Labels**: Clear and descriptive
- **Structure**: Semantic HTML
- **Navigation**: Keyboard accessible

## Mobile Optimization

On mobile devices:
- Simplified layout
- Stacked cards
- Touch-friendly buttons
- Optimized tables
- Font sizes adjusted

Example mobile layout:
```
┌─────────────────┐
│ 📊 Dashboard    │
│ [🔄][←][Logout]│
├─────────────────┤
│ Total: 127      │
├─────────────────┤
│ Planes: 95      │
├─────────────────┤
│ Drones: 15      │
├─────────────────┤
│ Archive: 342    │
├─────────────────┤
│[Overview]       │
│[Activity]       │
│[Details]        │
│[Health]         │
├─────────────────┤
│ Data Table...   │
└─────────────────┘
```

## Theme Consistency

The dashboard uses the same color scheme and styling approach as the main Map GUI:
- Professional gradient backgrounds
- Card-based layout
- Consistent spacing and padding
- Modern, clean design
- Mobile-first approach

## Feedback to User

### Successful Login
- Buttons change from [Login] to [Admin Stats][Logout]
- User navigates to dashboard

### Failed Login
- Red error message displayed
- Credentials cleared
- User can retry

### Data Loading
- "Loading..." message shown
- Data fills in as it arrives
- Timestamp updates on completion

### Logout
- Buttons reset to [Login]
- Dashboard becomes inaccessible
- User redirected to map
