# API Testing Fundamentals

## What is API Testing?

API testing is the process of validating an application's Application
Programming Interfaces to ensure that they behave correctly, reliably,
securely, and according to their defined contract.

API testing typically validates requests, responses, business rules,
authentication, authorization, error handling, data integrity, and
performance-related behavior.

API testing is commonly performed at the service layer without requiring
interaction with the application's user interface.

---

## Objectives of API Testing

The major objectives of API testing are:

1. Verify that the API returns the expected response for valid requests.
2. Verify that invalid requests are handled correctly.
3. Validate HTTP status codes.
4. Validate response headers.
5. Validate response body and data.
6. Validate business rules.
7. Validate authentication and authorization.
8. Validate error handling.
9. Validate boundary conditions.
10. Identify defects early before they reach the UI or production.

---

## Functional API Testing

Functional testing verifies that an API performs the behavior defined by
its requirements.

Typical checks include:

- Request parameters are accepted correctly.
- Mandatory fields are validated.
- Optional fields behave correctly.
- Business rules are applied correctly.
- Expected status codes are returned.
- Response data is correct.
- Response schema is correct.

Example:

For a user creation API:

POST /users

A functional test should verify that a valid request creates the user and
returns the expected status code and response data.

---

## Positive Testing

Positive testing verifies expected behavior using valid inputs.

Examples:

- Send a valid request body.
- Provide all mandatory fields.
- Use valid authentication credentials.
- Send valid data types.
- Use valid business values.

Expected behavior:

The API should process the request successfully and return the expected
response.

---

## Negative Testing

Negative testing verifies how the API behaves when invalid or unexpected
inputs are provided.

Examples:

- Missing mandatory fields.
- Invalid data types.
- Invalid authentication token.
- Invalid parameter values.
- Empty request body.
- Malformed JSON.
- Unsupported HTTP method.
- Invalid resource identifier.

The objective is to ensure that the API fails gracefully and returns an
appropriate response.

---

## Boundary Testing

Boundary testing validates behavior at and around the limits defined by
the requirements.

For example, if a username must contain between 5 and 20 characters,
use test values such as:

- 4 characters
- 5 characters
- 6 characters
- 19 characters
- 20 characters
- 21 characters

Boundary testing is useful for identifying validation defects that may not
be detected using only normal input values.

---

## Regression Testing

Regression testing verifies that previously working API functionality
continues to work after code changes.

Regression testing should be performed after changes such as:

- New API functionality.
- Bug fixes.
- Database changes.
- Authentication changes.
- Configuration changes.
- Dependency upgrades.
- Infrastructure changes.

Automated API regression suites can help execute these tests consistently
and quickly.

---

## Integration Testing

API integration testing verifies that multiple services or components
work correctly together.

Examples include:

- API communicating with a database.
- Order service communicating with payment service.
- User service communicating with authentication service.
- API communicating with an external third-party service.

The objective is to verify both the API behavior and the interaction
between dependent systems.

---

## Common API Test Categories

A comprehensive API test strategy may include:

- Functional testing
- Positive testing
- Negative testing
- Boundary testing
- Integration testing
- Regression testing
- Contract testing
- Schema validation
- Authentication testing
- Authorization testing
- Security testing
- Performance testing
- Reliability testing

The appropriate combination depends on the API's requirements,
architecture, risk, and business criticality.

---

## Recommended API Test Case Structure

A useful API test case should normally contain:

1. Test case ID
2. Test scenario
3. Preconditions
4. Request method
5. Endpoint
6. Request headers
7. Request parameters
8. Request body
9. Test data
10. Expected status code
11. Expected response
12. Validation or assertions
13. Postconditions

A well-defined test case should be specific enough that another tester
can execute it and obtain the same expected result.

---

## API Testing Best Practices

Recommended practices include:

- Validate both positive and negative scenarios.
- Validate status codes.
- Validate response body.
- Validate response schema.
- Validate mandatory and optional fields.
- Test invalid input.
- Test boundary values.
- Test authentication and authorization.
- Validate error messages where requirements define them.
- Use reusable test data where appropriate.
- Automate stable regression scenarios.
- Include API tests in CI/CD pipelines.
- Keep test cases independent when possible.
- Avoid relying only on UI tests for service validation.

---

## QE Decision Guideline

When designing API tests, do not focus only on the successful response.

For each API operation, consider:

1. What happens when the request is valid?
2. What happens when required data is missing?
3. What happens when data is invalid?
4. What happens at the input boundaries?
5. What happens without authentication?
6. What happens with invalid authentication?
7. What happens when the user is authenticated but not authorized?
8. What happens when a dependent service fails?
9. What happens when the same request is repeated?
10. What happens when unexpected data is supplied?

A strong API test strategy should attempt to validate both expected
behavior and failure behavior.