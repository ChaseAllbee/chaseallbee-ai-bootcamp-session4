# Practice Lead Authorization System

## Problem

Consultants are inappropriately removing colleagues from capabilities to make space for themselves or their preferred team members. This creates capability management chaos and undermines trust in the system.

## Recommended Solution

Implement a role-based access control system with the following features:

### User Interface
- Add a user authentication icon in the top right corner
- Login modal with username/password authentication
- Role-based navigation and permissions

### Permission Levels

**Practice Leads (Authenticated Users)**
- Full capability management: register/unregister consultants
- View all capability details and consultant information
- Modify capability capacity and requirements
- Generate capability reports and analytics

**Consultants (Standard Users)**
- View all available capabilities and registered consultants
- Self-register for capabilities (with practice lead approval workflow)
- View their own capability registrations
- Request capability training and development

### Authentication Storage

Since we don't have a database yet, store practice lead credentials in a `practice_leads.json` file that includes:
- Username/password combinations
- Role assignments
- Practice area permissions
- Approval workflows

## Security Considerations

- Implement proper password hashing
- Add session management
- Include audit logging for capability changes
- Consider integration with Slalom's SSO system for future enhancement
