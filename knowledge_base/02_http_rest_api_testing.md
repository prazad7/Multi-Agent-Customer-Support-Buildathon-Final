# HTTP and REST API Testing

## HTTP Methods

HTTP methods define the operation that a client wants to perform on a
resource.

Common HTTP methods used in REST APIs include:

- GET
- POST
- PUT
- PATCH
- DELETE

---

## GET

GET is generally used to retrieve information from a server.

Example:

GET /users/123

Typical test scenarios:

- Retrieve an existing user.
- Retrieve a non-existing user.
- Retrieve a user with an invalid ID.
- Retrieve users with valid query parameters.
- Retrieve users with invalid query parameters.
- Verify behavior when authentication is missing.
- Verify behavior when the authenticated user is not authorized.

A GET request should normally not modify the server-side resource.

---

## POST

POST is commonly used to create a new resource or submit data for
processing.

Example:

POST /users

Typical test scenarios:

- Create a resource with valid data.
- Create a resource without mandatory fields.
- Create a resource with invalid data types.
- Create a duplicate resource.
- Send an empty request body.
- Send malformed JSON.
- Verify authentication.
- Verify authorization.
- Verify response status code.
- Verify response body.

---

## PUT

PUT is generally used to completely replace or update a resource.

Example:

PUT /users/123

Typical test scenarios:

- Update an existing resource with valid data.
- Update a resource that does not exist.
- Send an invalid resource ID.
- Omit mandatory fields.
- Send invalid data types.
- Verify that the complete resource is handled according to the API
  contract.
- Verify authentication and authorization.

---

## PATCH

PATCH is commonly used to partially update an existing resource.

Example:

PATCH /users/123

Typical test scenarios:

- Update one valid field.
- Update multiple valid fields.
- Send an invalid field.
- Send an invalid data type.
- Send an empty request body.
- Attempt to update a non-existing resource.
- Verify authentication and authorization.

---

## DELETE

DELETE is generally used to remove a resource.

Example:

DELETE /users/123

Typical test scenarios:

- Delete an existing resource.
- Delete a non-existing resource.
- Delete the same resource multiple times.
- Use an invalid resource ID.
- Attempt deletion without authentication.
- Attempt deletion without sufficient authorization.
- Verify the response according to the API contract.
- Verify that the resource is actually removed when deletion succeeds.

---

# HTTP Status Codes

HTTP status codes communicate the result of an HTTP request.

The main categories are:

- 1xx - Informational
- 2xx - Successful
- 3xx - Redirection
- 4xx - Client error
- 5xx - Server error

---

## 200 OK

A 200 response generally indicates that the request was successfully
processed.

For API testing, do not validate only the 200 status code.

Also validate:

- Response body
- Response schema
- Required fields
- Data values
- Headers
- Business rules

---

## 201 Created

A 201 response generally indicates that a new resource was successfully
created.

For a create API, verify:

- Status code
- Created resource identifier
- Response body
- Resource data
- Headers where applicable
- Persistence of the resource

---

## 202 Accepted

A 202 response indicates that the request has been accepted for processing
but processing may not have completed yet.

For asynchronous APIs, test:

- Initial response.
- Processing status.
- Completion behavior.
- Failure behavior.
- Retry behavior where applicable.

---

## 204 No Content

A 204 response indicates successful processing with no response body.

Common examples include successful DELETE or update operations depending
on the API contract.

Testing should verify that:

- The status code is correct.
- The response body is empty when the contract requires it.
- The requested operation was actually completed.

---

# Client Error Status Codes

## 400 Bad Request

A 400 response generally indicates that the server cannot process the
request because the request is invalid.

Possible causes include:

- Invalid request format.
- Invalid parameter.
- Missing required information.
- Malformed request data.

Test scenarios should include:

- Missing required fields.
- Invalid values.
- Invalid data types.
- Malformed JSON.
- Invalid query parameters.

---

## 401 Unauthorized

A 401 response generally indicates that valid authentication credentials
were not provided or could not be accepted.

Test scenarios:

- No authentication header.
- Invalid token.
- Expired token.
- Malformed token.
- Invalid credentials.

---

## 403 Forbidden

A 403 response generally indicates that the request was understood but the
authenticated user is not permitted to perform the requested operation.

Test scenarios:

- Authenticated user without required permission.
- Read-only user attempting an update.
- Regular user attempting an administrator operation.
- Access to another user's restricted resource.

A useful distinction is:

401 generally relates to authentication.

403 generally relates to authorization.

---

## 404 Not Found

A 404 response generally indicates that the requested resource could not
be found.

Test scenarios:

- Non-existing resource ID.
- Invalid endpoint.
- Deleted resource.
- Incorrect path parameter.

---

## 409 Conflict

