# API Defect Troubleshooting

## 1. Purpose

API defect troubleshooting is the process of identifying, analyzing, and
isolating the cause of an API failure.

When an API test fails, the objective is not simply to report that the API
failed.

A QE should determine:

- What was expected?
- What actually happened?
- Where did the failure occur?
- Is the problem in the request?
- Is the problem in the API?
- Is the problem in a dependency?
- Is the problem in test data?
- Is the problem in authentication or authorization?
- Is the problem environmental?
- Is the problem intermittent?

---

## 2. Basic API Failure Analysis

When an API fails, analyze the following:

```text
Request
   ↓
Authentication
   ↓
API Gateway / Routing
   ↓
Application Logic
   ↓
Database / Dependency
   ↓
Response

Identify the earliest point where the expected behavior differs from the
actual behavior.

3. First-Level Troubleshooting Checklist

Check:

HTTP method
URL
Path parameters
Query parameters
Headers
Authentication
Authorization
Request body
Content-Type
Expected status code
Actual status code
Response body
Response headers
Test data
Environment
Dependency availability

Do not immediately assume that a failed API test means there is a product
defect.

4. HTTP Status Code Troubleshooting
400 Bad Request

Possible causes:

Missing required field
Invalid field value
Invalid data type
Malformed JSON
Invalid query parameter
Invalid path parameter

Check the request against the API contract.

401 Unauthorized

Possible causes:

Missing authentication
Invalid token
Expired token
Invalid API key
Incorrect authentication format

Check authentication before investigating application logic.

403 Forbidden

Possible causes:

User does not have required permission
Incorrect role
Insufficient scope
Access policy restriction

Authentication may be successful while authorization fails.

404 Not Found

Possible causes:

Incorrect endpoint
Incorrect path parameter
Resource does not exist
Incorrect environment
Routing problem

Verify both the endpoint and resource identifier.

409 Conflict

Possible causes:

Duplicate resource
Invalid state transition
Concurrent update
Business rule conflict

Understand the API's documented conflict behavior.

422 Unprocessable Entity

Possible causes:

Request structure is valid but business validation fails
Invalid business data
Field combination violates business rules

Check the response validation details.

429 Too Many Requests

Possible causes:

Rate limit exceeded
Too many requests
Incorrect retry behavior

Check:

Rate-limit headers
Retry-After information
Request frequency
Client retry configuration
500 Internal Server Error

Possible causes:

Application defect
Unhandled exception
Database problem
Dependency failure
Configuration issue

The server logs and correlation ID are often required for deeper
investigation.

502 Bad Gateway

Possible causes:

Upstream service failure
Gateway communication problem
Incorrect upstream response

Investigate the gateway and upstream dependency.

503 Service Unavailable

Possible causes:

Service unavailable
Deployment
Maintenance
Dependency unavailable
Infrastructure issue

Check service health and environment status.

504 Gateway Timeout

Possible causes:

Upstream service timeout
Slow dependency
Network problem
Application processing taking too long

Check response time and downstream dependencies.

5. Request vs Response Analysis

Always compare:

Expected Request
       ↓
Actual Request

Expected Response
       ↓
Actual Response

Look for differences in:

URL
HTTP method
Headers
Parameters
Request body
Status code
Response body
Response headers
6. Authentication Troubleshooting

When authentication fails, verify:

Token exists.
Token is not expired.
Correct token is being used.
Authentication header format is correct.
Correct environment is being used.
Required API key is present.
Required scopes are available.

Example:

Authorization: Bearer <token>

Never expose real tokens in defect reports, logs, screenshots, or source
code.

7. Authorization Troubleshooting

If authentication succeeds but the API returns 403:

Check:

User role
User permissions
Token scopes
Resource ownership
API authorization rules
Endpoint permissions

Distinguish clearly between:

401 = Authentication problem
403 = Authorization problem
8. Request Payload Troubleshooting

Compare the request payload against the API contract.

Check:

Required fields
Field names
Data types
Null values
Empty values
Field formats
Enumeration values
Nested objects
Arrays

Example:

{
  "quantity": "10"
}

If the contract requires an integer, sending "10" as a string may cause
validation failure.

9. Content-Type Troubleshooting

Verify the request Content-Type.

Examples:

application/json
application/xml
multipart/form-data
application/x-www-form-urlencoded

A valid payload with an incorrect Content-Type may still fail.

10. Response Validation Troubleshooting

A successful HTTP status does not always mean the API worked correctly.

For example:

HTTP 200

but:

{
  "status": "FAILED"
}

The test must validate the actual business response.

Check:

Required fields
Field values
Data types
Business status
Error fields
Schema
Data consistency
11. Database Validation

When appropriate, verify whether the API operation correctly changed
persistent data.

Example:

POST /users
      ↓
HTTP 201
      ↓
Verify user exists
      ↓
Verify stored values

Database validation should be used only when it is relevant to the
requirement and test objective.

12. Dependency Troubleshooting

An API may depend on:

Database
Payment service
Authentication service
External API
Message queue
Cache
Third-party service

If the API fails, determine whether the dependency is healthy.

Example:

API
 ↓
Payment Service
 ↓
Payment Service unavailable

The API failure may be caused by the dependency rather than the API's
primary business logic.

13. Correlation ID

A correlation ID can help trace a request across multiple services.

Example:

Client
  ↓
API Gateway
  ↓
Service A
  ↓
Service B
  ↓
Database

If the request carries a correlation ID, use it when investigating logs.

Example:

X-Correlation-ID: abc123

Do not expose sensitive information in defect reports.

14. Response Time Troubleshooting

When an API is slow, capture:

Request start time
Response time
Endpoint
HTTP method
Payload size
Response size
Dependency response time where available

Example:

Expected response time: < 2 seconds
Actual response time: 8.5 seconds

Determine whether the delay is caused by:

API processing
Database
External dependency
Network
Gateway
Infrastructure
15. Intermittent Failures

An intermittent failure does not automatically mean the API is defective.

Investigate:

Frequency
Time of occurrence
Environment
Test data
Concurrent requests
Network conditions
Dependency availability
Resource utilization

Record enough information to reproduce the problem.

16. Reproduction

A good defect should be reproducible whenever possible.

Record:

Environment
Endpoint
HTTP Method
Request
Headers
Test Data
Expected Result
Actual Result
Response
Timestamp
Correlation ID

Sensitive information must be removed or masked.

17. Environment Troubleshooting

Verify:

Correct environment
Correct base URL
Correct configuration
Required services running
Database available
Test data available
Authentication service available
External dependencies available

A test executed against the wrong environment can produce misleading
results.

18. Test Data Problems

A failed API test may be caused by incorrect or stale test data.

Check:

Record exists
Record is in expected state
User has expected permissions
Data has not expired
Required relationships exist
Data was not modified by another test

Test data should be controlled and predictable.

19. Defect vs Test Script Defect

Not every automation failure is a product defect.

Possible categories:

Product Defect
Test Automation Defect
Test Data Defect
Environment Defect
Configuration Defect
Dependency Defect
Infrastructure Defect

Before raising a product defect, eliminate obvious test, data, and
environment issues.

20. Defect Classification Example

Suppose:

Expected: HTTP 201
Actual: HTTP 500

Investigation shows the database was unavailable.

Classification:

Infrastructure / Dependency Issue

Not necessarily an application defect.

21. Another Example

Suppose:

Expected: HTTP 201
Actual: HTTP 400

Investigation shows the test sent:

{
  "email": ""
}

while the test requirement requires a valid email.

Classification:

Test Data / Test Design Issue
22. Another Example

Suppose:

Expected: HTTP 201
Actual: HTTP 500

The request is valid, the environment is healthy, and application logs
show an unhandled exception.

Classification:

Application Defect
23. QE Defect Investigation Flow

Use the following sequence:

API Test Failed
      ↓
Check Request
      ↓
Check Authentication
      ↓
Check Authorization
      ↓
Check Response
      ↓
Check Test Data
      ↓
Check Environment
      ↓
Check Dependencies
      ↓
Check Logs / Correlation ID
      ↓
Identify Root Cause
      ↓
Classify Failure
      ↓
Raise Defect if Required
24. Defect Report Information

A good API defect should contain:

Summary

A short description of the problem.

Environment

Example:

QA
Endpoint

Example:

POST /api/orders
Preconditions

Required conditions before executing the test.

Request

Include the relevant request details.

Sensitive information must be masked.

Expected Result

Describe the expected behavior.

Actual Result

Describe the actual behavior.

Response

Include relevant response information.

Reproduction Steps

Provide clear steps to reproduce the problem.

Evidence

Useful evidence may include:

API response
Logs
Screenshots
Correlation ID
Request/response capture

Sensitive data must be removed.

25. Safe Troubleshooting Principle

Never assume the first visible failure is the root cause.

For example:

API returns 500

does not immediately mean:

Application defect

Investigate:

Request
Authentication
Authorization
Test Data
Environment
Dependencies
Logs
Infrastructure

before assigning the final root cause.

26. QE Troubleshooting Checklist

Before raising an API defect, ask:

Did I use the correct endpoint?
Did I use the correct HTTP method?
Is the request payload correct?
Are required headers present?
Is authentication valid?
Does the user have required authorization?
Is the test data valid?
Is the environment correct?
Are dependent services available?
Is the database available where required?
Is the response consistent with the API contract?
Is the failure reproducible?
Do logs provide additional evidence?
Is there a correlation ID?
Could this be a test automation issue?
Could this be a test data issue?
Could this be an environment issue?
Could this be an infrastructure or dependency issue?
What is the most likely root cause?
Do we have enough evidence to raise a product defect?

A QE should classify an API failure based on evidence rather than
assumption.