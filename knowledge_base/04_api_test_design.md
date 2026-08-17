# API Test Design

## Purpose of API Test Design

API test design is the process of identifying test scenarios and test
cases that validate the functional, technical, security, and integration
behavior of an API.

A good API test strategy should cover:

- Expected behavior.
- Invalid behavior.
- Boundary conditions.
- Error handling.
- Authentication.
- Authorization.
- Data validation.
- Business rules.
- Integration behavior.
- Contract compliance.
- Security-related behavior.

The objective is not simply to verify that an endpoint returns the
expected HTTP status code. The objective is to determine whether the API
behaves correctly under realistic and unexpected conditions.

---

# Requirement Analysis Before Test Design

Before creating API test cases, understand:

1. API purpose.
2. Endpoint.
3. HTTP method.
4. Request structure.
5. Response structure.
6. Mandatory fields.
7. Optional fields.
8. Data types.
9. Allowed values.
10. Business rules.
11. Authentication requirements.
12. Authorization requirements.
13. Expected status codes.
14. Error behavior.
15. External dependencies.
16. Data persistence requirements.
17. Performance expectations.

If the API contract or requirement is unclear, identify the ambiguity
before creating assumptions in the test cases.

---

# Test Scenario Categories

A comprehensive API test strategy can include:

- Positive testing.
- Negative testing.
- Boundary testing.
- Equivalence partitioning.
- Input validation.
- Business rule testing.
- Authentication testing.
- Authorization testing.
- Schema validation.
- Contract testing.
- Integration testing.
- Idempotency testing.
- Error handling.
- Security testing.
- Performance testing.
- Reliability testing.
- Regression testing.

The applicable categories depend on the API and its requirements.

---

# Positive Test Design

Positive testing verifies that the API behaves correctly when valid data
and valid conditions are provided.

Example:

API:

POST /users

Valid request:

{
  "name": "John",
  "email": "john@example.com",
  "age": 30
}

Possible positive scenarios:

1. Create user with all valid mandatory fields.
2. Create user with valid optional fields.
3. Create user using minimum valid values.
4. Create user using maximum valid values.
5. Retrieve an existing user.
6. Update an existing user with valid data.
7. Delete an existing user when the user has permission.

Positive testing should verify both the response and the expected business
effect.

---

# Negative Test Design

Negative testing verifies that invalid requests are handled correctly.

Common negative scenarios include:

- Missing mandatory field.
- Invalid data type.
- Invalid format.
- Invalid enumeration value.
- Empty value.
- Null value.
- Malformed JSON.
- Invalid authentication.
- Insufficient authorization.
- Invalid path parameter.
- Invalid query parameter.
- Non-existing resource.
- Duplicate resource.
- Unsupported HTTP method.
- Invalid Content-Type.

A negative test should verify that:

1. The request is rejected appropriately.
2. The expected status code is returned.
3. The response structure is correct.
4. The error message is appropriate when defined by the contract.
5. Sensitive information is not exposed.
6. The system remains in a valid state.

---

# Boundary Value Analysis

Boundary value analysis focuses on values at and around the limits defined
by requirements.

Example:

If an input accepts 1 to 100:

Test:

- 0
- 1
- 2
- 99
- 100
- 101

The boundary values are especially important because validation defects
frequently occur at limits.

---

# String Boundary Testing

If a field accepts 5 to 20 characters, test:

- 4 characters.
- 5 characters.
- 6 characters.
- 19 characters.
- 20 characters.
- 21 characters.

Also consider:

- Empty string.
- Null.
- Whitespace-only string.
- Leading spaces.
- Trailing spaces.
- Special characters.
- Unicode characters where applicable.

---

# Numeric Boundary Testing

If an API accepts an integer between 1 and 100, test:

- 0.
- 1.
- 2.
- 99.
- 100.
- 101.

Also consider:

- Negative values.
- Decimal values.
- Very large values.
- Null.
- Empty string.
- Numeric values represented as strings.

The expected behavior must follow the API contract.

---

# Equivalence Partitioning

Equivalence partitioning divides input values into groups where values are
expected to behave similarly.

Example:

If age must be between 18 and 60:

Valid partition:

18 to 60

Invalid partitions:

Less than 18

Greater than 60

Instead of testing every possible value, representative values can be
selected from each partition.

Example:

- 17 → invalid partition.
- 30 → valid partition.
- 61 → invalid partition.

Equivalence partitioning helps reduce redundant test cases while
maintaining meaningful coverage.

---

# Required and Optional Fields

For every request field, determine whether it is:

- Mandatory.
- Optional.
- Conditionally mandatory.

Test scenarios should include:

### Mandatory field

- Field present with valid value.
- Field missing.
- Field present with invalid value.
- Field present with empty value.
- Field present with null value where applicable.