A 409 response can indicate a conflict between the request and the current
state of the resource.

Possible scenarios include:

- Creating a duplicate resource.
- Updating a resource that conflicts with another operation.
- Violating a uniqueness constraint.

The exact behavior should be validated against the API contract.

---

## 429 Too Many Requests

A 429 response generally indicates that the client has sent too many
requests within a defined period.

Test scenarios may include:

- Sending requests above the documented rate limit.
- Verifying the response status.
- Verifying retry-related headers when documented.
- Verifying recovery after the rate limit period.

---

# Server Error Status Codes

## 500 Internal Server Error

A 500 response generally indicates that the server encountered an
unexpected condition while processing the request.

Testing should verify:

- Appropriate status code.
- Safe error response.
- No sensitive information exposed.
- Appropriate logging on the server side where accessible.
- Recovery after the underlying issue is resolved.

---

## 502 Bad Gateway

A 502 response can occur when a gateway or proxy receives an invalid
response from an upstream service.

For distributed systems, test scenarios may include:

- Upstream service unavailable.
- Invalid upstream response.
- Gateway communication failure.

---

## 503 Service Unavailable

A 503 response generally indicates that the service is temporarily unable
to process requests.

Possible causes include:

- Service unavailable.
- Maintenance.
- Dependency failure.
- Temporary overload.

Test expected retry and recovery behavior according to the system
requirements.

---

# Request Headers

HTTP request headers provide additional information about the request.

Common headers include:

- Authorization
- Content-Type
- Accept
- User-Agent
- Correlation or trace identifiers

API tests should validate that required headers are:

- Present.
- Correctly formatted.
- Accepted by the server.
- Handled correctly when missing or invalid.

---

# Content-Type

Content-Type indicates the format of the request body.

A common value for JSON APIs is:

application/json

Test scenarios should include:

- Correct Content-Type.
- Missing Content-Type.
- Incorrect Content-Type.
- Malformed JSON when JSON is expected.

---

# Accept Header

The Accept header indicates the response formats that the client can
accept.

When an API supports content negotiation, tests should verify behavior
for supported and unsupported formats.

---

# Path Parameters

Path parameters identify a resource within the URL.

Example:

GET /users/123

Here:

123

is the user identifier.

Test scenarios:

- Valid identifier.
- Non-existing identifier.
- Invalid identifier.
- Empty identifier where applicable.
- Boundary identifier values.

---

# Query Parameters

Query parameters provide optional or filtering information.

Example:

GET /users?page=2&limit=20

Test scenarios:

- Valid page number.
- Valid page size.
- Zero or negative values.
- Very large values.
- Missing parameters.
- Invalid parameter types.
- Multiple filtering combinations.

---

# Request Body Validation

For APIs accepting JSON request bodies, validate:

- Required fields.
- Optional fields.
- Data types.
- String lengths.
- Numeric ranges.
- Enumerated values.
- Null handling.
- Nested objects.
- Arrays.
- Unknown fields when relevant.
- Special characters.

---

# Response Validation

A strong API test should validate more than the HTTP status code.

Recommended validations include:

1. Status code.
2. Response headers.
3. Response schema.
4. Required fields.
5. Data types.
6. Field values.
7. Business rules.
8. Error structure.
9. Response time where applicable.
10. Data persistence or side effects where applicable.

---

# JSON Schema Validation

JSON schema validation verifies that the API response follows the
expected structure.

Typical validations include:

- Required properties.
- Property data types.
- Nested object structure.
- Array structure.
- Allowed values.
- Minimum and maximum values.
- String constraints.

Schema validation helps detect contract-breaking changes.

---

# API Contract Testing

Contract testing verifies that an API continues to meet an agreed contract
between consumers and providers.

A contract may define:

- Endpoint.
- HTTP method.
- Request structure.
- Response structure.
- Status codes.
- Required fields.
- Data types.

Contract testing is especially useful in systems containing multiple
independently developed services.

---

# API Testing Checklist

For each API endpoint, consider validating:

- HTTP method.
- Endpoint.
- Authentication.
- Authorization.
- Headers.
- Path parameters.
- Query parameters.
- Request body.
- Required fields.
- Optional fields.
- Data types.
- Boundary values.
- Positive scenarios.
- Negative scenarios.
- Status codes.
- Response headers.
- Response body.
- Response schema.
- Business rules.
- Error handling.
- Security behavior.
- Performance expectations.
- Data persistence.
- Integration behavior.

---

# QE Testing Principle

Do not consider an API test successful merely because the expected HTTP
status code was returned.

For example, a test expecting HTTP 200 should also verify whether the
returned data and business behavior are correct.

A robust API test validates:

Request
→ Server behavior
→ Status code
→ Response structure
→ Response data
→ Business behavior
→ Side effects