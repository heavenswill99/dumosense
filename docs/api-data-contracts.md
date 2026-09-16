# Dumosense MVP API Data Contracts

**Status:** Week 3 Design Specification  
**Version:** 1.0  
**Scope:** MindGuard, Health Reserve and Shared Dumosense Platform

## 1. Purpose

This document defines the MVP data contracts between the Dumosense backend and product applications.

The contracts describe how product-facing services are expected to access and exchange data with the Dumosense data foundation.

These contracts are design specifications. The API endpoints have not yet been implemented or tested.

---

## 2. General Principles

- API access requires authentication where user-specific data is involved.
- The frontend does not connect directly to the database.
- The backend determines the authenticated user's identity.
- Consent must be checked before collecting or processing consent-dependent data.
- Product enrollment determines access to product-specific functionality.
- API responses should expose only the data required by the requesting product.
- Internal database structure should not be exposed directly to clients.
- Intelligence outputs must remain traceable to their originating intelligence run.
- System-generated events should be recorded by trusted backend services.

---

# 3. User Profile

### Endpoint

```http
GET /api/v1/profile
```

### Purpose

Retrieve the authenticated user's account and profile information.

### Database Sources

- `users`
- `user_profiles`

### Example Response

```json
{
  "user_id": "USR000076",
  "first_name": "Tosin",
  "last_name": "Okafor",
  "email": "tosin.okafor000076@example.com",
  "account_status": "active",
  "profile": {
    "age_group": "35-44",
    "sex": "male",
    "country": "Nigeria",
    "state_or_region": "Rivers",
    "profile_status": "complete"
  }
}
```

### Additional Operation

```http
PATCH /api/v1/profile
```

Used to update permitted profile fields.

---

# 4. Product Enrollments

### Endpoint

```http
GET /api/v1/products
```

### Purpose

Retrieve the Dumosense products available to the authenticated user.

### Database Source

- `product_enrollments`

### Example Response

```json
{
  "products": [
    {
      "product_code": "HEALTH_RESERVE",
      "enrollment_status": "active",
      "enrolled_at": "2025-12-18T04:00:00",
      "discontinued_at": null
    },
    {
      "product_code": "MINDGUARD",
      "enrollment_status": "active",
      "enrolled_at": "2025-12-20T10:00:00",
      "discontinued_at": null
    }
  ]
}
```

---

# 5. Consent

### Endpoints

```http
GET  /api/v1/consents
POST /api/v1/consents
POST /api/v1/consents/{consent_id}/withdraw
```

### Purpose

Retrieve, grant and withdraw user consent.

### Database Sources

- `consents`
- `consent_history`

### Example Grant Request

```json
{
  "consent_type": "cognitive_assessment",
  "consent_version": 1.00
}
```

Consent changes must preserve history rather than replacing previous records without traceability.

Consent must also be enforced when consent-dependent data is collected or processed.

---

# 6. MindGuard Cognitive Assessments

### Endpoints

```http
POST /api/v1/cognition/sessions
POST /api/v1/cognition/sessions/{session_id}/responses
POST /api/v1/cognition/sessions/{session_id}/complete

GET /api/v1/cognition/results
GET /api/v1/cognition/results/latest
```

### Purpose

Create cognitive assessment sessions, receive task responses and retrieve cognitive results.

### Database Sources

- `assessment_types`
- `cognitive_tasks`
- `assessment_sessions`
- `cognitive_responses`
- `cognitive_results`

### Example Session Request

```json
{
  "assessment_type_id": "AST00001",
  "difficulty_level": 2,
  "device_type": "web"
}
```

### Data Flow

Assessment Session → Cognitive Responses → Cognitive Result → Longitudinal History

The backend must verify applicable consent before accepting assessment data.

---

# 7. Wellbeing Check-ins

### Endpoints

```http
POST /api/v1/wellbeing/checkins
GET  /api/v1/wellbeing/checkins
GET  /api/v1/wellbeing/checkins/latest
```

### Purpose

Submit and retrieve MindGuard wellbeing observations.

### Database Source

- `wellbeing_checkins`

### Example Request

```json
{
  "mood_level": 3.8,
  "stress_level": 3.3,
  "anxiety_level": 2.7,
  "sleep_quality": 2.7,
  "sleep_hours": 8.5,
  "social_wellbeing": 2.7,
  "perceived_cognitive_change": 1.3
}
```