### Optional field

- Field omitted.
- Field included with valid value.
- Field included with invalid value.
- Field included with null where applicable.

### Conditionally mandatory field

Test the conditions that determine when the field becomes required.

---

# Data Type Validation

Validate that API fields accept the correct data type.

Common types include:

- String.
- Integer.
- Decimal.
- Boolean.
- Array.
- Object.
- Date.
- DateTime.

Example:

If age is defined as an integer, test:

- Valid integer.
- Decimal.
- String.
- Boolean.
- Null.
- Empty value.

The expected behavior should follow the API contract.

---

# Enumeration Testing

If a field accepts a fixed set of values, test:

- Every supported value.
- Unsupported value.
- Empty value.
- Null value.
- Incorrect case where case sensitivity matters.
- Leading or trailing spaces where applicable.

Example:

status:

- ACTIVE
- INACTIVE
- SUSPENDED

Test all supported values and at least one unsupported value.

---

# Business Rule Testing

Technical validation alone is not enough.

Business rules should also be tested.

Example:

An order API may allow cancellation only when:

- Order status is CREATED.
- Payment has not been completed.
- Shipment has not started.

Test combinations such as:

- CREATED → cancellation allowed.
- PAID → cancellation behavior according to requirement.
- SHIPPED → cancellation rejected.
- DELIVERED → cancellation rejected.

The test should validate the actual business rule rather than only the
HTTP response.

---

# State Transition Testing

Some APIs behave differently depending on the current state of a
resource.

Example order states:

CREATED
→ PAID
→ SHIPPED
→ DELIVERED

Test valid transitions:

CREATED → PAID

PAID → SHIPPED

SHIPPED → DELIVERED

Also test invalid transitions:

DELIVERED → CREATED

SHIPPED → CREATED

DELIVERED → CANCELLED

The expected behavior should be based on the documented state model.

---

# Idempotency Testing

Idempotency testing verifies whether repeating the same request produces
the expected result without unintended side effects.

This is particularly important for operations involving:

- Payments.
- Orders.
- Resource creation.
- Retry mechanisms.

Example:

A client submits a payment request with an idempotency key.

The same request is sent again with the same key.

The API should behave according to its documented idempotency contract.

Test scenarios should include:

- First request.
- Duplicate request with same idempotency key.
- Same key with different request data.
- Missing idempotency key where required.
- Invalid idempotency key.

---

# Duplicate Request Testing

Test what happens when the same operation is submitted multiple times.

Examples:

- Create the same user twice.
- Submit the same order twice.
- Submit the same payment request twice.
- Send repeated update requests.

Verify that the system does not create unintended duplicate data or
perform unintended repeated operations.

---

# Pagination Testing

For APIs that return lists, test pagination behavior.

Example:

GET /users?page=1&limit=20

Test:

- First page.
- Middle page.
- Last page.
- Page beyond available data.
- Page zero.
- Negative page.
- Very large page number.
- Limit minimum.
- Limit maximum.
- Limit beyond allowed maximum.
- Missing pagination parameters.

Also verify:

- Number of records.
- Total count where provided.
- Next/previous links where provided.
- Ordering.
- Duplicate or missing records between pages.

---

# Filtering and Sorting Testing

For APIs supporting filters and sorting, test:

- Valid filter.
- Invalid filter.
- Multiple filters.
- Empty filter.
- Case sensitivity.
- Special characters.
- Valid sort field.
- Invalid sort field.
- Ascending order.
- Descending order.
- Combination of filtering and sorting.

Verify that returned data actually matches the requested criteria.

---

# Search API Testing

For search endpoints, test:

- Exact search.
- Partial search.
- Case variations.
- Empty search.
- Special characters.
- No matching results.
- Large search input.
- Multiple search parameters.
- Invalid search parameter.

Verify:

- Matching records.
- Ordering.
- Pagination.
- Total result count.
- No unexpected records.

---

# Schema Validation

API responses should be validated against the expected schema where a
schema is available.

Validate:

- Required properties.
- Property names.
- Data types.
- Nested objects.
- Arrays.
- Enumerations.
- Nullability.
- String constraints.
- Numeric constraints.

Schema validation can detect breaking changes even when the HTTP status
code remains successful.

---

# Contract Testing

Contract testing validates that an API continues to satisfy an agreed
contract between consumers and providers.

A contract may define:

- Endpoint.
- HTTP method.
- Request structure.
- Response structure.
- Required fields.
- Data types.
- Status codes.

Contract tests are useful when multiple services are developed and
deployed independently.

---

# Authentication Test Design

For every protected endpoint, consider:

1. Valid credentials.
2. Missing credentials.
3. Invalid credentials.
4. Expired credentials.
5. Revoked credentials.
6. Malformed credentials.
7. Insufficient scope.
8. Unauthorized client.

The expected behavior should match the API's security requirements.

---

# Authorization Test Design

Test authorization independently from authentication.

Examples:

- Correct role.
- Incorrect role.
- Missing permission.
- Read-only user attempting write operation.
- User accessing another user's resource.
- Standard user attempting administrator operation.

Authorization tests should verify that security boundaries cannot be
bypassed.

---

# Error Handling Test Design

For each expected error condition, verify:

- HTTP status code.
- Error response structure.
- Error code where applicable.
- Error message where defined.
- Correlation ID where applicable.
- No sensitive information.
- No stack trace exposed to the client.
- Correct server-side state.

A consistent error contract makes APIs easier to test and troubleshoot.

---

# Dependency Failure Testing

If the API depends on another service, test failure scenarios where
possible.

Examples:

- Database unavailable.
- Payment service unavailable.
- Authentication service unavailable.
- External API timeout.
- Network failure.

Verify:

- Appropriate response.
- No incorrect data committed.
- Safe failure behavior.
- Retry behavior where applicable.
- Correct recovery behavior.

---

# Performance-Oriented Test Scenarios

Performance testing is a separate discipline, but API functional tests
can still identify basic performance expectations.

Consider:

- Response time.
- Large request payload.
- Large response payload.
- Concurrent requests.
- Repeated requests.
- Rate limiting.

Performance expectations should be based on defined requirements rather
than arbitrary assumptions.

---

# Data Integrity Testing

After an API operation, verify that the expected data state is correct.

Examples:

Create:

API response indicates successful creation.

Then verify:

- Resource exists.
- Correct fields are persisted.
- Generated identifier is valid.

Update:

- Updated fields contain expected values.
- Fields that should not change remain unchanged.

Delete:

- Resource is no longer accessible where the contract requires deletion.

---

# Test Data Design

Good API tests require appropriate test data.

Test data should include:

- Valid data.
- Invalid data.
- Boundary values.
- Duplicate data.
- Missing data.
- Null values.
- Special characters.
- Large values.
- Different user roles.
- Different resource states.

Avoid using production data for testing unless it has been appropriately
sanitized and approved.

---

# Test Case Prioritization

Not every test case has the same priority.

A useful prioritization approach is:

### High Priority

- Critical business functionality.
- Authentication.
- Authorization.
- Payment-related operations.
- Data creation and deletion.
- Core business rules.
- High-risk integrations.

### Medium Priority

- Important optional functionality.
- Secondary business flows.
- Additional validation scenarios.

### Low Priority

- Low-risk edge scenarios.
- Rarely used functionality.
- Non-critical variations.

Risk, business impact, usage frequency, and defect history should influence
test prioritization.

---

# API Test Design Example

Suppose an API is:

POST /orders

Request:

{
  "productId": "P100",
  "quantity": 2,
  "customerId": "C100"
}

A strong test design should consider:

## Positive

- Valid product.
- Valid customer.
- Valid quantity.
- Multiple valid products where supported.

## Negative

- Missing productId.
- Missing customerId.
- Missing quantity.
- Invalid productId.
- Invalid customerId.
- Invalid quantity.
- Negative quantity.
- Zero quantity.
- Invalid data type.
- Malformed JSON.

## Boundary

If quantity supports 1 to 10:

- 0
- 1
- 2
- 9
- 10
- 11

## Authorization

- Authorized customer.
- Unauthorized customer.
- Customer attempting to create an order for another restricted account.

## Business Rules

- Product unavailable.
- Product out of stock.
- Customer account inactive.
- Order limit exceeded.

## Duplicate / Idempotency

- Repeat the same request.
- Repeat with the same idempotency key.
- Repeat with a different idempotency key.

## Response Validation

Validate:

- Status code.
- Order ID.
- Customer ID.
- Product details.
- Quantity.
- Order status.
- Response schema.

---

# QE Test Design Checklist

Before considering API test coverage complete, ask:

1. Have positive scenarios been covered?
2. Have negative scenarios been covered?
3. Have boundary values been tested?
4. Have equivalence partitions been considered?
5. Have mandatory fields been tested?
6. Have optional fields been tested?
7. Have data types been tested?
8. Have business rules been tested?
9. Have state transitions been tested?
10. Have authentication scenarios been tested?
11. Have authorization scenarios been tested?
12. Have schema and contract validations been considered?
13. Have duplicate and idempotency scenarios been considered?
14. Have error responses been validated?
15. Have dependency failures been considered?
16. Have data integrity and side effects been verified?
17. Have high-risk scenarios been prioritized?
18. Have realistic test data and boundary data been included?

A strong API test strategy should combine functional correctness,
negative testing, boundary analysis, business-rule validation, security
testing, integration testing, and data validation.