The backend must verify wellbeing-data consent before accepting the record.

---

# 8. Context Records

### Endpoints

```http
POST /api/v1/context
GET  /api/v1/context
```

### Purpose

Store and retrieve contextual information that may help interpret longitudinal observations.

### Database Source

- `context_records`

### Example Request

```json
{
  "related_session_id": "SES00000411",
  "context_type": "sleep",
  "context_value": "poor",
  "source": "self_report"
}
```

Context records provide supporting information and should not by themselves be interpreted as proof of causation.

---

# 9. Health Reserve Assessments

### Endpoints

```http
POST /api/v1/health-reserve/assessments
GET  /api/v1/health-reserve/assessments
GET  /api/v1/health-reserve/latest
GET  /api/v1/health-reserve/progress
```

### Purpose

Submit Health Reserve assessments and retrieve current and longitudinal preparedness information.

### Database Source

- `health_reserve_assessments`

### Example Response

```json
{
  "assessed_at": "2026-08-29T04:00:00",
  "healthcare_coverage_status": "partial",
  "current_preparedness_amount": 779000,
  "preparedness_target": 1098000,
  "preparedness_gap": 319000,
  "preparedness_ratio": 0.709472,
  "reserve_status": "moderate"
}
```

The progress endpoint can provide changes between earlier and current preparedness positions.

---

# 10. Events

### Endpoints

```http
POST /api/v1/events
GET  /api/v1/events
```

### Purpose

Record and retrieve important user and system activity across Dumosense.

### Database Source

- `events`

### Example Event

```json
{
  "event_type": "cognitive_session_completed",
  "source": "mindguard",
  "related_entity_type": "assessment_session",
  "related_entity_id": "SES00000410"
}
```

Events support reconstruction of:

**what happened → when → source → related record**

Trusted system events should normally be created by backend services rather than accepted directly from untrusted clients.

---

# 11. Insights and Recommendations

### Endpoints

```http
GET /api/v1/insights
GET /api/v1/insights/latest
GET /api/v1/insights?product=MINDGUARD
GET /api/v1/insights?product=HEALTH_RESERVE
```

### Purpose

Deliver Dumosense intelligence and associated recommendations to product applications.

### Database Sources

- `intelligence_runs`
- `insights`
- `recommendations`

### Example Response

```json
{
  "product_code": "MINDGUARD",
  "insight": {
    "insight_type": "stable_pattern",
    "priority": "low",
    "text": "Synthetic output: stable pattern.",
    "explanation": "Architecture-testing synthetic explanation only."
  },
  "recommendation": {
    "recommendation_type": "maintain_monitoring",
    "text": "Continue routine monitoring.",
    "priority": "medium"
  }
}
```

Each insight must remain traceable internally to its intelligence run, including model or rule version and relevant input period.

---

# 12. Actions

### Endpoints

```http
POST /api/v1/actions
GET  /api/v1/actions
```

### Purpose

Record and retrieve user actions associated with Dumosense recommendations.

### Database Source

- `actions`

### Example Request

```json
{
  "recommendation_id": "REC00000060",
  "action_type": "acknowledged"
}
```

This supports the traceability chain:

**Data → Intelligence Run → Insight → Recommendation → Action**

---

# 13. MVP Contract Summary

| Contract | Main Endpoint | Authentication |
|---|---|---|
| User Profile | `/api/v1/profile` | Required |
| Product Enrollments | `/api/v1/products` | Required |
| Consent | `/api/v1/consents` | Required |
| Cognitive Assessments | `/api/v1/cognition/...` | Required |
| Wellbeing Check-ins | `/api/v1/wellbeing/...` | Required |
| Context Records | `/api/v1/context` | Required |
| Health Reserve | `/api/v1/health-reserve/...` | Required |
| Events | `/api/v1/events` | Required |
| Insights & Recommendations | `/api/v1/insights` | Required |
| Actions | `/api/v1/actions` | Required |

---

## 14. Implementation Status

**API Contract Design:** Complete

**Backend Endpoint Implementation:** Not yet implemented

**Postman/API Testing:** Not yet performed

**Current Data Foundation:** MySQL development database with synthetic longitudinal data

> Synthetic development data only. Not for clinical use.